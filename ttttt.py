from openai import OpenAI

client = OpenAI(
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-cxropeqeyqablbtbltjfqezajpziohsnlomwfuqecqnrtzxo"
)

response = client.chat.completions.create(
    model="Qwen/Qwen2.5-VL-72B-Instruct",  # 或 deepseek-ai/DeepSeek-V3 等
    messages=[
        {"role": "system", "content": "你是一位数学家，用最清晰的步骤解答问题。"},
        {"role": "user", "content": "证明勾股定理，并给出一个直观的几何证明思路。"}
    ],
    max_tokens=4096,
    temperature=0.6,
    stream=True,  # 改为流式输出
    extra_body={
        "enable_thinking": True,
        "thinking_budget": 2048  # 控制思考过程最大长度为1000 token
    }
)

print("最终回答（流式输出）：\n")

thinking_part = ""
answer_part = ""
in_thinking = False

for chunk in response:
    if not chunk.choices:
        continue

    delta = chunk.choices[0].delta

    # 处理思考部分（如果模型支持 reasoning_content 流式返回）
    if hasattr(delta, "reasoning_content") and delta.reasoning_content is not None:
        thinking_part += delta.reasoning_content
        print("\n[思考中] ", delta.reasoning_content, end="", flush=True)
        in_thinking = True

    # 处理正式回答内容
    elif delta.content is not None:
        # 如果之前还在思考中，现在切换到回答
        if in_thinking:
            print("\n\n───────────── 正式回答 ─────────────\n")
            in_thinking = False
        answer_part += delta.content
        print(delta.content, end="", flush=True)

# 结束后换行
print("\n")

# 如果收集到了思考过程，可以在这里统一打印或保存
if thinking_part:
    print("\n───────────── 完整思考过程（回顾）─────────────")
    print(thinking_part)