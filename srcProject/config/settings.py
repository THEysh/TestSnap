# src/config/settings.py
import yaml
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(BASE_DIR, 'configs.yaml')

def load_config(config_path=CONFIG_PATH):
    """加载并返回 YAML 配置文件内容。"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件未找到: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

_config_data = load_config()
# 设备配置
DEVICE = _config_data.get('device', 'cpu')

# 获取激活的布局模型的具体配置
ACTIVE_LAYOUT_CONFIG = _config_data['layout_weights_config']['layout_model']
# 提取布局模型名称和其完整的权重路径
LAYOUT_MODEL_NAME = ACTIVE_LAYOUT_CONFIG['name']
# 组合路径：通用模型目录 + 模型配置中定义的相对路径
LAYOUT_WEIGHTS_PATH = os.path.join(BASE_DIR, ACTIVE_LAYOUT_CONFIG['path'])

ACTIVE_READ_MODEL_CONFIG = _config_data['read_weights_config']['read_model']
READ_MODEL_NAME = ACTIVE_READ_MODEL_CONFIG['name']
READ_WEIGHTS_PATH = os.path.join(BASE_DIR, ACTIVE_READ_MODEL_CONFIG['path'])


FLOW_CONFIG = _config_data.get('gpt-api', {})
FLOW_API_KEY = FLOW_CONFIG.get('api_key', '')
FLOW_URL = FLOW_CONFIG.get('base_url', '')
FLOW_API_NAME = FLOW_CONFIG.get('api_name', 'Siliconflow')
FLOW_USE_MODEL_NAME = FLOW_CONFIG.get('model_name', 'Pro/Qwen/Qwen2.5-VL-7B-Instruct')