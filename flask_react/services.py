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

        self._lock = threading.Lock()
        self._ctx: multiprocessing.context.BaseContext | None = None
        self._in_q: multiprocessing.queues.Queue | None = None
        self._out_q: multiprocessing.queues.Queue | None = None
        self._process: multiprocessing.Process | None = None
        self._reader_thread: threading.Thread | None = None

        self._gen = 0
        self._inflight: set[str] = set()
        self._shutdown_event = threading.Event()

        self._pending_lock = threading.Lock()
        self._pending: dict[str, queue.Queue] = {}

        self._monitor_started = False
        atexit.register(self.shutdown)

    def shutdown(self) -> None:
        if self._shutdown_event.is_set():
            return
        self._shutdown_event.set()
        with self._lock:
            in_q = self._in_q
            proc = self._process
        if in_q is not None:
            try:
                in_q.put(None)
            except Exception:
                pass
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
            last_pid: int | None = None
            while not self._shutdown_event.is_set():
                try:
                    self.ensure_running()
                    with self._lock:
                        proc = self._process
                        pid = proc.pid if proc is not None else None
                    if pid and pid != last_pid:
                        self.send_command("warmup", {}, timeout_seconds=600)
                        last_pid = pid
                except Exception:
                    pass
                time.sleep(2)

        t = threading.Thread(target=loop, name="TextSnapWorkerMonitor", daemon=True)
        t.start()

    def ensure_running(self) -> None:
        if self._shutdown_event.is_set():
            return
        with self._lock:
            if self._process is not None and self._process.is_alive():
                return
            self._start_worker_locked()

    def submit_task(self, task_id: str, file_path: str, file_type: str) -> None:
        self.ensure_running()
        with self._lock:
            self._inflight.add(task_id)
            in_q = self._in_q
        if in_q is None:
            raise RuntimeError("worker未就绪")
        in_q.put({"task_id": task_id, "file_path": file_path, "file_type": file_type})

    def send_command(self, kind: str, payload: dict[str, Any], timeout_seconds: int = 20) -> dict[str, Any]:
        command_id = uuid.uuid4().hex
        response_q: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[command_id] = response_q
        self.ensure_running()
        with self._lock:
            in_q = self._in_q
        if in_q is None:
            with self._pending_lock:
                self._pending.pop(command_id, None)
            return {"success": False, "error": "worker未就绪", "command_id": command_id}
        in_q.put({"kind": kind, "command_id": command_id, "payload": payload})
        try:
            return response_q.get(timeout=timeout_seconds)
        except Exception:
            with self._pending_lock:
                self._pending.pop(command_id, None)
            return {"success": False, "error": "worker响应超时", "command_id": command_id}

    def _start_worker_locked(self) -> None:
        self._gen += 1
        local_gen = self._gen

        self._ctx = multiprocessing.get_context("spawn")
        self._in_q = self._ctx.Queue()
        self._out_q = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_subprocess_worker_main,
            args=(self._in_q, self._out_q, self._api_base_url),
            daemon=True,
        )
        self._process.start()

        def reader_loop() -> None:
            while True:
                with self._lock:
                    if local_gen != self._gen:
                        return
                    proc = self._process
                    out_q = self._out_q
                if proc is None or out_q is None:
                    return
                try:
                    msg = out_q.get(timeout=0.5)
                except Exception:
                    if proc is not None and not proc.is_alive():
                        self._handle_worker_crash(proc)
                        return
                    continue
                self._dispatch_worker_message(msg)

        self._reader_thread = threading.Thread(
            target=reader_loop, name="TextSnapWorkerReader", daemon=True
        )
        self._reader_thread.start()

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

    def _handle_worker_crash(self, dead_proc: multiprocessing.Process | None = None) -> None:
        try:
            if dead_proc is not None:
                logger.error(
                    f"处理进程退出: pid={getattr(dead_proc, 'pid', None)}, exitcode={getattr(dead_proc, 'exitcode', None)}"
                )
            else:
                logger.error("处理进程退出")
        except Exception:
            pass

        with self._lock:
            inflight = list(self._inflight)
            self._inflight.clear()
            self._process = None
            self._in_q = None
            self._out_q = None
            self._ctx = None
            self._gen += 1

        with self._pending_lock:
            pending = list(self._pending.items())
            self._pending.clear()

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

        for command_id, q in pending:
            try:
                q.put({"type": "command_result", "command_id": command_id, "success": False, "error": "worker已崩溃"})
            except Exception:
                pass


def _subprocess_worker_main(in_q: Any, out_q: Any, api_base_url: str) -> None:
    from srcProject.main_process_sequence import get_model_manager as worker_get_model_manager
    from srcProject.main_process_sequence import main as process_main

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
        self._cancel_conv_ids: set[str] = set()

    def mark_cancel(self, conv_id: str | None, request_id: str | None) -> None:
        with self._cancel_lock:
            if request_id:
                self._cancel_request_ids.add(str(request_id))
            if conv_id:
                self._cancel_conv_ids.add(str(conv_id))

    def clear_cancel(self, conv_id: str | None, request_id: str | None) -> None:
        with self._cancel_lock:
            if request_id:
                self._cancel_request_ids.discard(str(request_id))
            if conv_id:
                self._cancel_conv_ids.discard(str(conv_id))

    def is_cancelled(self, conv_id: str | None, request_id: str | None) -> bool:
        with self._cancel_lock:
            if request_id and str(request_id) in self._cancel_request_ids:
                return True
            if conv_id and str(conv_id) in self._cancel_conv_ids:
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


def init_mimetypes() -> None:
    mimetypes.add_type("image/webp", ".webp")
    mimetypes.add_type("image/svg+xml", ".svg")


def get_project_root() -> Path:
    root = find_project_root()
    if root is None:
        raise RuntimeError("无法定位项目根目录")
    return Path(root)
