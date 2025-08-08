import requests
from srcProject.config.settings import FLOW_API_KEY, FLOW_URL, FLOW_API_NAME
from srcProject.models.flow_base_api import FlowOCR
import json
import http.client

class ChatAnywhereOCR(FlowOCR):
    def __init__(self, api_key: str, base_url: str, api_name: str):
        # 对于API调用，model_path不是必需的，但为了符合BaseModel接口，我们仍然接受它
        super().__init__(api_key, base_url,api_name)
        self.api_model_name = 'gpt-4o-mini-2024-07-18'
    def _load_model(self):
        """
        加载模型（对于API客户端，这里主要是验证API密钥）
        """
        print(f"初始化ChatAnywhere")
        # 可以在这里添加API密钥验证逻辑
        if not self.api_key:
            raise ValueError("API密钥不能为空")
        print("ChatAnywhere初始化成功")

    def get_models(self):
        """
        使用 requests 库从 ChatAnywhere API 获取模型列表
        """
        try:
            url = f'{self.api_url}/models'
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }
            response = requests.get(url, headers=headers)
            # 检查响应状态码
            response.raise_for_status()  # 如果状态码是 4xx 或 5xx，将引发异常
            # 返回 res
            res = []
            if response.json() and "data" in response.json():
                print("成功获取模型列表：")
                for model in response.json()["data"]:
                    res.append(model)
                    # print(f"- {model['id']} (类型: {model['object']})")
            return res
        except requests.exceptions.RequestException as e:
            print(f"在获取模型时发生错误：{e}")
            raise

if __name__ == "__main__":
    # 替换为你的 ChatAnywhere API 密钥
    # 推荐从环境变量中获取密钥，更安全
    # api_key = os.getenv("CHATANYWHERE_API_KEY")
    api_key = FLOW_API_KEY

    # 实例化 ChatAnywhereOCR 类
    ocr_client = ChatAnywhereOCR(
        api_key=api_key,
        base_url=FLOW_URL,
        api_name=FLOW_API_NAME
    )
    try:
        # 调用 get_models 方法获取模型列表
        models_data = ocr_client.get_models()
        print(models_data)
    except Exception as e:
        print(f"主程序运行出错: {e}")