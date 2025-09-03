import time
import threading
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
# 允许跨域请求，在开发环境下很重要
CORS(app)

# 存储任务进度的字典，键为任务ID，值为进度
# 在实际应用中，你可能需要一个更健壮的方案，比如使用数据库或Redis
task_progress = {}


def heavy_computation(task_id):
    """模拟一个耗时的复杂运算"""
    total_steps = 100
    for i in range(total_steps + 1):
        # 模拟计算
        time.sleep(0.1)
        # 更新进度
        progress = int((i / total_steps) * 100)
        task_progress[task_id] = progress
        print(f"Task {task_id}: {progress}%")
    print(f"Task {task_id} finished.")


@app.route('/start_task', methods=['POST'])
def start_task():
    """启动耗时任务"""
    task_id = str(int(time.time()))  # 使用时间戳作为简单的任务ID

    # 在新线程中启动任务，避免阻塞主线程
    thread = threading.Thread(target=heavy_computation, args=(task_id,))
    thread.start()

    # 初始化进度
    task_progress[task_id] = 0

    return jsonify({'task_id': task_id, 'message': 'Task started'})


@app.route('/get_progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """查询任务进度"""
    progress = task_progress.get(task_id, -1)  # 如果任务ID不存在，返回-1
    return jsonify({'progress': progress})


if __name__ == '__main__':
    app.run(debug=True, port=5000)