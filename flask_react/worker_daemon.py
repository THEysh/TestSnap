from __future__ import annotations

import multiprocessing
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse
import queue
import threading
import time
import uuid
from typing import Any

from multiprocessing.connection import Listener
from dotenv import load_dotenv


class WorkerDaemon:
    def __init__(self, api_base_url: str, host: str, port: int, authkey: bytes) -> None:
        self._api_base_url = api_base_url
        self._host = host
        self._port = port
        self._authkey = authkey

        self._lock = threading.Lock()
        self._shutdown = threading.Event()

        self._active: dict[str, Any] | None = None
        self._standby: dict[str, Any] | None = None
        self._slot_seq = 0

        self._inflight: set[str] = set()

        self._pending_lock = threading.Lock()
        self._pending: dict[str, queue.Queue] = {}

        self._conn_lock = threading.Lock()
        self._conn: Any | None = None
        self._send_q: queue.Queue = queue.Queue()
        self._sender: threading.Thread | None = None

    def serve_forever(self) -> None:
        self._ensure_workers()
        with Listener((self._host, self._port), authkey=self._authkey) as listener:
            while not self._shutdown.is_set():
                try:
                    conn = listener.accept()
                except Exception:
                    time.sleep(0.2)
                    continue
                with self._conn_lock:
                    if self._conn is not None:
                        try:
                            self._conn.close()
                        except Exception:
                            pass
                    self._conn = conn
                if self._sender is None or not self._sender.is_alive():
                    self._sender = threading.Thread(target=self._send_loop, name="TextSnapDaemonSender", daemon=True)
                    self._sender.start()
                try:
                    self._recv_loop(conn)
                finally:
                    with self._conn_lock:
                        if self._conn is conn:
                            self._conn = None
                    try:
                        conn.close()
                    except Exception:
                        pass

    def _send_loop(self) -> None:
        while not self._shutdown.is_set():
            try:
                msg = self._send_q.get(timeout=0.5)
            except Exception:
                continue
            with self._conn_lock:
                conn = self._conn
            if conn is None:
                continue
            try:
                conn.send(msg)
            except Exception:
                with self._conn_lock:
                    if self._conn is conn:
                        self._conn = None

    def _recv_loop(self, conn: Any) -> None:
        while not self._shutdown.is_set():
            try:
                job = conn.recv()
            except EOFError:
                return
            except Exception:
                return
            if not isinstance(job, dict):
                continue
            kind = job.get("kind")
            if kind == "task":
                task_id = str(job.get("task_id") or "")
                file_path = str(job.get("file_path") or "")
                file_type = str(job.get("file_type") or "")
                if not task_id or not file_path or not file_type:
                    continue
                with self._lock:
                    self._inflight.add(task_id)
                    active = self._active
                if not active:
                    self._send_q.put({"type": "done", "task_id": task_id, "success": False, "error": "worker未就绪"})
                    continue
                active["in_q"].put({"task_id": task_id, "file_path": file_path, "file_type": file_type})
                continue
            if kind == "command":
                command_kind = str(job.get("command_kind") or "")
                command_id = str(job.get("command_id") or "")
                payload = job.get("payload") or {}
                with self._lock:
                    active = self._active
                if not command_kind or not command_id or not active:
                    self._send_q.put(
                        {
                            "type": "command_result",
                            "command_id": command_id,
                            "success": False,
                            "error": "worker未就绪",
                        }
                    )
                    continue
                active["in_q"].put({"kind": command_kind, "command_id": command_id, "payload": payload})
                continue

    def _ensure_workers(self) -> None:
        with self._lock:
            if not self._active or not self._active.get("proc") or not self._active["proc"].is_alive():
                self._active = self._start_worker_locked("active")
            if not self._standby or not self._standby.get("proc") or not self._standby["proc"].is_alive():
                self._standby = self._start_worker_locked("standby")

        self._warm_slot(self._active)
        self._warm_slot(self._standby)

    def _warm_slot(self, slot: dict[str, Any] | None) -> None:
        if not slot:
            return
        if slot.get("warmed"):
            return
        command_id = f"warmup_{uuid.uuid4().hex}"
        q: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[command_id] = q
        slot["in_q"].put({"kind": "warmup", "command_id": command_id, "payload": {}})
        try:
            q.get(timeout=600)
            with self._lock:
                if slot.get("role") == "active" and self._active and self._active.get("slot_id") == slot.get("slot_id"):
                    self._active["warmed"] = True
                if slot.get("role") == "standby" and self._standby and self._standby.get("slot_id") == slot.get("slot_id"):
                    self._standby["warmed"] = True
        except Exception:
            with self._pending_lock:
                self._pending.pop(command_id, None)

    def _start_worker_locked(self, role: str) -> dict[str, Any]:
        self._slot_seq += 1
        slot_id = self._slot_seq
        ctx = multiprocessing.get_context("spawn")
        in_q = ctx.Queue()
        out_q = ctx.Queue()
        from flask_react.services import _subprocess_worker_main

        proc = ctx.Process(
            target=_subprocess_worker_main,
            args=(in_q, out_q, self._api_base_url),
            daemon=False,
        )
        proc.start()

        def reader_loop() -> None:
            while not self._shutdown.is_set():
                try:
                    msg = out_q.get(timeout=0.5)
                except Exception:
                    if proc is not None and not proc.is_alive():
                        self._handle_crash(role, slot_id, proc)
                        return
                    continue
                if isinstance(msg, dict) and msg.get("type") == "command_result":
                    command_id = msg.get("command_id")
                    if command_id:
                        with self._pending_lock:
                            q = self._pending.pop(str(command_id), None)
                        if q is not None:
                            try:
                                q.put(msg)
                            except Exception:
                                pass
                            continue
                self._send_q.put(msg)
                if isinstance(msg, dict) and msg.get("type") == "done":
                    task_id = msg.get("task_id")
                    if task_id:
                        with self._lock:
                            self._inflight.discard(str(task_id))

        reader = threading.Thread(target=reader_loop, name=f"TextSnapDaemonWorkerReader-{role}-{slot_id}", daemon=True)
        reader.start()
        return {"role": role, "slot_id": slot_id, "ctx": ctx, "in_q": in_q, "out_q": out_q, "proc": proc, "reader": reader, "warmed": False}

    def _handle_crash(self, role: str, slot_id: int, dead_proc: multiprocessing.Process | None) -> None:
        if role == "standby":
            with self._lock:
                if self._standby and self._standby.get("slot_id") == slot_id:
                    self._standby = None
            try:
                self._ensure_workers()
            except Exception:
                pass
            return

        inflight: list[str]
        with self._lock:
            inflight = list(self._inflight)
            self._inflight.clear()
            if self._active and self._active.get("slot_id") == slot_id:
                self._active = None
            if self._standby and self._standby.get("proc") and self._standby["proc"].is_alive():
                self._active = self._standby
                self._active["role"] = "active"
                self._standby = None
        for task_id in inflight:
            self._send_q.put({"type": "done", "task_id": task_id, "success": False, "error": "处理进程崩溃（0xC0000005），任务已中止"})
        try:
            self._ensure_workers()
        except Exception:
            pass


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    port = int(os.getenv("PORT", "7861"))
    base_url = os.getenv("BASE_URL", "")
    if base_url:
        parsed = urlparse(base_url.strip())
        if not parsed.scheme and not parsed.netloc:
            parsed = urlparse(f"http://{base_url.strip()}")
        netloc = parsed.netloc or ""
        if ":" not in netloc:
            netloc = f"{netloc}:{port}"
        base_root = urlunparse((parsed.scheme or "http", netloc, "", "", "", ""))
        api_base_url = f"{base_root}/api"
    else:
        api_base_url = f"http://127.0.0.1:{port}/api"
    host = os.getenv("HOST", "0.0.0.0")
    daemon_port = int(os.getenv("WORKER_PORT", "7862"))
    authkey = (os.getenv("WORKER_AUTHKEY", "textsnap") or "textsnap").encode("utf-8")
    WorkerDaemon(api_base_url=api_base_url, host=host, port=daemon_port, authkey=authkey).serve_forever()


if __name__ == "__main__":
    main()
