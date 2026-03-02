from typing import List, Dict, Any
from openai import AsyncOpenAI
from srcProject.models.model_base import BaseModel
from srcProject.config.settings import CHAT_API_KEY, CHAT_URL, CHAT_MODEL_NAME
import requests
import sys

class SiliconChatModel(BaseModel):
    """
    面向对话的 SiliconFlow(OpenAI 兼容) 客户端
    继承 BaseModel 以统一项目模型管理方式
    """

    def __init__(self,
                 api_keys: List[str] | str = None,
                 base_url: str = None,
                 model_name: str = None,
                 device: str = "api"):
        self._api_keys = [api_keys] if isinstance(api_keys, str) else (api_keys or CHAT_API_KEY)
        self._base_url = base_url or CHAT_URL
        self._model_name = model_name or CHAT_MODEL_NAME
        self.client: AsyncOpenAI | None = None
        super().__init__(model_path="API-CHAT", device=device)

    def _load_model(self):
        key = self._api_keys[0] if isinstance(self._api_keys, list) else self._api_keys
        self.client = AsyncOpenAI(api_key=key, base_url=self._base_url)

    @property
    def names(self) -> Dict[int, str]:
        return {}

    async def achat_stream(self, messages: List[Dict[str, Any]]):
        """
        异步流式聊天：yield 文本增量
        包含模型思考内容（reasoning_content）与普通内容（content），如实输出。
        """
        resp = await self.client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            stream=True
        )
        async for chunk in resp:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if not delta:
                continue
            # 优先输出思考内容（若模型支持），随后输出普通内容
            rc = getattr(delta, "reasoning_content", None)
            if rc:
                try:
                    yield str(rc)
                except Exception:
                    yield rc  # 最后兜底
            ct = getattr(delta, "content", None)
            if ct:
                try:
                    yield str(ct)
                except Exception:
                    yield ct

def main():
    url = "http://localhost:7861/api/chat/stream"
    payload = {
        "messages": [
            {"role": "system", "content": "你是一个简洁的中文助理。"},
            {"role": "user", "content": "从1数到10"}
        ]
    }
    print("POST", url)
    with requests.post(url, json=payload, stream=True) as r:
        r.raise_for_status()
        print("开始流式接收：")
        buffer = ""
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            buffer += chunk.decode("utf-8")
            # SSE 以空行分帧
            while True:
                idx = buffer.find("\n\n")
                if idx == -1:
                    break
                frame = buffer[:idx]
                buffer = buffer[idx + 2:]
                # 解析 data 行
                for line in frame.split("\n"):
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                        if data == "[DONE]":
                            print("\n[完成]")
                            return
                        # 直接输出片段
                        sys.stdout.write(data)
                        sys.stdout.flush()
                    elif line.startswith("event: error"):
                        print("\n[服务端错误帧]")
                # 下一帧
        print("\n[连接结束]")


if __name__ == "__main__":
    # 先启动server.py 在运行测试流式访问
    main()