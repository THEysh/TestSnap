from typing import List, Dict, Any, Union
from openai import AsyncOpenAI
from srcProject.models.model_base import BaseModel
from srcProject.config.settings import CHAT_API_KEY, CHAT_URL, CHAT_MODEL_NAME
import requests
import sys
import os
import base64
import mimetypes
from urllib.parse import urlparse
from srcProject.utlis.common import find_project_root

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

    def _normalize_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        兼容多模态输入的消息规范化：
        - 若 content 为字符串：保持不变
        - 若 content 为列表（[{type: 'text'|'image_url', ...}]）：保持不变
        - 若存在 image_url / images / image_base64 字段：转换为 OpenAI 兼容的 content 列表
        - 允许在同一条消息中同时包含文本与多张图片
        """
        norm: List[Dict[str, Any]] = []
        for m in messages or []:
            role = m.get("role", "user")
            content: Union[str, List[Any], None] = m.get("content")
            parts: List[Dict[str, Any]] = []
            # 1) 若 content 已为 parts 列表
            if isinstance(content, list):
                for it in content:
                    if isinstance(it, dict) and it.get("type") in ("text", "image_url"):
                        parts.append(it)
                    elif isinstance(it, str):
                        parts.append({"type": "text", "text": it})
                if parts:
                    norm.append({"role": role, "content": parts})
                    continue
            # 2) 收集可能的图片字段
            image_urls: List[str] = []
            if isinstance(m.get("images"), list):
                for url in m["images"]:
                    if isinstance(url, str) and url:
                        image_urls.append(url)
            if isinstance(m.get("image_url"), str) and m["image_url"]:
                image_urls.append(m["image_url"])
            if isinstance(m.get("image_base64"), str) and m["image_base64"]:
                b64 = m["image_base64"]
                if not b64.startswith("data:"):
                    b64 = f"data:image/jpeg;base64,{b64}"
                image_urls.append(b64)
            # 3) 若存在图片，拼接文本+图片为 parts
            if image_urls:
                txt = content if isinstance(content, str) else m.get("text", "")
                if isinstance(txt, str) and txt.strip():
                    parts.append({"type": "text", "text": txt})
                for url in image_urls:
                    final_url = self._ensure_data_url(url)
                    parts.append({"type": "image_url", "image_url": {"url": final_url, "detail": "auto"}})
                norm.append({"role": role, "content": parts})
                continue
            # 4) 默认字符串内容
            if isinstance(content, str):
                norm.append({"role": role, "content": content})
                continue
            # 5) 兜底：空文本
            norm.append({"role": role, "content": ""})
        return norm

    def _ensure_data_url(self, url: str) -> str:
        try:
            if not isinstance(url, str) or not url:
                return url
            if url.startswith("data:"):
                return url
            u = urlparse(url)
            if u.scheme in ("http", "https") and u.path.startswith("/api/files/") and u.hostname in ("localhost", "127.0.0.1"):
                rel = u.path[len("/api/files/"):]
                base = find_project_root()
                full = os.path.join(base, rel)
                if os.path.exists(full) and os.path.isfile(full):
                    with open(full, "rb") as f:
                        data = f.read()
                    mime, _ = mimetypes.guess_type(full)
                    if not mime:
                        mime = "image/png"
                    b64 = base64.b64encode(data).decode("ascii")
                    return f"data:{mime};base64,{b64}"
            return url
        except Exception:
            return url

    async def achat_stream(self, messages: List[Dict[str, Any]]):
        """
        异步流式聊天：yield 文本增量
        包含模型思考内容（reasoning_content）与普通内容（content），如实输出。
        """
        norm_messages = self._normalize_messages(messages)
        resp = await self.client.chat.completions.create(
            model=self._model_name,
            messages=norm_messages,
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
