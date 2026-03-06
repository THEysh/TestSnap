from __future__ import annotations

import json
import queue
from pathlib import Path
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, request, send_from_directory

from flask_react.log import TASK_PROCESS, get_task_stream, logger, remove_task_stream
from flask_react.services import safe_resolve_under_root


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _get_services() -> tuple[Any, Any, Any, Any]:
    worker = current_app.extensions["worker_manager"]
    file_service = current_app.extensions["file_service"]
    markdown_service = current_app.extensions["markdown_service"]
    chat_service = current_app.extensions["chat_service"]
    return worker, file_service, markdown_service, chat_service


@api_bp.get("/task/progress/<task_id>")
def get_task_progress(task_id: str):
    try:
        if task_id not in TASK_PROCESS:
            return jsonify({"success": False, "error": "任务不存在或已完成"}), 404
        task_info = TASK_PROCESS[task_id].copy()
        return jsonify(
            {
                "success": True,
                "task_id": task_id,
                "progress": task_info.get("progress", 0),
                "status": task_info.get("status", "unknown"),
                "message": task_info.get("message", ""),
                "result": task_info.get("result"),
                "updated_at": task_info.get("updated_at"),
            }
        )
    except Exception as e:
        logger.error(f"获取任务进度失败 {task_id}: {e}")
        return jsonify({"success": False, "error": f"获取进度失败: {e}"}), 500


@api_bp.get("/task/list")
def list_tasks():
    try:
        tasks = []
        for task_id, task_info in TASK_PROCESS.items():
            tasks.append(
                {
                    "task_id": task_id,
                    "progress": task_info.get("progress", 0),
                    "status": task_info.get("status", "unknown"),
                    "message": task_info.get("message", ""),
                    "created_at": task_info.get("created_at"),
                    "updated_at": task_info.get("updated_at"),
                }
            )
        return jsonify({"success": True, "tasks": tasks, "total": len(tasks)})
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        return jsonify({"success": False, "error": f"获取任务列表失败: {e}"}), 500


@api_bp.get("/task/ocr/stream/<task_id>")
def stream_ocr(task_id: str):
    task_stream = get_task_stream(task_id)
    if not task_stream:
        return jsonify({"success": False, "error": "任务不存在或已完成"}), 404

    def sync_generator():
        try:
            while True:
                try:
                    payload = task_stream.get(timeout=1)
                except queue.Empty:
                    yield ":\n\n"
                    continue
                if isinstance(payload, dict) and payload.get("type") == "done":
                    yield "event: done\ndata: [DONE]\n\n"
                    break
                if not isinstance(payload, dict):
                    payload = {"type": "append", "content": str(payload)}
                json_str = json.dumps(payload, ensure_ascii=False)
                yield f"data: {json_str}\n\n"
        finally:
            remove_task_stream(task_id)

    resp = Response(sync_generator(), mimetype="text/event-stream")
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


@api_bp.post("/markdown")
def get_markdown():
    try:
        data = request.get_json(force=True, silent=True) or {}
        result, status = _get_services()[2].load_markdown(str(data.get("path") or ""))
        return jsonify(result), status
    except Exception as e:
        return jsonify({"success": False, "error": f"服务器内部错误: {e}"}), 500


@api_bp.get("/files/<path:filename>")
def serve_file(filename: str):
    try:
        project_root: Path = current_app.config["PROJECT_ROOT"]
        full_path = safe_resolve_under_root(project_root, filename)
        if full_path is None:
            return jsonify({"success": False, "error": "文件路径不在项目目录内"}), 403
        if not full_path.exists():
            return jsonify({"success": False, "error": "文件不存在"}), 404
        return send_from_directory(str(full_path.parent), full_path.name)
    except Exception as e:
        return jsonify({"success": False, "error": f"文件服务错误: {e}"}), 500


@api_bp.post("/pdf/upload")
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400
    _, file_service, _, _ = _get_services()
    result = file_service.upload(request.files["file"], "pdf")
    status_code = 200 if result.get("success") else 400 if "未选择文件" in str(result.get("error", "")) else 500
    return jsonify(result), status_code


@api_bp.post("/pdf/process")
def process_uploaded_pdf():
    try:
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"接收到PDF处理请求: {data}")
        if not data or "filename" not in data:
            return jsonify({"success": False, "error": "请提供文件名"}), 400
        _, file_service, _, _ = _get_services()
        result = file_service.process_async(str(data["filename"]), "pdf")
        err = str(result.get("error", ""))
        if result.get("success"):
            status_code = 200
        elif "未选择文件" in err or "请提供文件名" in err:
            status_code = 400
        elif "文件不存在" in err:
            status_code = 404
        else:
            status_code = 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"PDF处理请求异常: {e}")
        return jsonify({"success": False, "error": f"处理失败: {e}"}), 500


@api_bp.get("/pdf/list")
def list_pdfs():
    try:
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        original_files = []
        if upload_folder.exists():
            for child in upload_folder.iterdir():
                if child.is_file() and child.suffix.lower() == ".pdf":
                    stat = child.stat()
                    original_files.append(
                        {"filename": child.name, "size": stat.st_size, "modified": stat.st_mtime}
                    )
        return jsonify({"success": True, "original_files": original_files, "processed_files": []})
    except Exception as e:
        return jsonify({"success": False, "error": f"获取文件列表失败: {e}"}), 500


@api_bp.post("/image/upload")
def upload_image():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "没有上传文件"}), 400
    _, file_service, _, _ = _get_services()
    result = file_service.upload(request.files["file"], "image")
    status_code = 200 if result.get("success") else 400 if "未选择文件" in str(result.get("error", "")) else 500
    return jsonify(result), status_code


@api_bp.post("/image/process")
def process_uploaded_image():
    try:
        data = request.get_json(force=True, silent=True) or {}
        logger.info(f"接收到图片处理请求: {data}")
        if not data or "filename" not in data:
            return jsonify({"success": False, "error": "请提供文件名"}), 400
        _, file_service, _, _ = _get_services()
        result = file_service.process_async(str(data["filename"]), "image")
        err = str(result.get("error", ""))
        if result.get("success"):
            status_code = 200
        elif "未选择文件" in err or "请提供文件名" in err:
            status_code = 400
        elif "文件不存在" in err:
            status_code = 404
        else:
            status_code = 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"图片处理请求异常: {e}")
        return jsonify({"success": False, "error": f"处理失败: {e}"}), 500


@api_bp.get("/health")
def health_check():
    project_root = current_app.config["PROJECT_ROOT"]
    return jsonify({"status": "healthy", "project_root": str(project_root), "active_tasks": len(TASK_PROCESS)})


@api_bp.post("/update/model_config")
def update_model_config():
    try:
        data = request.get_json(force=True, silent=True)
        logger.info(f"接收到更新模型配置处理请求: {data}")
        if not isinstance(data, dict):
            return jsonify({"status": "error", "message": "请求体格式不正确，需要一个JSON对象"}), 400

        read_model = data.get("read_model")
        ocr_api_model = data.get("ocr_api_model")
        if not read_model and not ocr_api_model:
            return jsonify({"status": "error", "message": "未提供任何模型配置进行更新"}), 400
        if ocr_api_model and (not isinstance(ocr_api_model, dict) or not ocr_api_model.get("model_name")):
            return jsonify({"status": "error", "message": "ocr_api_model配置缺失关键字段 (model_name)"}), 400

        worker, _, _, _ = _get_services()
        resp = worker.send_command("update_config", {"read_model": read_model, "ocr_api_model": ocr_api_model})
        if not resp or not resp.get("success"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"模型配置更新失败: {(resp or {}).get('error') if isinstance(resp, dict) else '未知错误'}",
                    }
                ),
                500,
            )
        updated = resp.get("updated") or {}
        update_results = {}
        if read_model:
            update_results["read_model"] = {"model_name": read_model, "updated": updated.get("read_model", False)}
        if ocr_api_model:
            update_results["ocr_api_model"] = {
                "model_name": ocr_api_model.get("model_name"),
                "api_name": ocr_api_model.get("api_name"),
                "updated": updated.get("ocr_api_model", False),
            }
        return jsonify({"status": "success", "message": "模型配置更新完成", "details": update_results}), 200
    except Exception as e:
        logger.error(f"处理更新模型配置请求时发生错误: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"处理请求时发生错误: {e}"}), 500


@api_bp.post("/chat/stream")
def api_chat_stream():
    try:
        data = request.get_json(force=True, silent=True) or {}
        messages = data.get("messages") or []
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400

        enable_reasoning = bool(data.get("enable_reasoning", False))
        model_name = data.get("model_name", None)
        conv_id = data.get("conv_id", None)
        request_id = data.get("request_id", None)

        chat_service = _get_services()[3]
        resp = Response(
            chat_service.stream_events(messages, enable_reasoning, model_name, conv_id, request_id),
            mimetype="text/event-stream",
        )
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Connection"] = "keep-alive"
        resp.headers["X-Accel-Buffering"] = "no"
        return resp
    except Exception as e:
        logger.error(f"/api/chat/stream 失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.post("/chat")
def api_chat():
    try:
        data = request.get_json(force=True, silent=True) or {}
        messages = data.get("messages") or []
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({"success": False, "error": "messages 不能为空"}), 400
        enable_reasoning = bool(data.get("enable_reasoning", False))
        model_name = data.get("model_name", None)
        chat_service = _get_services()[3]
        result = chat_service.chat_once(messages, enable_reasoning, model_name)
        return jsonify(result), 200 if result.get("success") else 500
    except Exception as e:
        logger.error(f"/api/chat 失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.post("/chat/cancel")
def api_chat_cancel():
    try:
        data = request.get_json(force=True, silent=True) or {}
        conv_id = data.get("conv_id", None)
        request_id = data.get("request_id", None)
        if not conv_id and not request_id:
            return jsonify({"success": False, "error": "conv_id 或 request_id 不能为空"}), 400
        chat_service = _get_services()[3]
        chat_service.mark_cancel(conv_id, request_id)
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error(f"/api/chat/cancel 失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
