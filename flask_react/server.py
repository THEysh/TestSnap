from __future__ import annotations
import os
from flask_react.app import create_app


app = create_app()


def main() -> None:
    port = int(os.getenv("TEXTSNAP_PORT", str(app.config.get("PORT", 7861))))
    project_root = app.config.get("PROJECT_ROOT")
    print(f"Flask服务器启动在端口: {port}")
    print(f"项目根目录: {project_root}")
    print(f"API地址: http://localhost:{port}/api/markdown")
    print(f"文件服务: http://localhost:{port}/api/files/<文件路径>")
    print(f"健康检查: http://localhost:{port}/api/health")
    print(f"任务进度查询: http://localhost:{port}/api/task/progress/<任务ID>")
    print(f"任务列表: http://localhost:{port}/api/task/list")
    print(f"图片上传: http://localhost:{port}/api/image/upload")
    print(f"图片处理: http://localhost:{port}/api/image/process")
    print(f"PDF上传: http://localhost:{port}/api/pdf/upload")
    print(f"PDF处理: http://localhost:{port}/api/pdf/process")
    print(f"对话聊天： http://localhost:{port}/api/chat/stream")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

