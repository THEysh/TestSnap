from datetime import datetime
from typing import List, Dict, Any
import requests
from PIL import Image
import base64
from io import BytesIO
import json
# 导入异步客户端
from openai import AsyncOpenAI
from srcProject.config.constants import CLASS_INF, INSTRUCTION, BlockType
from srcProject.config.settings import FLOW_API_KEY, FLOW_URL, FLOW_API_NAME, FLOW_USE_MODEL_NAME
from srcProject.models.flow_base_api import FlowOCR
from srcProject.utlis.common import get_key_by_value


def image_to_base64(image: Image.Image) -> str:
    """
    将 PIL Image 对象转换为 base64 编码的字符串。
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


class Silicon(FlowOCR):
    def __init__(self, api_key: str, base_url: str, api_name: str):
        self.api_model_name = FLOW_USE_MODEL_NAME
        # 将 OpenAI 客户端改为 AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        super().__init__(api_key, base_url, api_name)

    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        print(f"初始化Siliconflow, 获取模型列表")
        if not self.api_key:
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
                'Authorization': f'Bearer {self.api_key}'
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

    async def instruction(self,inf_Classkey:BlockType=None):

        if inf_Classkey is None: return "Please output the text content from the image."
        ret = INSTRUCTION.get(inf_Classkey, "Please output the text content from the image.")
        return ret

    async def json_process(self, json_string: str) -> str:
        """
        异步处理 JSON 字符串，从字符串中提取第一个 JSON 对象的内容，
        并返回其 "text" 键的值。
        这个函数被设计用于异步环境，尽管其核心逻辑是同步的。
        Args:
            json_string (str): 包含一个或多个 JSON 对象的字符串。

        Returns:
            str: 如果成功提取并找到 "text" 键，则返回其值；
                 否则返回空字符串。
        """
        try:
            # 寻找第一个'{'和它对应的'}'
            start_index = json_string.find('{')
            if start_index == -1:
                print("字符串中没有找到 JSON 对象。")
                return ""
            # 维护一个括号计数器
            brace_count = 0
            end_index = -1
            for i in range(start_index, len(json_string)):
                if json_string[i] == '{':
                    brace_count += 1
                elif json_string[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_index = i
                        break
            if end_index == -1:
                print("JSON 对象不完整或格式错误。")
                return ""
            # 提取并解析这部分字符串
            extracted_json_str = json_string[start_index: end_index + 1]
            data = json.loads(extracted_json_str)
            # 提取 "text" 内容，如果键不存在则返回空字符串
            extracted_text = data.get("text", "")
            if extracted_text:
                print(f'成功提取到内容: "{extracted_text}"')
            else:
                print('JSON 中没有 "text" 键或其内容为空。')
            return extracted_text

        except json.JSONDecodeError:
            print("提取的子字符串不是有效的 JSON 格式。")
            return ""
        except Exception as e:
            print(f"发生了一个错误: {e}")
            return ""

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
                        "role": "system",
                        "content": "You are a rigorous OCR assistant responsible only for recognizing image content. Your answer needs to meet the following requirements: 1. Please output all recognized content as a single line without inserting any line breaks. 2. The output should not contain any greetings or additional explanations, only the plain text content in the image should be returned."
                    },
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

if __name__ == "__main__":
    api_key = FLOW_API_KEY
    ocr_client = Silicon(
        api_key=api_key,
        base_url=FLOW_URL,
        api_name=FLOW_API_NAME
    )
    # 注意：这里只是实例化客户端，并没有调用任何异步方法。
    # 如果要测试，需要在一个异步函数中调用 ocr_client.predict()
    # 例如：
    # async def main():
    #     # 假设你有一个 PIL Image 对象
    #     dummy_image = Image.new('RGB', (100, 100), color = 'red')
    #     result = await ocr_client.predict(dummy_image)
    #     print(f"OCR 结果: {result}")
    #
    # import asyncio
    # asyncio.run(main())
