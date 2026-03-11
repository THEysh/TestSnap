from __future__ import annotations

import atexit
import asyncio
import json
import mimetypes
import multiprocessing
import os
import queue
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from werkzeug.utils import secure_filename

from flask_react.log import (
    TASK_PROCESS,
    close_task_stream,
    complete_task,
    init_task_stream,
    logger,
    push_task_stream,
    update_task_progress,
)
from srcProject.models.chat_model import SiliconChatModel
from srcProject.utlis.common import find_project_root, to_relative_path


def safe_resolve_under_root(root: Path, relative_path: str) -> Path | None:
    try:
        root_abs = root.resolve()
        candidate = (root_abs / relative_path).resolve()
        try:
            root_norm = os.path.normcase(str(root_abs))
            cand_norm = os.path.normcase(str(candidate))
            if os.path.commonpath([root_norm, cand_norm]) == root_norm:
                return candidate
        except Exception:
            if str(candidate).startswith(str(root_abs)):
                return candidate
        return None
    except Exception:
        return None


@dataclass(frozen=True)
class FileTypeConfig:
    upload_dir: Path
    allowed_extensions: set[str]
    success_message: str


class FileRetention:
    def __init__(self, retention_seconds: int = 10800) -> None:
        self._retention_seconds = retention_seconds

    def schedule_file_deletion(self, file_path: Path) -> None:
        def delete_file() -> None:
            try:
                if file_path.exists():
                    file_path.unlink(missing_ok=True)
                    logger.info(f"文件已自动删除: {file_path}")
            except Exception as e:
                logger.error(f"删除文件失败: {file_path}, 错误: {e}")

        timer = threading.Timer(self._retention_seconds, delete_file)
        timer.daemon = True
        timer.start()

    def schedule_directory_deletion(self, dir_path: Path) -> None:
        def delete_directory() -> None:
            try:
                if not dir_path.exists():
                    return
                total_files = 0
                total_size = 0
                for root, _, files in os.walk(dir_path):
                    for filename in files:
                        total_files += 1
                        try:
                            total_size += (Path(root) / filename).stat().st_size
                        except Exception:
                            pass
                shutil.rmtree(dir_path)
                logger.info(
                    f"目录已自动删除: {dir_path}, 共删除 {total_files} 个文件，总大小约 {total_size / 1024 / 1024:.2f} MB"
                )
            except Exception as e:
                logger.error(f"删除目录失败: {dir_path}, 错误: {e}")

        logger.info(f"安排目录在{self._retention_seconds}秒后删除: {dir_path}")
        timer = threading.Timer(self._retention_seconds, delete_directory)
        timer.daemon = True
        timer.start()


class WorkerManager:
    def __init__(self, api_base_url: str, on_result_directory: Callable[[Path], None]) -> None:
        self._api_base_url = api_base_url
        self._on_result_directory = on_result_directory

        self._mode = (os.getenv("TEXTSNAP_WORKER_MODE", "embedded") or "embedded").lower()

        self._lock = threading.Lock()
        self._inflight: set[str] = set()
        self._shutdown_event = threading.Event()

        self._pending_lock = threading.Lock()
        self._pending: dict[str, queue.Queue] = {}

        self._slot_seq = 0
        self._active: dict[str, Any] | None = None
        self._standby: dict[str, Any] | None = None

        self._daemon_lock = threading.Lock()
        self._daemon_conn: Any | None = None
        self._daemon_reader: threading.Thread | None = None
        self._daemon_host = os.getenv("HOST", "0.0.0.0")
        self._daemon_port = int(os.getenv("PORT", "7862"))
        self._daemon_authkey = (os.getenv("WORKER_AUTHKEY", "textsnap") or "textsnap").encode("utf-8")

        self._monitor_started = False
        atexit.register(self.shutdown)

    def shutdown(self) -> None:
        if self._shutdown_event.is_set():
            return
        self._shutdown_event.set()
        if self._mode == "daemon":
            with self._daemon_lock:
                conn = self._daemon_conn
                self._daemon_conn = None
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            return

        with self._lock:
            active = self._active
            standby = self._standby
            self._active = None
            self._standby = None
        for slot in [active, standby]:
            if not slot:
                continue
            try:
                slot.get("in_q").put(None)
            except Exception:
                pass
            proc = slot.get("proc")
            if proc is not None and proc.is_alive():
                try:
                    proc.join(timeout=2)
                except Exception:
                    pass
                if proc.is_alive():
                    try:
                        proc.terminate()
                    except Exception:
                        pass

    def start_monitor(self) -> None:
        if self._monitor_started:
            return
        if multiprocessing.current_process().name != "MainProcess":
            return
        self._monitor_started = True

        def loop() -> None:
            while not self._shutdown_event.is_set():
                try:
                    self.ensure_running()
                    if self._mode != "daemon":
                        self._warmup_if_needed()
                except Exception:
                    pass
                time.sleep(2)

        t = threading.Thread(target=loop, name="TextSnapWorkerMonitor", daemon=True)
        t.start()

    def ensure_running(self) -> None:
        if self._shutdown_event.is_set():
            return
        if self._mode == "daemon":
            self._ensure_daemon_connected()
            return
        with self._lock:
            if not self._active or not self._active.get("proc") or not self._active["proc"].is_alive():
                self._active = self._start_local_worker_locked(role="active")

            if not self._standby or not self._standby.get("proc") or not self._standby["proc"].is_alive():
                self._standby = self._start_local_worker_locked(role="standby")

    def _warmup_if_needed(self) -> None:
        slots: list[dict[str, Any]] = []
        with self._lock:
            if self._active and not self._active.get("warmed"):
                slots.append(self._active)
            if self._standby and not self._standby.get("warmed"):
                slots.append(self._standby)
        for slot in slots:
            try:
                resp = self._send_command_to_slot(slot, "warmup", {}, timeout_seconds=600)
                if resp and resp.get("success"):
                    with self._lock:
                        if slot.get("role") == "active" and self._active and self._active.get("slot_id") == slot.get("slot_id"):
                            self._active["warmed"] = True
                        if slot.get("role") == "standby" and self._standby and self._standby.get("slot_id") == slot.get("slot_id"):
                            self._standby["warmed"] = True
            except Exception:
                continue

    def submit_task(self, task_id: str, file_path: str, file_type: str) -> None:
        self.ensure_running()
        with self._lock:
            self._inflight.add(task_id)
            active = self._active
        if self._mode == "daemon":
            self._daemon_send({"kind": "task", "task_id": task_id, "file_path": file_path, "file_type": file_type})
            return
        if not active:
            raise RuntimeError("worker未就绪")
        active["in_q"].put({"task_id": task_id, "file_path": file_path, "file_type": file_type})

    def send_command(self, kind: str, payload: dict[str, Any], timeout_seconds: int = 20) -> dict[str, Any]:
        command_id = uuid.uuid4().hex
        response_q: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[command_id] = response_q
        self.ensure_running()
        if self._mode == "daemon":
            try:
                self._daemon_send({"kind": "command", "command_kind": kind, "command_id": command_id, "payload": payload})
            except Exception:
                with self._pending_lock:
                    self._pending.pop(command_id, None)
                return {"success": False, "error": "worker未就绪", "command_id": command_id}
        else:
            with self._lock:
                active = self._active
            if not active:
                with self._pending_lock:
                    self._pending.pop(command_id, None)
                return {"success": False, "error": "worker未就绪", "command_id": command_id}
            active["in_q"].put({"kind": kind, "command_id": command_id, "payload": payload})
        try:
            return response_q.get(timeout=timeout_seconds)
        except Exception:
            with self._pending_lock:
                self._pending.pop(command_id, None)
            return {"success": False, "error": "worker响应超时", "command_id": command_id}

    def _start_local_worker_locked(self, role: str) -> dict[str, Any]:
        self._slot_seq += 1
        slot_id = self._slot_seq

        ctx = multiprocessing.get_context("spawn")
        in_q = ctx.Queue()
        out_q = ctx.Queue()
        proc = ctx.Process(
            target=_subprocess_worker_main,
            args=(in_q, out_q, self._api_base_url),
            daemon=True,
        )
        proc.start()

        def reader_loop() -> None:
            while not self._shutdown_event.is_set():
                try:
                    msg = out_q.get(timeout=0.5)
                except Exception:
                    if proc is not None and not proc.is_alive():
                        self._handle_local_worker_crash(role, slot_id, proc)
                        return
                    continue
                self._dispatch_worker_message(msg)

        reader = threading.Thread(
            target=reader_loop, name=f"TextSnapWorkerReader-{role}-{slot_id}", daemon=True
        )
        reader.start()
        return {
            "role": role,
            "slot_id": slot_id,
            "ctx": ctx,
            "in_q": in_q,
            "out_q": out_q,
            "proc": proc,
            "reader": reader,
            "warmed": False,
        }

    def _handle_local_worker_crash(self, role: str, slot_id: int, dead_proc: multiprocessing.Process | None) -> None:
        try:
            if dead_proc is not None:
                logger.error(
                    f"处理进程退出: role={role}, pid={getattr(dead_proc, 'pid', None)}, exitcode={getattr(dead_proc, 'exitcode', None)}"
                )
            else:
                logger.error(f"处理进程退出: role={role}")
        except Exception:
            pass

        if role == "standby":
            with self._lock:
                if self._standby and self._standby.get("slot_id") == slot_id:
                    self._standby = None
            return

        inflight: list[str]
        with self._lock:
            if self._active and self._active.get("slot_id") == slot_id:
                self._active = None
            inflight = list(self._inflight)
            self._inflight.clear()

            if self._standby and self._standby.get("proc") and self._standby["proc"].is_alive():
                self._active = self._standby
                self._active["role"] = "active"
                self._standby = None

            if not self._standby or not self._standby.get("proc") or not self._standby["proc"].is_alive():
                self._standby = self._start_local_worker_locked(role="standby")

        err_msg = "处理进程崩溃（0xC0000005），任务已中止"
        try:
            exitcode = getattr(dead_proc, "exitcode", None) if dead_proc is not None else None
            if exitcode in (-1, 0xC000013A):
                err_msg = "处理进程被中断，任务已中止"
        except Exception:
            pass

        for task_id in inflight:
            try:
                complete_task(task_id, error=err_msg)
            except Exception:
                pass
            try:
                close_task_stream(task_id)
            except Exception:
                pass

        with self._pending_lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for command_id, q in pending:
            try:
                q.put({"type": "command_result", "command_id": command_id, "success": False, "error": "worker已崩溃"})
            except Exception:
                pass

    def _send_command_to_slot(self, slot: dict[str, Any] | None, kind: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        if not slot:
            raise RuntimeError("worker未就绪")
        command_id = uuid.uuid4().hex
        response_q: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[command_id] = response_q
        slot["in_q"].put({"kind": kind, "command_id": command_id, "payload": payload})
        try:
            return response_q.get(timeout=timeout_seconds)
        except Exception:
            with self._pending_lock:
                self._pending.pop(command_id, None)
            raise

    def _ensure_daemon_connected(self) -> None:
        with self._daemon_lock:
            if self._daemon_conn is not None:
                return
            from multiprocessing.connection import Client

            conn = Client((self._daemon_host, self._daemon_port), authkey=self._daemon_authkey)
            self._daemon_conn = conn

            def reader_loop() -> None:
                while not self._shutdown_event.is_set():
                    try:
                        msg = conn.recv()
                    except Exception:
                        with self._daemon_lock:
                            if self._daemon_conn is conn:
                                self._daemon_conn = None
                        inflight: list[str]
                        with self._lock:
                            inflight = list(self._inflight)
                            self._inflight.clear()
                        for task_id in inflight:
                            try:
                                complete_task(task_id, error="worker连接中断，任务已中止")
                            except Exception:
                                pass
                            try:
                                close_task_stream(task_id)
                            except Exception:
                                pass
                        return
                    if isinstance(msg, dict):
                        self._dispatch_worker_message(msg)

            self._daemon_reader = threading.Thread(
                target=reader_loop, name="TextSnapDaemonReader", daemon=True
            )
            self._daemon_reader.start()

    def _daemon_send(self, payload: dict[str, Any]) -> None:
        self._ensure_daemon_connected()
        with self._daemon_lock:
            conn = self._daemon_conn
        if conn is None:
            raise RuntimeError("worker未就绪")
        conn.send(payload)

    def _dispatch_worker_message(self, msg: dict[str, Any]) -> None:
        try:
            mtype = msg.get("type")
            task_id = msg.get("task_id")
            if mtype == "stream":
                payload = msg.get("payload")
                if payload is not None:
                    push_task_stream(task_id, payload)
                return
            if mtype == "progress":
                update_task_progress(
                    task_id,
                    msg.get("progress", 0),
                    msg.get("status", "processing"),
                    msg.get("message"),
                )
                return
            if mtype == "status":
                if task_id in TASK_PROCESS:
                    TASK_PROCESS[task_id]["status"] = msg.get("status") or TASK_PROCESS[task_id].get("status")
                    TASK_PROCESS[task_id]["message"] = msg.get("message") or TASK_PROCESS[task_id].get("message")
                    TASK_PROCESS[task_id]["updated_at"] = time.time()
                return
            if mtype == "done":
                success = bool(msg.get("success", False))
                if success:
                    result = msg.get("result") or {}
                    result_directory = msg.get("result_directory")
                    if result_directory:
                        try:
                            p = Path(result_directory)
                            if p.exists() and p.is_dir():
                                self._on_result_directory(p)
                        except Exception:
                            pass
                    complete_task(task_id, result)
                else:
                    complete_task(task_id, error=msg.get("error") or "处理失败")
                try:
                    close_task_stream(task_id)
                except Exception:
                    pass
                with self._lock:
                    self._inflight.discard(task_id)
                return
            if mtype == "command_result":
                command_id = msg.get("command_id")
                if not command_id:
                    return
                with self._pending_lock:
                    q = self._pending.pop(command_id, None)
                if q is not None:
                    try:
                        q.put(msg)
                    except Exception:
                        pass
        except Exception:
            return

def _subprocess_worker_main(in_q: Any, out_q: Any, api_base_url: str) -> None:
    try:
        os.environ.setdefault("OMP_NUM_THREADS", "1")
        os.environ.setdefault("MKL_NUM_THREADS", "1")
        os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
        os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
        os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
    except Exception:
        pass
    try:
        import cv2  # type: ignore

        try:
            cv2.setNumThreads(0)
        except Exception:
            pass
    except Exception:
        pass
    try:
        import torch  # type: ignore

        try:
            torch.set_num_threads(1)
        except Exception:
            pass
        try:
            torch.set_num_interop_threads(1)
        except Exception:
            pass
    except Exception:
        pass

    from srcProject.main_process_sequence import get_model_manager as worker_get_model_manager
    from srcProject.main_process_sequence import main as process_main

    try:
        while True:
            try:
                job = in_q.get()
            except (KeyboardInterrupt, EOFError):
                break
            if job is None:
                break

            kind = job.get("kind") or "process"
            if kind == "warmup":
                command_id = job.get("command_id")
                try:
                    mgr = worker_get_model_manager()
                    out_q.put(
                        {
                            "type": "command_result",
                            "command_id": command_id,
                            "success": True,
                            "pid": os.getpid(),
                            "device": getattr(mgr, "device", None),
                        }
                    )
                except Exception as e:
                    out_q.put({"type": "command_result", "command_id": command_id, "success": False, "error": str(e)})
                continue

            if kind == "update_config":
                command_id = job.get("command_id")
                payload = job.get("payload") or {}
                try:
                    mgr = worker_get_model_manager()
                    updated: dict[str, Any] = {}
                    if read_model := payload.get("read_model"):
                        updated["read_model"] = mgr.change_read_model(model_name=read_model)
                    ocr_api_model = payload.get("ocr_api_model")
                    if isinstance(ocr_api_model, dict):
                        updated["ocr_api_model"] = mgr.change_ocr_recognizer(
                            api_name=ocr_api_model.get("api_name", None),
                            api_key=ocr_api_model.get("api_key", None),
                            base_url=ocr_api_model.get("base_url", None),
                            model_name=ocr_api_model.get("model_name", None),
                        )
                    out_q.put({"type": "command_result", "command_id": command_id, "success": True, "updated": updated})
                except Exception as e:
                    out_q.put({"type": "command_result", "command_id": command_id, "success": False, "error": str(e)})
                continue

            task_id = job.get("task_id")
            file_path = job.get("file_path")
            file_type = job.get("file_type")
            try:
                def progress_update(local_task_id: str, progress: float, status: str = "processing", message: str | None = None) -> None:
                    out_q.put(
                        {
                            "type": "progress",
                            "task_id": local_task_id,
                            "progress": progress,
                            "status": status,
                            "message": message,
                        }
                    )

                def stream_callback(local_task_id: str, payload: Any) -> None:
                    out_q.put({"type": "stream", "task_id": local_task_id, "payload": payload})

                out_q.put(
                    {"type": "status", "task_id": task_id, "status": "processing", "message": f"正在处理{file_type}文件"}
                )

                try:
                    md_save_path, visualize_path = asyncio.run(
                        process_main(
                            file_path,
                            task_id=task_id,
                            stream_callback=stream_callback,
                            stream_api_base_url=api_base_url,
                            progress_update=progress_update,
                        )
                    )
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    md_save_path, visualize_path = loop.run_until_complete(
                        process_main(
                            file_path,
                            task_id=task_id,
                            stream_callback=stream_callback,
                            stream_api_base_url=api_base_url,
                            progress_update=progress_update,
                        )
                    )
                    try:
                        loop.stop()
                        loop.close()
                    except Exception:
                        pass

                if not os.path.isfile(visualize_path):
                    raise RuntimeError("路径不存在，处理失败")

                visualize_relative_path = to_relative_path(visualize_path)
                md_relative_path = to_relative_path(md_save_path)
                try:
                    result_directory = os.path.dirname(visualize_path) or os.path.dirname(md_save_path)
                except Exception:
                    result_directory = None
                result = {
                    "success": True,
                    "processed_file": visualize_relative_path,
                    "md_path": md_relative_path,
                    "processing_info": {
                        "method": "示例处理",
                        "description": "示例处理",
                        "file_size": os.path.getsize(visualize_path),
                        "auto_delete_info": "该文件将在3小时后自动删除",
                    },
                }
                out_q.put(
                    {
                        "type": "done",
                        "task_id": task_id,
                        "success": True,
                        "result": result,
                        "result_directory": result_directory,
                    }
                )
            except Exception as e:
                out_q.put({"type": "done", "task_id": task_id, "success": False, "error": str(e)})
    finally:
        try:
            import srcProject.main_process_sequence as _mps
            mgr = getattr(_mps, "_MODEL_MANAGER", None)
            if mgr is not None:
                chat_model = getattr(mgr, "chat_model", None)
                if chat_model is not None:
                    close = getattr(chat_model, "aclose", None)
                    if close is not None:
                        try:
                            asyncio.run(close())
                        except Exception:
                            pass
        except Exception:
            pass


class FileService:
    def __init__(self, project_root: Path, retention: FileRetention, worker: WorkerManager) -> None:
        self._project_root = project_root
        self._retention = retention
        self._worker = worker

        upload_root = project_root / "srcProject" / "output" / "visualizations" / "uploads"
        self._file_type_config: dict[str, FileTypeConfig] = {
            "pdf": FileTypeConfig(
                upload_dir=upload_root / "pdfs",
                allowed_extensions={"pdf"},
                success_message="PDF处理完成",
            ),
            "image": FileTypeConfig(
                upload_dir=upload_root / "images",
                allowed_extensions={"png", "jpg", "jpeg", "gif", "bmp", "webp"},
                success_message="图片处理完成",
            ),
        }

    def ensure_directories(self) -> None:
        for cfg in self._file_type_config.values():
            cfg.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, file_obj: Any, file_type: str) -> dict[str, Any]:
        cfg = self._file_type_config.get(file_type)
        if cfg is None:
            return {"success": False, "error": f"不支持的文件类型: {file_type}"}
        if not file_obj or not getattr(file_obj, "filename", ""):
            return {"success": False, "error": "未选择文件"}

        filename = str(file_obj.filename)
        _, ext = os.path.splitext(filename.lower())
        if ext[1:] not in cfg.allowed_extensions:
            supported = ", ".join(sorted(cfg.allowed_extensions))
            return {"success": False, "error": f"只支持以下文件类型: {supported}"}

        safe_name = secure_filename(filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = cfg.upload_dir / unique_filename
        cfg.upload_dir.mkdir(parents=True, exist_ok=True)

        try:
            file_obj.save(str(file_path))
            logger.info(f"已上传{file_type}文件: {safe_name} 至 {file_path}")
        except Exception as e:
            logger.error(f"{file_type}文件上传失败: {e}")
            return {"success": False, "error": f"上传失败: {e}"}

        self._retention.schedule_file_deletion(file_path)
        try:
            file_size = file_path.stat().st_size
        except Exception:
            file_size = 0

        return {
            "success": True,
            "message": f"{file_type}文件上传成功",
            "file_info": {
                "original_filename": safe_name,
                "unique_filename": unique_filename,
                "file_size": file_size,
                "file_path": str(file_path),
            },
        }

    def process_async(self, filename: str, file_type: str) -> dict[str, Any]:
        cfg = self._file_type_config.get(file_type)
        if cfg is None:
            return {"success": False, "error": f"不支持的文件类型: {file_type}"}

        file_path = cfg.upload_dir / filename
        if not file_path.exists():
            return {"success": False, "error": "文件不存在"}

        task_id = f"{file_type}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
        TASK_PROCESS[task_id] = {
            "progress": 0,
            "status": "started",
            "message": f"开始处理{file_type}文件",
            "file_type": file_type,
            "filename": filename,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        init_task_stream(task_id)
        logger.info(f"创建任务 {task_id}: 处理{file_type}文件 {filename}")

        TASK_PROCESS[task_id]["status"] = "queued"
        TASK_PROCESS[task_id]["message"] = f"已进入队列，等待处理{file_type}文件"
        TASK_PROCESS[task_id]["updated_at"] = time.time()

        self._worker.submit_task(task_id, str(file_path), file_type)
        return {"success": True, "message": f"{file_type}文件处理已启动", "task_id": task_id}


class MarkdownService:
    def __init__(self, project_root: Path, port: int) -> None:
        self._project_root = project_root
        self._port = port

    def load_markdown(self, relative_path: str) -> dict[str, Any]:
        if not relative_path:
            return {"success": False, "error": "请提供文件路径"}, 400

        full_path = safe_resolve_under_root(self._project_root, relative_path)
        if full_path is None:
            return {"success": False, "error": "文件路径不在项目目录内"}, 403

        if not full_path.exists():
            return {"success": False, "error": f"文件不存在: {relative_path}"}, 404
        if full_path.suffix.lower() != ".md":
            return {"success": False, "error": "只支持Markdown文件(.md)"}, 400

        try:
            content = full_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = full_path.read_text(encoding="gbk")
            except UnicodeDecodeError:
                return {"success": False, "error": "文件编码格式不支持"}, 400
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {e}"}, 500

        file_dir = str(Path(relative_path).parent).replace("\\", "/")
        return (
            {
                "success": True,
                "content": content,
                "file_dir": "" if file_dir == "." else file_dir,
                "file_path": relative_path,
                "api_base_url": f"http://localhost:{self._port}/api/files",
            },
            200,
        )


class ChatService:
    def __init__(self, api_keys: list[str] | str, base_url: str, model_name: str) -> None:
        self._api_keys = api_keys
        self._base_url = base_url
        self._model_name = model_name

        self._model_lock = threading.Lock()
        self._model: SiliconChatModel | None = None

        self._cancel_lock = threading.Lock()
        self._cancel_request_ids: set[str] = set()

    def mark_cancel(self, conv_id: str | None, request_id: str | None) -> None:
        with self._cancel_lock:
            if request_id:
                self._cancel_request_ids.add(str(request_id))

    def clear_cancel(self, conv_id: str | None, request_id: str | None) -> None:
        with self._cancel_lock:
            if request_id:
                self._cancel_request_ids.discard(str(request_id))

    def is_cancelled(self, conv_id: str | None, request_id: str | None) -> bool:
        with self._cancel_lock:
            if request_id and str(request_id) in self._cancel_request_ids:
                return True
            return False

    def _get_model(self) -> SiliconChatModel:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                self._model = SiliconChatModel(
                    api_keys=self._api_keys,
                    base_url=self._base_url,
                    model_name=self._model_name,
                )
        return self._model

    def stream_events(
        self,
        messages: list[dict[str, Any]],
        enable_reasoning: bool,
        model_name: str | None,
        conv_id: str | None,
        request_id: str | None,
    ) -> Iterator[str]:
        loop = asyncio.new_event_loop()
        try:
            try:
                asyncio.set_event_loop(loop)
            except Exception:
                pass

            agen = self._get_model().achat_stream(messages, enable_reasoning, model_name)
            try:
                while True:
                    if self.is_cancelled(conv_id, request_id):
                        break
                    try:
                        piece = loop.run_until_complete(agen.__anext__())
                    except StopAsyncIteration:
                        break
                    except GeneratorExit:
                        break

                    if isinstance(piece, dict):
                        payload = json.dumps(piece, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                    else:
                        error_msg = "返回的内容无法解析为json"
                        payload = json.dumps({"error": error_msg, "detail": str(piece)}, ensure_ascii=False)
                        yield f"event: error\ndata: {payload}\n\n"
            finally:
                try:
                    loop.run_until_complete(agen.aclose())
                except Exception:
                    pass
        except GeneratorExit:
            pass
        except Exception as e:
            err = str(e).replace("\n", " ")
            yield f"event: error\ndata: {err}\n\n"
        finally:
            self.clear_cancel(conv_id, request_id)
            try:
                loop.stop()
                loop.close()
            except Exception:
                pass
        yield "event: done\ndata: [DONE]\n\n"

    def chat_once(
        self, messages: list[dict[str, Any]], enable_reasoning: bool, model_name: str | None
    ) -> dict[str, Any]:
        loop = asyncio.new_event_loop()
        reply_parts: list[str] = []
        try:
            try:
                asyncio.set_event_loop(loop)
            except Exception:
                pass
            agen = self._get_model().achat_stream(messages, enable_reasoning, model_name)
            try:
                while True:
                    try:
                        piece = loop.run_until_complete(agen.__anext__())
                    except StopAsyncIteration:
                        break
                    if isinstance(piece, dict):
                        if piece.get("type") == "content":
                            reply_parts.append(str(piece.get("content") or ""))
                    elif isinstance(piece, str):
                        reply_parts.append(piece)
            finally:
                try:
                    loop.run_until_complete(agen.aclose())
                except Exception:
                    pass
            return {"success": True, "reply": "".join(reply_parts)}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            try:
                loop.stop()
                loop.close()
            except Exception:
                pass

    def generate_card(self, chat_text: str, model_name: str | None) -> dict[str, Any]:
        def extract_json(text: str) -> dict[str, Any] | None:
            raw = str(text or "").strip()
            if not raw:
                return None
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            candidate = raw[start : end + 1]
            try:
                return json.loads(candidate)
            except Exception:
                return None

        def normalize_card(obj: dict[str, Any]) -> dict[str, Any] | None:
            if not isinstance(obj, dict):
                return None
            title = str(obj.get("title") or "").strip()
            kp = obj.get("knowledge_points")
            if not isinstance(kp, list):
                kp = []
            kp_list = [str(x).strip() for x in kp if str(x).strip()]
            ex = obj.get("example") if isinstance(obj.get("example"), dict) else {}
            question = str((ex or {}).get("question") or "").strip()
            analysis = str((ex or {}).get("analysis") or "").strip()
            summary = str(obj.get("summary") or "").strip()
            if not title:
                title = "学习卡片"
            if not kp_list and not question and not summary:
                return None
            return {
                "title": title,
                "knowledge_points": kp_list[:8],
                "example": {"question": question, "analysis": analysis},
                "summary": summary,
            }

        system_prompt = "\n".join(
            [
                "你是 AI 学伴的学习卡片生成助手。",
                "你的任务是根据用户刚刚与 AI 的聊天内容，提炼核心知识，并生成一张结构清晰的学习卡片，方便用户复习。",
                "输出必须为严格 JSON，不要使用 Markdown，不要添加任何解释文字，不要使用代码块。",
                '输出格式必须为：{"title": "...", "knowledge_points": ["..."], "example": {"question": "...", "analysis": "..."}, "summary": "..."}',
                "knowledge_points 请输出 3-5 条。",
                "example 请输出 1 道典型例题的题目与简要解析。",
                "summary 用一句话总结核心思想。",
            ]
        )
        user_prompt = f"聊天内容如下：\n\n{str(chat_text or '').strip()}\n"
        reply = self.chat_once(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            enable_reasoning=False,
            model_name=model_name,
        )
        if not reply.get("success"):
            return reply
        content = str(reply.get("reply") or "")
        parsed = extract_json(content)
        if parsed is None:
            return {"success": False, "error": "生成卡片失败：返回结果不是有效 JSON"}
        card = normalize_card(parsed)
        if card is None:
            return {"success": False, "error": "生成卡片失败：返回 JSON 字段不完整"}
        return {"success": True, "data": card}

    def stream_generate_card_markdown(self, chat_text: str, model_name: str | None) -> Iterator[str]:
        system_prompt = "\n".join(
            [
                "你是 AI 学伴的学习卡片生成助手。",
                "你的任务是根据用户刚刚与 AI 的聊天内容，提炼核心知识，并生成一张结构清晰的学习卡片，方便用户复习。",
                "学习卡片结构如下：标题、知识点（3-5条）、题目(如果聊天内容中，涉及到题目的话，列出原题)、易错点(难以理解的部分)、对问题的做出详细的解释、总结。",
                "内容清晰，不要冗长。",
                "输出格式必须为 Markdown：",
                "# 标题",
                "## 知识点",
                "- ",
                "## (这个部分根据聊天内容自由生成)"
                "## 总结",
            ]
        )
        user_prompt = f"聊天内容如下：\n\n{str(chat_text or '').strip()}\n"
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        loop = asyncio.new_event_loop()
        try:
            try:
                asyncio.set_event_loop(loop)
            except Exception:
                pass
            agen = self._get_model().achat_stream(messages, enable_reasoning=False, model_name=model_name)
            try:
                while True:
                    try:
                        piece = loop.run_until_complete(agen.__anext__())
                    except StopAsyncIteration:
                        break
                    except GeneratorExit:
                        break
                    if isinstance(piece, dict) and piece.get("type") == "content":
                        payload = json.dumps({"type": "delta", "content": str(piece.get("content") or "")}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
                    elif isinstance(piece, str) and piece:
                        payload = json.dumps({"type": "delta", "content": str(piece)}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"
            finally:
                try:
                    loop.run_until_complete(agen.aclose())
                except Exception:
                    pass
        except Exception as e:
            err = str(e).replace("\n", " ")
            payload = json.dumps({"type": "error", "content": err}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        finally:
            try:
                loop.stop()
                loop.close()
            except Exception:
                pass
        yield "event: done\ndata: [DONE]\n\n"


def init_mimetypes() -> None:
    mimetypes.add_type("image/webp", ".webp")
    mimetypes.add_type("image/svg+xml", ".svg")


def get_project_root() -> Path:
    root = find_project_root()
    if root is None:
        raise RuntimeError("无法定位项目根目录")
    return Path(root)
