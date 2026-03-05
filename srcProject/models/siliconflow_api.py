from datetime import datetime
from typing import List, Dict, Any
import requests
from PIL import Image
import asyncio
from srcProject.config.constants import BlockType
from srcProject.config.settings import  FLOW_USE_MODEL_NAME
from srcProject.models.flow_base_api import FlowOCR, image_to_base64


class Silicon(FlowOCR):
    def __init__(self, api_keys: list|str, base_url: str, model_name: str):
        self.api_model_name = model_name
        if isinstance(api_keys, str):
            self.api_keys = [api_keys]
        elif isinstance(api_keys, list):
            self.api_keys = api_keys
        super().__init__(api_keys, base_url, self.api_model_name)

    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        print(f"初始化Siliconflow, 获取模型列表")
        if not self.api_keys[0]:
            raise ValueError("API密钥不能为空")
        res = self.get_models()
        if res:
            for model_inf in res:
                print(model_inf)
            print(f"Siliconflow初始化成功, 当前激活的模型:{self.api_model_name}")

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
            base64_image = image_to_base64(image)
            # await 异步的 _api_req 方法
            return await self._api_req(base64_image, inf_Classkey)
        else:
            return ""

    async def _api_req(self, base64_image: str, inf_Class_key:BlockType=None) -> str:
        """
        异步 API 请求函数。
        """
        text = ""
        try:
            inf_instruction = await self.instruction(inf_Class_key)
            api_key, key_index = self._get_key()
            if not api_key:
                return ""
            url = f"{self.api_url}/chat/completions"
            payload = {
                "model": self.api_model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "auto"
                                }
                            },
                            {
                                "type": "text",
                                "text": inf_instruction
                            }
                        ]
                    }
                ],
                "stream": False,
                "temperature": 0,
                "max_tokens": 2048
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers=headers,
                timeout=60
            )
            if response.status_code >= 400:
                self._set_key_index(key_index)
                return ""
            data = response.json() if response.content else {}
            choices = data.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                text = message.get("content") or ""
            return text
        except Exception as e:
            print(f"API 请求或处理过程中发生错误: {e}")
            return ""


