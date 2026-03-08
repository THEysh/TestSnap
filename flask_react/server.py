from __future__ import annotations
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from flask_react.app import create_app
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)

app = create_app()

def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_base_url(base_url: str, port: int) -> str:
    raw = (base_url or "").strip()
    if not raw:
        return f"http://127.0.0.1:{port}"
    parsed = urlparse(raw)
    if not parsed.scheme and not parsed.netloc:
        raw = f"http://{raw}"
        parsed = urlparse(raw)
    netloc = parsed.netloc
    if ":" not in netloc:
        netloc = f"{netloc}:{port}"
    return urlunparse((parsed.scheme or "http", netloc, "", "", "", ""))


PORT = int(os.getenv("PORT", str(app.config.get("PORT", 7861))))
HOST = str(os.getenv("HOST", "0.0.0.0"))
BASE_URL = normalize_base_url(os.getenv("BASE_URL", ""), PORT)


def main() -> None:
    project_root = app.config.get("PROJECT_ROOT")
    debug = parse_bool(os.getenv("DEBUG", None), False)
    print(f"Flask服务器启动在端口: {PORT}")
    print(f"项目根目录: {project_root}")
    print(f"API地址: {BASE_URL}/api/markdown")
    print(f"文件服务: {BASE_URL}/api/files/<文件路径>")
    print(f"健康检查: {BASE_URL}/api/health")
    print(f"任务进度查询: {BASE_URL}/api/task/progress/<任务ID>")
    print(f"任务列表: {BASE_URL}/api/task/list")
    print(f"图片上传: {BASE_URL}/api/image/upload")
    print(f"图片处理: {BASE_URL}/api/image/process")
    print(f"PDF上传: {BASE_URL}/api/pdf/upload")
    print(f"PDF处理: {BASE_URL}/api/pdf/process")
    print(f"对话聊天： {BASE_URL}/api/chat/stream")
    app.run(host=HOST, port=PORT, debug=debug, use_reloader=False)


if __name__ == "__main__":
    main()
