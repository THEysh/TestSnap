# srcProject/models/silicon_flow_ocr.py
"""
提供与硅基流动API的交互功能，用于OCR文本识别
"""
import requests
import base64
from PIL import Image
import io
from io import BytesIO
from srcProject.config.constants import INSTRUCTION, BlockType
from srcProject.config.settings import FLOW_API_KEY, FLOW_URL, FLOW_API_NAME
from srcProject.models.model_base import BaseModel
from typing import List, Dict, Any
import random
def image_to_base64(image: Image.Image) -> str:
    """
    将 PIL Image 对象转换为 base64 编码的字符串。
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

class FlowOCR(BaseModel):
    """
    硅基流动OCR模型的API客户端实现
    """
    def __init__(self, api_keys:list|str, base_url: str, api_name: str):
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
            self.key_index = [0]
        elif isinstance(api_keys, list):
            self.api_keys = api_keys
            self.key_index = [item for item in range(len(api_keys))]
        else:
            raise " api_keys，只支持：list|str"

        self.api_url = base_url
        self.api_name = api_name
        super().__init__(model_path='API模型不需要路径')

    async def instruction(self,inf_Classkey:BlockType=None):
        if inf_Classkey is None: return "Please output the text content from the image."
        ret = INSTRUCTION.get(inf_Classkey, "Please output the text content from the image.")
        return ret

    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        pass
    def _get_keys_index(self)->int|None:
        """
        从列表中随机返回一个值，但该值不能是 -1。
        返回:
          Any: 列表中一个随机的值，如果列表中没有非 -1 的元素，则返回 None。
        """
        # 过滤掉所有 -1 的元素，创建一个新列表
        filtered_list = [item for item in self.key_index if item != -1]
        # 如果过滤后的列表不为空，则从其中随机选择一个元素
        if filtered_list:
            return random.choice(filtered_list)
        else:
            # 如果列表中所有元素都是 -1，则返回 None 或其他指示值
            return None

    def _get_key(self)->tuple[str,int]|tuple[None,None]:
        """获取一个可用的API密钥"""

        index = self._get_keys_index()
        if index is None:
            print("出现错误，key池已经为空")
            return None,None
        else:
            return self.api_keys[index], index

    def _set_key_index(self, index):
        """设置密钥索引为-1，表示该密钥已不可用"""
        self.key_index[index] = -1


    @property
    def names(self) -> Dict[int, str]:
        """
        返回模型类别映射（对于OCR，这里返回空字典）
        """
        return {}

if __name__ == "__main__":
    FlowOCR(api_key=FLOW_API_KEY, base_url=FLOW_URL, api_name=FLOW_API_NAME)