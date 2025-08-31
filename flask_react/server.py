from srcProject.main_process_sequence import main
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os
import mimetypes
import logging
from srcProject.utlis.common import find_project_root, to_relative_path
from werkzeug.utils import secure_filename
import uuid
import nest_asyncio
import asyncio
nest_asyncio.apply()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TextSnapServer')
app = Flask(__name__)

CORS(app)  # 允许跨域请求
# 获取项目根目录
project_root = find_project_root()
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
        'process_func': lambda path: process_pdf_image(path),
        'success_message': 'PDF处理完成'
    },
    'image': {
        'upload_folder': IMAGE_UPLOAD_FOLDER,
        'allowed_extensions': ALLOWED_IMAGE_EXTENSIONS,
        'process_func': lambda path: process_pdf_image(path),
        'success_message': '图片处理完成'
    }
}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['IMAGE_UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
@app.route('/api/markdown', methods=['POST'])
def get_markdown():
    """
    接收Markdown文件路径，返回文件内容
    """
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
        return send_from_directory(directory, file_name)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件服务错误: {str(e)}'
        }), 500

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

# 通用文件处理函数
def process_file(filename, file_type):
    """
    通用文件处理函数
    :param filename: 文件名
    :param file_type: 文件类型 ('pdf' 或 'image')
    :return: 包含处理结果的字典
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
            return {'success': False, 'error': '文件不存在'}\
            
        # 处理文件
        result = config['process_func'](file_path)
        
        if result['success']:
            return {
                'success': True,
                'message': config['success_message'],
                'original_file': filename,
                'processed_file': result['processed_filename'],
                'processing_info': result['processing_info'],
                'md_path': result['md_path']
            }
        else:
            return {'success': False, 'error': result['error']}
            
    except Exception as e:
        logger.error(f"{file_type}文件处理失败: {str(e)}")
        return {'success': False, 'error': f'处理失败: {str(e)}'}

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

def process_pdf_image(file_path):
    try:
        loop = asyncio.get_event_loop()  # 获取当前 event loop
        md_save_path, visualize_path = loop.run_until_complete(main(file_path))

        if not os.path.isfile(visualize_path):
            return {'success': False, 'error': '路径不存在，处理失败'}

        visualize_relative_path = to_relative_path(visualize_path)
        md_relative_path = to_relative_path(md_save_path)

        return {
            'success': True,
            'processed_path': visualize_relative_path,
            'processed_filename': visualize_relative_path,
            'md_path': md_relative_path,
            'processing_info': {
                'method': '示例处理',
                'description': '示例处理',
                'file_size': os.path.getsize(visualize_path)
            }
        }

    except Exception as e:
        import traceback
        logger.error(f"process_pdf_image 异常:\n{traceback.format_exc()}")
        return {'success': False, 'error': str(e)}

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
    处理已上传的PDF文件
    """
    try:
        data = request.get_json()
        logger.info(f"接收到PDF处理请求: {data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400
        
        result = process_file(data['filename'], 'pdf')
        status_code = 200 if result['success'] else 400 if 'error' in result and ('未选择文件' in result['error'] or '请提供文件名' in result['error']) else 404 if 'error' in result and '文件不存在' in result['error'] else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"PDF处理请求异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

@app.route('/api/pdf/view/<filename>')
def view_pdf(filename):
    """
    查看PDF文件
    """
    logger.info(f"请求查看PDF文件: {filename}")
    response, error = view_file(filename, 'pdf')
    if error:
        status_code = 404 if error['error'] == '文件不存在' else 500
        return jsonify(error), status_code
    return response

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
        'project_root': project_root
    })

# 新增：图片处理API
@app.route('/api/image/process', methods=['POST'])
def process_uploaded_image():
    """
    处理已上传的图片文件
    """
    try:
        data = request.get_json()
        logger.info(f"接收到图片处理请求: {data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400
        
        result = process_file(data['filename'], 'image')
        status_code = 200 if result['success'] else 400 if 'error' in result and ('未选择文件' in result['error'] or '请提供文件名' in result['error']) else 404 if 'error' in result and '文件不存在' in result['error'] else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"图片处理请求异常: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

# 新增：图片查看API
@app.route('/api/image/view/<filename>')
def view_image(filename):
    """
    查看图片文件
    """
    logger.info(f"请求查看图片文件: {filename}")
    response, error = view_file(filename, 'image')
    if error:
        status_code = 404 if error['error'] == '文件不存在' else 500
        return jsonify(error), status_code
    return response

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
    # 新增：图片API信息
    print(f"图片上传: http://localhost:{PORT}/api/image/upload")
    print(f"图片处理: http://localhost:{PORT}/api/image/process")
    print(f"图片查看: http://localhost:{PORT}/api/image/view/<文件名>")
    # PDF API信息
    print(f"PDF上传: http://localhost:{PORT}/api/pdf/upload")
    print(f"PDF处理: http://localhost:{PORT}/api/pdf/process")
    print(f"PDF查看: http://localhost:{PORT}/api/pdf/view/<文件名>")

    app.run(host='0.0.0.0', port=PORT, debug=True)