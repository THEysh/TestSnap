"""
Model manager for coordinating multiple models.

Responsible for:
- Loading and managing all model instances
- Resource allocation across models
- Coordinating inference across different model types
- Corresponds to MonkeyOCR_model in the original implementation
"""
from typing import List, Any, Dict
from PIL import Image
from srcProject.config.settings import LAYOUT_MODEL_NAME, LAYOUT_WEIGHTS_PATH, READ_MODEL_NAME, READ_WEIGHTS_PATH, \
    FLOW_API_NAME, FLOW_API_KEY, FLOW_URL, DEVICE
from srcProject.models.layout_detector import DocLayoutYOLO
from srcProject.models.layout_reader import LayoutReader
from srcProject.models.model_base import BaseModel
from srcProject.models.siliconflow_api import Silicon


class ModelFactory:
    @staticmethod
    def create(model_name: str='api',
               model_Path: str='',
               device: str = 'cuda',
               api_key: str = '',
               base_url: str = '',
               api_name:str = '') -> BaseModel:
        if model_name.lower() == 'doclayout_yolo':
            return DocLayoutYOLO(model_Path, device)
        elif model_name.lower() == 'layoutlmv3':
            return LayoutReader(model_Path, device)
        elif model_name.lower() == 'siliconflow':
            return Silicon(api_key=api_key, base_url=base_url, api_name=api_name)
        else:
            raise ValueError(f"不支持的模型名称: {model_name}")



class ModelManager:
    def __init__(self,device: str = DEVICE):
        self.device = device
        print(f"使用{self.device}加载了模型")
        # 使用工厂创建布局检测器实例
        self.layout_detector = ModelFactory.create(
            model_name=LAYOUT_MODEL_NAME,
            model_Path=LAYOUT_WEIGHTS_PATH,
            device=device
        )
        # 现在可以通过检测器实例访问类别名称映射
        self.layout_category_names = self.layout_detector.names
        print(f"已加载布局模型: {LAYOUT_MODEL_NAME}，类别: {self.layout_category_names}")
        self.read_model = ModelFactory.create(
            model_name=READ_MODEL_NAME,
            model_Path=READ_WEIGHTS_PATH,
            device=device
        )
        print(f"已加载布局模型: {READ_MODEL_NAME}")
        self.ocr_recognizer = ModelFactory.create(
            api_key=FLOW_API_KEY,
            base_url=FLOW_URL,
            api_name=FLOW_API_NAME,
            model_name= FLOW_API_NAME
        )
        print(f"已加载OCR-api模型: {FLOW_API_NAME}")
        # ... 初始化其他模型（内容识别器、阅读顺序预测器）
        # self.content_recognizer = ContentRecognizer(...)
        # self.reading_order_predictor = ReadingOrderPredictor(...)


if __name__ == '__main__':
    # 获取当前脚本所在的目录
    ModelManager(device='cpu')