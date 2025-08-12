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
    async def _api_req(self, image_part: Part, inf_Class_key:BlockType=None, index:int=0) -> str:
        """
        异步 API 请求函数。
        """
        try:
            inf_instruction = await self.instruction(inf_Class_key)
            response = await self.client.aio.models.generate_content(
                model=self.api_model_name,
                contents=[image_part, inf_instruction]
            )
            return response.text
        except Exception as e:
            # 检查是否是 429 错误，并根据情况抛出自定义异常
            if "429" in str(e):
                print("捕获到 429 错误: 1分钟内访问了次数(突破google服务器限制)，从配置文件的api_key尝试获取其它的key，或者等待google服务器响应")
                new_index = self._get_keys_index()
                if new_index is not None:
                    self.client = genai.Client(api_key=self.api_keys[new_index])
                    return await self._api_req(image_part, inf_Class_key, new_index)
                else:
                    print("所有的key均不满足要求")
                    return ""

            elif "400" in str(e):
                print("捕获到 400 错误: API key expired. Please renew the API key.")
                self.key_index[index] = -1
                new_index = self._get_keys_index()
                if new_index is not None:
                    self.client = genai.Client(api_key=self.api_keys[new_index])
                    return await self._api_req(image_part, inf_Class_key,new_index)
                else:
                    print("所有的key均不满足要求")
                    return ""
            else:
                print(f"API 请求或处理过程中发生未知错误: {e}")
                return ""



