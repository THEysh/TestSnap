import json
import queue
from flask_react.log import TASK_PROCESS, update_task_progress, complete_task, logger, init_task_stream, get_task_stream, push_task_stream, close_task_stream, remove_task_stream
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os
import mimetypes
import shutil
import threading
import multiprocessing
import time
from srcProject.utlis.common import find_project_root, to_relative_path
from werkzeug.utils import secure_filename
import uuid
import nest_asyncio
import asyncio
from srcProject.models.chat_model import SiliconChatModel
from srcProject.config.settings import CHAT_API_KEY, CHAT_URL, CHAT_MODEL_NAME

nest_asyncio.apply()
app = Flask(__name__)

CORS(app)  # 允许跨域请求
# 获取项目根目录
project_root = find_project_root()
API_BASE_URL = os.getenv('TEXTSNAP_API_BASE_URL', 'http://127.0.0.1:7861/api')
# 设置静态文件类型
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/svg+xml', '.svg')

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(project_root, 'srcProject/output/visualizations/uploads', 'pdfs')
# 新增：图片上传配置
IMAGE_UPLOAD_FOLDER = os.path.join(project_root, 'srcProject/output/visualizations/uploads', 'images')

# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 定义文件类型配置映射
FILE_TYPE_CONFIG = {
    'pdf': {
        'upload_folder': UPLOAD_FOLDER,
        'allowed_extensions': ALLOWED_EXTENSIONS,
        'success_message': 'PDF处理完成'
    },
    'image': {
        'upload_folder': IMAGE_UPLOAD_FOLDER,
        'allowed_extensions': ALLOWED_IMAGE_EXTENSIONS,
        'success_message': '图片处理完成'
    }
}

_WORKER_LOCK = threading.Lock()
_WORKER_CTX = None
_WORKER_IN_Q = None
_WORKER_OUT_Q = None
_WORKER_PROCESS = None
_WORKER_READER_THREAD = None
_WORKER_GEN = 0
_WORKER_INFLIGHT = set()

def _subprocess_worker_main(in_q, out_q, api_base_url):
    from srcProject.main_process_sequence import main as process_main, get_model_manager as worker_get_model_manager
    while True:
        job = in_q.get()
        if job is None:
            break
        kind = job.get('kind') or 'process'
        if kind == 'update_config':
            command_id = job.get('command_id')
            payload = job.get('payload') or {}
            try:
                mgr = worker_get_model_manager()
                updated = {}
                read_model = payload.get('read_model')
                if read_model:
                    updated['read_model'] = mgr.change_read_model(model_name=read_model)
                ocr_api_model = payload.get('ocr_api_model')
                if isinstance(ocr_api_model, dict):
                    updated['ocr_api_model'] = mgr.change_ocr_recognizer(
                        api_name=ocr_api_model.get('api_name', None),
                        api_key=ocr_api_model.get('api_key', None),
                        base_url=ocr_api_model.get('base_url', None),
                        model_name=ocr_api_model.get('model_name', None)
                    )
                out_q.put({'type': 'command_result', 'command_id': command_id, 'success': True, 'updated': updated})
            except Exception as e:
                out_q.put({'type': 'command_result', 'command_id': command_id, 'success': False, 'error': str(e)})
            continue
        task_id = job.get('task_id')
        file_path = job.get('file_path')
        file_type = job.get('file_type')
        try:
            def progress_update(local_task_id, progress, status='processing', message=None):
                out_q.put({
                    'type': 'progress',
                    'task_id': local_task_id,
                    'progress': progress,
                    'status': status,
                    'message': message
                })
            def stream_callback(local_task_id, payload):
                out_q.put({
                    'type': 'stream',
                    'task_id': local_task_id,
                    'payload': payload
                })
            out_q.put({
                'type': 'status',
                'task_id': task_id,
                'status': 'processing',
                'message': f'正在处理{file_type}文件'
            })
            try:
                md_save_path, visualize_path = asyncio.run(
                    process_main(file_path, task_id=task_id, stream_callback=stream_callback, stream_api_base_url=api_base_url, progress_update=progress_update)
                )
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                md_save_path, visualize_path = loop.run_until_complete(
                    process_main(file_path, task_id=task_id, stream_callback=stream_callback, stream_api_base_url=api_base_url, progress_update=progress_update)
                )
                try:
                    loop.stop()
                    loop.close()
                except Exception:
                    pass
            if not os.path.isfile(visualize_path):
                raise RuntimeError('路径不存在，处理失败')
            visualize_relative_path = to_relative_path(visualize_path)
            md_relative_path = to_relative_path(md_save_path)
            try:
                result_directory = os.path.dirname(visualize_path) or os.path.dirname(md_save_path)
            except Exception:
                result_directory = None
            result = {
                'success': True,
                'processed_file': visualize_relative_path,
                'md_path': md_relative_path,
                'processing_info': {
                    'method': '示例处理',
                    'description': '示例处理',
                    'file_size': os.path.getsize(visualize_path),
                    'auto_delete_info': '该文件将在3小时后自动删除'
                }
            }
            out_q.put({
                'type': 'done',
                'task_id': task_id,
                'success': True,
                'result': result,
                'result_directory': result_directory
            })
        except Exception as e:
            out_q.put({
                'type': 'done',
                'task_id': task_id,
                'success': False,
                'error': str(e)
            })

def _start_worker_locked():
    global _WORKER_CTX, _WORKER_IN_Q, _WORKER_OUT_Q, _WORKER_PROCESS, _WORKER_READER_THREAD, _WORKER_GEN
    _WORKER_GEN += 1
    gen = _WORKER_GEN
    _WORKER_CTX = multiprocessing.get_context("spawn")
    _WORKER_IN_Q = _WORKER_CTX.Queue()
    _WORKER_OUT_Q = _WORKER_CTX.Queue()
    _WORKER_PROCESS = _WORKER_CTX.Process(
        target=_subprocess_worker_main,
        args=(_WORKER_IN_Q, _WORKER_OUT_Q, API_BASE_URL)
    )
    _WORKER_PROCESS.daemon = True
    _WORKER_PROCESS.start()

    def _reader_loop(local_gen):
        while True:
            with _WORKER_LOCK:
                if local_gen != _WORKER_GEN:
                    return
                proc = _WORKER_PROCESS
                out_q = _WORKER_OUT_Q
            if proc is None or out_q is None:
                return
            try:
                msg = out_q.get(timeout=0.5)
            except Exception:
                if proc is not None and not proc.is_alive():
                    _handle_worker_crash()
                    return
                continue
            try:
                mtype = msg.get('type')
                task_id = msg.get('task_id')
                if mtype == 'stream':
                    payload = msg.get('payload')
                    if payload is not None:
                        push_task_stream(task_id, payload)
                elif mtype == 'progress':
                    update_task_progress(task_id, msg.get('progress', 0), msg.get('status', 'processing'), msg.get('message'))
                elif mtype == 'status':
                    if task_id in TASK_PROCESS:
                        TASK_PROCESS[task_id]['status'] = msg.get('status') or TASK_PROCESS[task_id].get('status')
                        TASK_PROCESS[task_id]['message'] = msg.get('message') or TASK_PROCESS[task_id].get('message')
                        TASK_PROCESS[task_id]['updated_at'] = time.time()
                elif mtype == 'done':
                    success = msg.get('success', False)
                    if success:
                        result = msg.get('result') or {}
                        result_directory = msg.get('result_directory')
                        if result_directory and os.path.isdir(result_directory):
                            try:
                                schedule_directory_deletion(result_directory)
                            except Exception:
                                pass
                        complete_task(task_id, result)
                    else:
                        complete_task(task_id, error=msg.get('error') or '处理失败')
                    try:
                        close_task_stream(task_id)
                    except Exception:
                        pass
                    with _WORKER_LOCK:
                        _WORKER_INFLIGHT.discard(task_id)
                elif mtype == 'command_result':
                    command_id = msg.get('command_id')
                    if command_id:
                        with _WORKER_PENDING_LOCK:
                            q = _WORKER_PENDING.pop(command_id, None)
                        if q is not None:
                            try:
                                q.put(msg)
                            except Exception:
                                pass
            except Exception:
                continue

    _WORKER_READER_THREAD = threading.Thread(target=_reader_loop, args=(gen,), name='TextSnapWorkerReader')
    _WORKER_READER_THREAD.daemon = True
    _WORKER_READER_THREAD.start()

def _ensure_worker_running():
    with _WORKER_LOCK:
        if _WORKER_PROCESS is not None and _WORKER_PROCESS.is_alive():
            return
        _start_worker_locked()

def _handle_worker_crash():
    global _WORKER_PROCESS, _WORKER_IN_Q, _WORKER_OUT_Q, _WORKER_CTX, _WORKER_GEN
    with _WORKER_LOCK:
        inflight = list(_WORKER_INFLIGHT)
        _WORKER_INFLIGHT.clear()
        _WORKER_PROCESS = None
        _WORKER_IN_Q = None
        _WORKER_OUT_Q = None
        _WORKER_CTX = None
        _WORKER_GEN += 1
    with _WORKER_PENDING_LOCK:
        pending = list(_WORKER_PENDING.items())
        _WORKER_PENDING.clear()
    for task_id in inflight:
        try:
            complete_task(task_id, error='处理进程崩溃（0xC0000005），任务已中止')
        except Exception:
            pass
        try:
            close_task_stream(task_id)
        except Exception:
            pass
    for command_id, q in pending:
        try:
            q.put({'type': 'command_result', 'command_id': command_id, 'success': False, 'error': 'worker已崩溃'})
        except Exception:
            pass

_CHAT_LOCK = threading.Lock()
_CHAT_MODEL = None

def _get_chat_model():
    global _CHAT_MODEL
    if _CHAT_MODEL is not None:
        return _CHAT_MODEL
    with _CHAT_LOCK:
        if _CHAT_MODEL is None:
            _CHAT_MODEL = SiliconChatModel(api_keys=CHAT_API_KEY, base_url=CHAT_URL, model_name=CHAT_MODEL_NAME)
    return _CHAT_MODEL

_WORKER_PENDING_LOCK = threading.Lock()
_WORKER_PENDING = {}

def _send_worker_command(kind, payload, timeout_seconds=20):
    command_id = uuid.uuid4().hex
    q = queue.Queue(maxsize=1)
    with _WORKER_PENDING_LOCK:
        _WORKER_PENDING[command_id] = q
    _ensure_worker_running()
    with _WORKER_LOCK:
        in_q = _WORKER_IN_Q
    in_q.put({
        'kind': kind,
        'command_id': command_id,
        'payload': payload
    })
    try:
        return q.get(timeout=timeout_seconds)
    except Exception:
        with _WORKER_PENDING_LOCK:
            _WORKER_PENDING.pop(command_id, None)
        return {'success': False, 'error': 'worker响应超时', 'command_id': command_id}


# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

@app.route('/api/task/progress/<task_id>', methods=['GET'])
def get_task_progress(task_id):
    """
    获取任务进度
    """
    try:
        if task_id not in TASK_PROCESS:
            return jsonify({
                'success': False,
                'error': '任务不存在或已完成'
            }), 404
        task_info = TASK_PROCESS[task_id].copy()
        return jsonify({
            'success': True,
            'task_id': task_id,
            'progress': task_info.get('progress', 0),
            'status': task_info.get('status', 'unknown'),
            'message': task_info.get('message', ''),
            'result': task_info.get('result'),
            'updated_at': task_info.get('updated_at')
        })
    except Exception as e:
        logger.error(f"获取任务进度失败 {task_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取进度失败: {str(e)}'
        }), 500


@app.route('/api/task/list', methods=['GET'])
def list_tasks():
    """
    获取所有任务列表
    """
    try:
        tasks = []
        for task_id, task_info in TASK_PROCESS.items():
            tasks.append({
                'task_id': task_id,
                'progress': task_info.get('progress', 0),
                'status': task_info.get('status', 'unknown'),
                'message': task_info.get('message', ''),
                'created_at': task_info.get('created_at'),
                'updated_at': task_info.get('updated_at')
            })

        return jsonify({
            'success': True,
            'tasks': tasks,
            'total': len(tasks)
        })
    except Exception as e:
        logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'获取任务列表失败: {str(e)}'
        }), 500

@app.route('/api/task/ocr/stream/<task_id>', methods=['GET'])
def stream_ocr(task_id):
    task_stream = get_task_stream(task_id)
    if not task_stream:
        return jsonify({'success': False, 'error': '任务不存在或已完成'}), 404
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
    resp = Response(sync_generator(), mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Connection'] = 'keep-alive'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp

@app.route('/api/markdown', methods=['POST'])
def get_markdown():
    """
    接收Markdown文件路径，返回文件内容
    """
    print("开始 '/api/markdown' ")
    try:
        data = request.get_json()

        if not data or 'path' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件路径'
            }), 400

        file_path = data['path']

        # 构建完整的文件路径
        full_path = os.path.join(project_root, file_path)

        # 安全检查：确保文件在项目根目录内
        try:
            full_path = os.path.abspath(full_path)
            project_root_abs = os.path.abspath(project_root)
            if not full_path.startswith(project_root_abs):
                return jsonify({
                    'success': False,
                    'error': '文件路径不在项目目录内'
                }), 403
        except Exception as e:
            return jsonify({
                'success': False,
                'error': '文件路径无效'
            }), 400

        # 检查文件是否存在
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': f'文件不存在: {file_path}'
            }), 404

        # 检查是否为Markdown文件
        if not full_path.endswith('.md'):
            return jsonify({
                'success': False,
                'error': '只支持Markdown文件(.md)'
            }), 400

        # 读取文件内容
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(full_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except UnicodeDecodeError:
                return jsonify({
                    'success': False,
                    'error': '文件编码格式不支持'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'读取文件失败: {str(e)}'
            }), 500

        # 获取文件的目录路径，用于图片路径处理
        file_dir = os.path.dirname(file_path)
        print("结束 '/api/markdown' ")
        return jsonify({
            'success': True,
            'content': content,
            'file_dir': file_dir,
            'file_path': file_path,
            'api_base_url': f'http://localhost:{PORT}/api/files'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'服务器内部错误: {str(e)}'
        }), 500


@app.route('/api/files/<path:filename>')
def serve_file(filename):
    """
    静态文件服务接口，用于提供图片等资源文件
    """
    print("开始 /api/files/")
    try:
        # 构建完整的文件路径
        full_path = os.path.join(project_root, filename)

        # 安全检查：确保文件在项目根目录内
        full_path = os.path.abspath(full_path)
        project_root_abs = os.path.abspath(project_root)
        if not full_path.startswith(project_root_abs):
            return jsonify({
                'success': False,
                'error': '文件路径不在项目目录内'
            }), 403

        # 检查文件是否存在
        if not os.path.exists(full_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        # 获取文件目录和文件名
        directory = os.path.dirname(full_path)
        file_name = os.path.basename(full_path)

        # 使用send_from_directory安全地提供文件
        print("结束 /api/files/")
        return send_from_directory(directory, file_name)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件服务错误: {str(e)}'
        }), 500


def schedule_file_deletion(file_path, delay_seconds=10800):
    """
    安排文件在指定分钟后被删除

    :param file_path: 文件路径
    :param delay_seconds: 延迟秒数，默认为10800秒
    """

    def delete_file():
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"文件已自动删除: {file_path}")
            except Exception as e:
                logger.error(f"删除文件失败: {file_path}, 错误: {str(e)}")

    # 创建定时器线程
    timer = threading.Timer(delay_seconds, delete_file)
    timer.daemon = True  # 设置为守护线程，避免阻止服务器关闭
    timer.start()


def schedule_directory_deletion(dir_path, delay_seconds=10800):
    """
    安排目录在指定秒后被删除
    :param dir_path: 目录路径
    :param delay_seconds: 延迟秒数，默认为10800秒
    """

    def delete_directory():
        if os.path.exists(dir_path):
            try:
                # 统计要删除的文件数量和总大小
                total_files = 0
                total_size = 0
                for root, _, files in os.walk(dir_path):
                    for file in files:
                        total_files += 1
                        total_size += os.path.getsize(os.path.join(root, file))

                # 删除目录及其内容
                shutil.rmtree(dir_path)
                logger.info(
                    f"目录已自动删除: {dir_path}, 共删除 {total_files} 个文件，总大小约 {total_size / 1024 / 1024:.2f} MB")
            except Exception as e:
                logger.error(f"删除目录失败: {dir_path}, 错误: {str(e)}")

    logger.info(f"安排目录在{delay_seconds}秒后删除: {dir_path}")
    # 创建定时器线程
    timer = threading.Timer(delay_seconds, delete_directory)
    timer.daemon = True  # 设置为守护线程，避免阻止服务器关闭
    timer.start()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


# 通用文件上传函数
def upload_file(file, file_type):
    """
    通用文件上传函数
    :param file: 上传的文件对象
    :param file_type: 文件类型 ('pdf' 或 'image')
    :return: 包含上传结果的字典
    """
    try:
        if not file or file.filename == '':
            return {'success': False, 'error': '未选择文件'}

        # 获取文件类型配置
        config = FILE_TYPE_CONFIG.get(file_type)
        if not config:
            return {'success': False, 'error': f'不支持的文件类型: {file_type}'}
        # 验证文件类型
        _, ext = os.path.splitext(file.filename.lower())
        if ext[1:] not in config['allowed_extensions']:
            supported = ', '.join(config['allowed_extensions'])
            return {'success': False, 'error': f'只支持以下文件类型: {supported}'}
        # 生成安全的文件名
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(config['upload_folder'], unique_filename)

        # 确保上传目录存在
        os.makedirs(config['upload_folder'], exist_ok=True)

        # 保存文件
        file.save(file_path)
        logger.info(f"已上传{file_type}文件: {filename} 至 {file_path}")
        # 安排xx后删除上传的文件
        schedule_file_deletion(file_path)
        # 获取文件信息
        file_size = os.path.getsize(file_path)

        return {
            'success': True,
            'message': f'{file_type}文件上传成功',
            'file_info': {
                'original_filename': filename,
                'unique_filename': unique_filename,
                'file_size': file_size,
                'file_path': file_path
            }
        }

    except Exception as e:
        logger.error(f"{file_type}文件上传失败: {str(e)}")
        return {'success': False, 'error': f'上传失败: {str(e)}'}


# 通用文件处理函数（异步版本）
def process_file_async(filename, file_type):
    """
    异步处理文件，返回任务ID
    :param filename: 文件名
    :param file_type: 文件类型 ('pdf' 或 'image')
    :return: 包含任务ID的字典
    """
    try:
        # 获取文件类型配置
        config = FILE_TYPE_CONFIG.get(file_type)
        if not config:
            return {'success': False, 'error': f'不支持的文件类型: {file_type}'}

        # 构建文件路径
        file_path = os.path.join(config['upload_folder'], filename)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {'success': False, 'error': '文件不存在'}

        # 生成任务ID
        task_id = f"{file_type}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"

        # 初始化任务进度
        TASK_PROCESS[task_id] = {
            'progress': 0,
            'status': 'started',
            'message': f'开始处理{file_type}文件',
            'file_type': file_type,
            'filename': filename,
            'created_at': time.time(),
            'updated_at': time.time()
        }
        init_task_stream(task_id)

        logger.info(f"创建任务 {task_id}: 处理{file_type}文件 {filename}")

        TASK_PROCESS[task_id]['status'] = 'queued'
        TASK_PROCESS[task_id]['message'] = f'已进入队列，等待处理{file_type}文件'
        TASK_PROCESS[task_id]['updated_at'] = time.time()

        _ensure_worker_running()
        with _WORKER_LOCK:
            _WORKER_INFLIGHT.add(task_id)
            in_q = _WORKER_IN_Q
        in_q.put({
            'task_id': task_id,
            'file_path': file_path,
            'file_type': file_type
        })

        return {
            'success': True,
            'message': f'{file_type}文件处理已启动',
            'task_id': task_id
        }

    except Exception as e:
        logger.error(f"{file_type}文件异步处理失败: {str(e)}")
        return {'success': False, 'error': f'启动处理失败: {str(e)}'}


# 通用文件查看函数
def view_file(filename, file_type):
    """
    通用文件查看函数
    :param filename: 文件名或相对路径
    :param file_type: 文件类型 ('pdf' 或 'image')
    :return: Flask响应对象或错误信息
    """
    try:
        # 获取文件类型配置
        config = FILE_TYPE_CONFIG.get(file_type)
        if not config:
            return None, {'success': False, 'error': f'不支持的文件类型: {file_type}'}

        # 检查原始文件
        original_path = os.path.join(config['upload_folder'], filename)
        if os.path.exists(original_path):
            return send_from_directory(config['upload_folder'], filename), None
        # 获取目录和文件名
        relative_full_path = os.path.join(project_root, filename)
        if os.path.exists(relative_full_path):
            directory = os.path.dirname(relative_full_path)
            file_name = os.path.basename(relative_full_path)
            return send_from_directory(directory, file_name), None

        logger.warning(f"文件不存在: {filename}, 类型: {file_type}")
        return None, {'success': False, 'error': '文件不存在'}

    except Exception as e:
        logger.error(f"{file_type}文件查看失败: {str(e)}")
        return None, {'success': False, 'error': f'文件访问错误: {str(e)}'}


@app.route('/api/chat/stream', methods=['POST'])
def api_chat_stream():
    """
    SSE 流式接口：逐片输出 data: <text>\\n\\n
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        messages = data.get('messages') or []
        if not isinstance(messages, list) or len(messages) == 0:
            return jsonify({'success': False, 'error': 'messages 不能为空'}), 400
        enable_reasoning = data.get('enable_reasoning', False)
        model_name = data.get('model_name', None)
        def sync_generator():
            try:
                loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(loop)
                except Exception:
                    pass
                agen = _get_chat_model().achat_stream(messages, enable_reasoning, model_name)
                try:
                    while True:
                        try:
                            piece = loop.run_until_complete(agen.__anext__())
                        except StopAsyncIteration:
                            break
                        if isinstance(piece, dict):
                            # 结构化输出 → 转 JSON
                            json_str = json.dumps(piece, ensure_ascii=False)
                            yield f"data: {json_str}\n\n"
                        else:
                            # 方案1：发送明确的 error 事件
                            error_msg = "返回的内容无法解析为json"
                            yield f'event: error\ndata: {json.dumps({"error": error_msg, "detail": str(piece)}, ensure_ascii=False)}\n\n'
                finally:
                    try:
                        loop.run_until_complete(agen.aclose())
                    except Exception:
                        pass
                    try:
                        loop.stop()
                        loop.close()
                    except Exception:
                        pass
                yield "event: done\ndata: [DONE]\n\n"
            except Exception as e:
                err = str(e).replace("\n", " ")
                yield f"event: error\ndata: {err}\n\n"

        resp = Response(sync_generator(), mimetype='text/event-stream')
        resp.headers['Cache-Control'] = 'no-cache'
        resp.headers['Connection'] = 'keep-alive'
        resp.headers['X-Accel-Buffering'] = 'no'
        return resp
    except Exception as e:
        logger.error(f"/api/chat/stream 失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    """
    上传PDF文件
    """
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': '没有上传文件'
        }), 400

    result = upload_file(request.files['file'], 'pdf')
    status_code = 200 if result['success'] else 400 if 'error' in result and '未选择文件' in result['error'] else 500
    return jsonify(result), status_code

@app.route('/api/pdf/process', methods=['POST'])
def process_uploaded_pdf():
    """
    处理已上传的PDF文件（异步版本）
    """
    try:
        data = request.get_json()
        logger.info(f"接收到PDF处理请求: {data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400

        result = process_file_async(data['filename'], 'pdf')
        status_code = 200 if result['success'] else 400 if 'error' in result and (
                    '未选择文件' in result['error'] or '请提供文件名' in result[
                'error']) else 404 if 'error' in result and '文件不存在' in result['error'] else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"PDF处理请求异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

@app.route('/api/pdf/list', methods=['GET'])
def list_pdfs():
    """
    列出所有PDF文件
    """
    try:
        original_files = []
        processed_files = []

        # 获取原始文件列表
        if os.path.exists(app.config['UPLOAD_FOLDER']):
            for filename in os.listdir(app.config['UPLOAD_FOLDER']):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    original_files.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'modified': os.path.getmtime(file_path)
                    })

        return jsonify({
            'success': True,
            'original_files': original_files,
            'processed_files': processed_files
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取文件列表失败: {str(e)}'
        }), 500


# 新增：图片上传API
@app.route('/api/image/upload', methods=['POST'])
def upload_image():
    """
    上传图片文件
    """
    if 'file' not in request.files:
        return jsonify({
            'success': False,
            'error': '没有上传文件'
        }), 400

    result = upload_file(request.files['file'], 'image')
    status_code = 200 if result['success'] else 400 if 'error' in result and '未选择文件' in result['error'] else 500
    return jsonify(result), status_code


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    """
    return jsonify({
        'status': 'healthy',
        'project_root': project_root,
        'active_tasks': len(TASK_PROCESS)
    })


# 新增：图片处理API（异步版本）
@app.route('/api/image/process', methods=['POST'])
def process_uploaded_image():
    """
    处理已上传的图片文件（异步版本）
    """
    try:
        data = request.get_json()
        logger.info(f"接收到图片处理请求: {data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400

        result = process_file_async(data['filename'], 'image')
        status_code = 200 if result['success'] else 400 if 'error' in result and (
                    '未选择文件' in result['error'] or '请提供文件名' in result[
                'error']) else 404 if 'error' in result and '文件不存在' in result['error'] else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"图片处理请求异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500
@app.route('/api/update/model_config', methods=['POST'])
def update_model_config():
    try:
        data = request.get_json()
        logger.info(f"接收到更新模型配置处理请求: {data}")

        if not isinstance(data, dict):
            return jsonify({"status": "error", "message": "请求体格式不正确，需要一个JSON对象"}), 400

        read_model = data.get('read_model')
        ocr_api_model = data.get('ocr_api_model')
        if not read_model and not ocr_api_model:
            return jsonify({
                "status": "error",
                "message": "未提供任何模型配置进行更新"
            }), 400

        if ocr_api_model and (not isinstance(ocr_api_model, dict) or not ocr_api_model.get('model_name')):
            return jsonify({
                "status": "error",
                "message": "ocr_api_model配置缺失关键字段 (model_name)"
            }), 400

        resp = _send_worker_command('update_config', {'read_model': read_model, 'ocr_api_model': ocr_api_model})
        if not resp or not resp.get('success'):
            return jsonify({
                "status": "error",
                "message": f"模型配置更新失败: {resp.get('error') if isinstance(resp, dict) else '未知错误'}"
            }), 500

        updated = resp.get('updated') or {}
        update_results = {}
        if read_model:
            update_results['read_model'] = {"model_name": read_model, "updated": updated.get('read_model', False)}
        if ocr_api_model:
            update_results['ocr_api_model'] = {
                "model_name": ocr_api_model.get('model_name'),
                "api_name": ocr_api_model.get('api_name'),
                "updated": updated.get('ocr_api_model', False)
            }

        return jsonify({
            "status": "success",
            "message": "模型配置更新完成",
            "details": update_results
        }), 200

    except Exception as e:
        logger.error(f"处理更新模型配置请求时发生错误: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"处理请求时发生错误: {e}"
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API接口不存在'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500



if __name__ == '__main__':
    PORT = 7861
    print(f"Flask服务器启动在端口: {PORT}")
    print(f"项目根目录: {project_root}")
    print(f"API地址: http://localhost:{PORT}/api/markdown")
    print(f"文件服务: http://localhost:{PORT}/api/files/<文件路径>")
    print(f"健康检查: http://localhost:{PORT}/api/health")
    # 新增：任务进度API信息
    print(f"任务进度查询: http://localhost:{PORT}/api/task/progress/<任务ID>")
    print(f"任务列表: http://localhost:{PORT}/api/task/list")
    # 新增：图片API信息
    print(f"图片上传: http://localhost:{PORT}/api/image/upload")
    print(f"图片处理: http://localhost:{PORT}/api/image/process")
    # PDF API信息
    print(f"PDF上传: http://localhost:{PORT}/api/pdf/upload")
    print(f"PDF处理: http://localhost:{PORT}/api/pdf/process")
    # 对话聊天
    print(f"对话聊天： http://localhost:{PORT}/api/chat/stream")

    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
