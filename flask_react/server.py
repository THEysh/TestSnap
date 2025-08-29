from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import mimetypes
import shutil
from pathlib import Path
from srcProject.utlis.common import find_project_root
from werkzeug.utils import secure_filename
import uuid
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 获取项目根目录
project_root = find_project_root()

# 设置静态文件类型
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/svg+xml', '.svg')

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(project_root, 'flask_react/uploads', 'pdfs')
PROCESSED_FOLDER = os.path.join(project_root, 'flask_react/uploads', 'processed')
# 新增：图片上传配置
IMAGE_UPLOAD_FOLDER = os.path.join(project_root, 'flask_react/uploads', 'images')
IMAGE_PROCESSED_FOLDER = os.path.join(project_root, 'flask_react/uploads', 'processed_images')
# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_PROCESSED_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['IMAGE_UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER
app.config['IMAGE_PROCESSED_FOLDER'] = IMAGE_PROCESSED_FOLDER
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


def process_pdf(file_path):
    """
    处理PDF文件 - 这里可以添加你的PDF处理逻辑
    例如：OCR、文本提取、图片提取、格式转换等
    目前作为示例，我们简单复制文件并添加处理标记
    """
    try:
        # 生成处理后的文件名
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        processed_filename = f"{name}_processed{ext}"
        processed_filename = "9f06569d4e48487796978c4fcc970ad9_processed.pdf"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        # 这里可以添加实际的PDF处理逻辑

        print(f"process, ")
        # 返回处理结果信息
        return {
            'success': True,
            'processed_path': processed_path,
            'processed_filename': processed_filename,
            'processing_info': {
                'method': '示例处理',
                'description': '这是一个示例处理结果，实际应用中会进行真实的PDF处理',
                'file_size': os.path.getsize(processed_path)
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'PDF处理失败: {str(e)}'
        }

def process_image(file_path):
    """
    处理图片文件 - 这里可以添加你的图片处理逻辑
    例如：调整大小、压缩、滤镜效果、格式转换等
    目前作为示例，我们简单复制文件并添加处理标记
    """
    try:
        # 生成处理后的文件名
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        processed_filename = f"{name}_processed{ext}"
        processed_path = os.path.join(app.config['IMAGE_PROCESSED_FOLDER'], processed_filename)
        
        # 这里可以添加实际的图片处理逻辑
        # 作为示例，我们只是复制文件
        import shutil
        shutil.copy2(file_path, processed_path)
        
        print(f"图片处理完成: {processed_filename}")
        # 返回处理结果信息
        return {
            'success': True,
            'processed_path': processed_path,
            'processed_filename': processed_filename,
            'processing_info': {
                'method': '示例处理',
                'description': '这是一个示例处理结果，实际应用中会进行真实的图片处理',
                'file_size': os.path.getsize(processed_path)
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'图片处理失败: {str(e)}'
        }

@app.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    """
    上传PDF文件
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': '只支持PDF文件'
            }), 400

        # 生成安全的文件名
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        # 保存文件
        file.save(file_path)

        # 获取文件信息
        file_size = os.path.getsize(file_path)

        return jsonify({
            'success': True,
            'message': '文件上传成功',
            'file_info': {
                'original_filename': filename,
                'unique_filename': unique_filename,
                'file_size': file_size,
                'file_path': file_path
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'上传失败: {str(e)}'
        }), 500

@app.route('/api/pdf/process', methods=['POST'])
def process_uploaded_pdf():
    """
    处理已上传的PDF文件
    """
    try:
        data = request.get_json()
        print(f"data:{data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400

        filename = data['filename']


        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        # 处理PDF
        result = process_pdf(file_path)

        if result['success']:
            return jsonify({
                'success': True,
                'message': 'PDF处理完成',
                'original_file': filename,
                'processed_file': result['processed_filename'],
                'processing_info': result['processing_info']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'处理失败: {str(e)}'
        }), 500

@app.route('/api/pdf/view/<filename>')
def view_pdf(filename):
    """
    查看PDF文件
    """
    try:
        # 检查原始文件
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(original_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

        # 检查处理后的文件
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
        if os.path.exists(processed_path):
            return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件访问错误: {str(e)}'
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

        # 获取处理后文件列表
        if os.path.exists(app.config['PROCESSED_FOLDER']):
            for filename in os.listdir(app.config['PROCESSED_FOLDER']):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(app.config['PROCESSED_FOLDER'], filename)
                    processed_files.append({
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
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '未选择文件'
            }), 400

        if not allowed_image_file(file.filename):
            return jsonify({
                'success': False,
                'error': '只支持图片文件(png, jpg, jpeg, gif, bmp, webp)'
            }), 400

        # 生成安全的文件名
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], unique_filename)

        # 保存文件
        file.save(file_path)

        # 获取文件信息
        file_size = os.path.getsize(file_path)

        return jsonify({
            'success': True,
            'message': '图片上传成功',
            'file_info': {
                'original_filename': filename,
                'unique_filename': unique_filename,
                'file_size': file_size,
                'file_path': file_path
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'上传失败: {str(e)}'
        }), 500

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
        print(f"data:{data}")
        if not data or 'filename' not in data:
            return jsonify({
                'success': False,
                'error': '请提供文件名'
            }), 400

        filename = data['filename']

        file_path = os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], filename)

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404

        # 处理图片
        result = process_image(file_path)

        if result['success']:
            return jsonify({
                'success': True,
                'message': '图片处理完成',
                'original_file': filename,
                'processed_file': result['processed_filename'],
                'processing_info': result['processing_info']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500

    except Exception as e:
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
    try:
        # 检查原始文件
        original_path = os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], filename)
        if os.path.exists(original_path):
            return send_from_directory(app.config['IMAGE_UPLOAD_FOLDER'], filename)

        # 检查处理后的文件
        processed_path = os.path.join(app.config['IMAGE_PROCESSED_FOLDER'], filename)
        if os.path.exists(processed_path):
            return send_from_directory(app.config['IMAGE_PROCESSED_FOLDER'], filename)

        return jsonify({
            'success': False,
            'error': '文件不存在'
        }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'文件访问错误: {str(e)}'
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
    # 新增：图片API信息
    print(f"图片上传: http://localhost:{PORT}/api/image/upload")
    print(f"图片处理: http://localhost:{PORT}/api/image/process")
    print(f"图片查看: http://localhost:{PORT}/api/image/view/<文件名>")
    # PDF API信息
    print(f"PDF上传: http://localhost:{PORT}/api/pdf/upload")
    print(f"PDF处理: http://localhost:{PORT}/api/pdf/process")
    print(f"PDF查看: http://localhost:{PORT}/api/pdf/view/<文件名>")

    app.run(host='0.0.0.0', port=PORT, debug=True)