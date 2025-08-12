from datetime import datetime
from typing import List, Dict, Any
import requests
from PIL import Image
from openai import AsyncOpenAI
from srcProject.config.constants import BlockType
from srcProject.config.settings import  FLOW_USE_MODEL_NAME
from srcProject.models.flow_base_api import FlowOCR, image_to_base64


class Silicon(FlowOCR):
    def __init__(self, api_keys: list|str, base_url: str, api_name: str):
        self.api_model_name = FLOW_USE_MODEL_NAME
        # 将 OpenAI 客户端改为 AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_keys[0],
            base_url=base_url
        )
        super().__init__(api_keys, base_url, api_name)

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
            response = await self.client.chat.completions.create(
                model=self.api_model_name,
                messages=[
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
                stream=True,  # 启用流式传输
            )
            # 遍历异步迭代器，获取流式响应
            async for chunk in response:
                chunk_message = chunk.choices[0].delta.content
                if chunk_message:
                    text += str(chunk_message)
            return text
        except Exception as e:
            print(f"API 请求或处理过程中发生错误: {e}")
            return ""


