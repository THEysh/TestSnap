import http.server
import socketserver
import os
from srcProject.utlis.common import find_project_root

PORT = 7861

project_root = find_project_root()
# 将工作目录切换到项目根目录
os.chdir(project_root)
# 这行代码现在变得很简单，因为它位于正确的目录下
index_html_path = 'gradio_demo/index.html'
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 无需再进行 os.chdir()
        # 你的逻辑只需处理 self.path
        if self.path == '/':
            self.path = '/' + index_html_path  # 添加一个斜杠，确保路径正确
        # 接下来，让父类自行处理所有文件
        super().do_GET()

Handler = CustomHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"serving markdown web server at port: {PORT}")
    print(f"http://localhost:{PORT}")
    print(f"Web server root directory is: {os.getcwd()}") # 使用 os.getcwd() 确认
    httpd.serve_forever()