import random
from typing import List, Dict, Any
import requests
import asyncio
from PIL import Image
from google import genai
import io

from google.genai import types
from google.genai.types import Part
import time

from srcProject.config.constants import BlockType
from srcProject.config.settings import FLOW_API_KEY, FLOW_URL, FLOW_API_NAME, FLOW_USE_MODEL_NAME
from srcProject.models.flow_base_api import FlowOCR, image_to_base64


class Google(FlowOCR):
    def __init__(self, api_keys: list, api_name: str):
        self.api_model_name = FLOW_USE_MODEL_NAME
        self.client = genai.Client(api_key=api_keys[0])
        super().__init__(api_keys, "", api_name)

    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        for m in self.client.models.list():
            for action in m.supported_actions:
                if action == "generateContent":
                    print(m.name)
        print("当前激活模型{}".format(self.api_model_name))
    def get_models(self) -> List[dict]:
        """
        使用 requests 库从 ChatAnywhere API 获取模型列表
        （requests 是同步库，如果需要异步，请使用 aiohttp 等）
        """
        try:
            url = f'{self.api_url}/models'
            querystring = {"sub_type": "chat"}
            headers = {
                'Authorization': f'Bearer {self.api_keys[0]}'
            }
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            res = []
            if response.json() and "data" in response.json():
                print("成功获取模型列表：")
                for model in response.json()["data"]:
                    res.append(model)
            return res
        except requests.exceptions.RequestException as e:
            print(f"在获取模型时发生错误：{e}")
            raise
    async def predict(self, image: Image.Image, inf_Classkey:BlockType=None) -> str:
        """
        异步预测函数，处理图片并调用 OCR API。
        """
        if isinstance(image, Image.Image):
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            image_bytes = img_byte_arr.getvalue()
            image_part = Part.from_bytes(data=image_bytes, mime_type='image/png')
            return await self._api_req(image_part, inf_Classkey, self._get_keys_index())
        else:
            return ""

    async def _api_req(self, image_part: Part,
                       inf_Class_key:BlockType = None,
                       retries: int = 0) -> str:
        """
        异步 API 请求函数，支持重试。
        """
        try:
            inf_instruction = await self.instruction(inf_Class_key)
            response = await self.client.aio.models.generate_content(
                model=self.api_model_name,
                contents=[image_part, inf_instruction]
            )
            return response.text
        except Exception as e:
            # 如果重试次数超过限制，直接抛出异常
            if retries >= 3:
                print(f"API 请求失败，重试次数已达上限：{e}")
                return ""
            new_key,new_index = self._get_key()
            if new_key is not None:
                self.client = genai.Client(api_key=new_key)
            # 处理特定的错误
            if "429" in str(e):
                print("捕获到 429 错误: 访问频率过高。google服务器拒绝，尝试从配置文件中keys中更换")
                return await self._api_req(image_part, inf_Class_key)
            elif "400" in str(e):
                print("捕获到 400 错误: API 密钥已过期。")
                self._set_key_index(new_index)
                return await self._api_req(image_part, inf_Class_key)
            else:
                print(f"API 请求或处理过程中发生未知错误: {e}。开始第 {retries + 1} 次重试...")
                # 可以在重试前添加一个短暂的等待时间，以避免立即失败
                await asyncio.sleep(2 ** retries)
                return await self._api_req(image_part, inf_Class_key, retries=retries + 1)


