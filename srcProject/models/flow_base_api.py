# srcProject/models/silicon_flow_ocr.py
"""
提供与硅基流动API的交互功能，用于OCR文本识别
"""
import requests
import base64
from PIL import Image
import io
from srcProject.config.settings import FLOW_API_KEY, FLOW_URL, FLOW_API_NAME
from srcProject.models.model_base import BaseModel
from typing import List, Dict, Any

class FlowOCR(BaseModel):
    """
    硅基流动OCR模型的API客户端实现
    """
    def __init__(self, api_key: str, base_url: str, api_name: str):
        # 对于API调用，model_path不是必需的，但为了符合BaseModel接口，我们仍然接受它
        self.api_key = api_key
        self.api_url = base_url
        self.api_name = api_name
        super().__init__(model_path='API模型不需要路径')

    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        pass

    @property
    def names(self) -> Dict[int, str]:
        """
        返回模型类别映射（对于OCR，这里返回空字典）
        """
        return {}

if __name__ == "__main__":
    FlowOCR(api_key=FLOW_API_KEY, base_url=FLOW_URL, api_name=FLOW_API_NAME)