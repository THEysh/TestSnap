import requests
import sys


def test_two_images_comparison():
    url = "http://localhost:7861/api/chat/stream"

    # 两张图片的地址
    image1 = "http://localhost:7861/api/files/srcProject/output/visualizations/2dba7c0b/images/66029d50-56f0-4484-a6a8-69f93c17a20e.png"
    image2 = "http://localhost:7861/api/files/srcProject/output/visualizations/2dba7c0b/images/66029d50-56f0-4484-a6a8-69f93c17a20e.png"  # 请替换为实际地址

    payload = {
        "messages": [
            {"role": "system", "content": "你是一个专业的数据可视化分析师，擅长对比分析多张图表。"},
            {
                "role": "user",
                "content": """请详细对比分析这两张图片：

请从以下几个方面进行对比：
1. 图表类型分别是什么？
""",
                "images": [image1, image2]
            }
        ]
    }

    print(f"POST {url}")
    print(f"对比分析两张图片:")
    print(f"图片1: {image1}")
    print(f"图片2: {image2}")
    print("-" * 60)

    with requests.post(url, json=payload, stream=True) as r:
        r.raise_for_status()
        print("开始接收分析结果：")
        buffer = ""
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue
            buffer += chunk.decode("utf-8")
            while True:
                idx = buffer.find("\n\n")
                if idx == -1:
                    break
                frame = buffer[:idx]
                buffer = buffer[idx + 2:]
                for line in frame.split("\n"):
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                        if data == "[DONE]":
                            print("\n[对比分析完成]")
                            return
                        sys.stdout.write(data)
                        sys.stdout.flush()
        print("\n[连接结束]")


if __name__ == "__main__":
    test_two_images_comparison()