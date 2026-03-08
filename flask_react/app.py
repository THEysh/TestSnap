from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import nest_asyncio
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from flask_react.routes import api_bp, generate_bp
from flask_react.services import (
    ChatService,
    FileRetention,
    FileService,
    MarkdownService,
    WorkerManager,
    get_project_root,
    init_mimetypes,
)
from srcProject.config.settings import CHAT_API_KEY, CHAT_MODEL_NAME, CHAT_URL


def create_app() -> Flask:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    nest_asyncio.apply()
    init_mimetypes()

    app = Flask(__name__)
    CORS(app)

    project_root = get_project_root()
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

    retention = FileRetention(retention_seconds=10800)
    worker = WorkerManager(api_base_url=api_base_url, on_result_directory=retention.schedule_directory_deletion)
    file_service = FileService(project_root=project_root, retention=retention, worker=worker)
    markdown_service = MarkdownService(project_root=project_root, port=port)
    chat_service = ChatService(api_keys=CHAT_API_KEY, base_url=CHAT_URL, model_name=CHAT_MODEL_NAME)

    file_service.ensure_directories()
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["PROJECT_ROOT"] = project_root
    app.config["PORT"] = port
    app.config["UPLOAD_FOLDER"] = str(project_root / "srcProject" / "output" / "visualizations" / "uploads" / "pdfs")
    app.config["IMAGE_UPLOAD_FOLDER"] = str(
        project_root / "srcProject" / "output" / "visualizations" / "uploads" / "images"
    )

    app.extensions["worker_manager"] = worker
    app.extensions["file_service"] = file_service
    app.extensions["markdown_service"] = markdown_service
    app.extensions["chat_service"] = chat_service

    worker.start_monitor()
    app.register_blueprint(api_bp)
    app.register_blueprint(generate_bp)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "API接口不存在"}), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"success": False, "error": "服务器内部错误"}), 500

    return app
