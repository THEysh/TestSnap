import numpy as np
import gradio as gr
import fitz
from PIL import Image
import os
from typing import List, Tuple, Any, Optional

pdf_cache = {
    "images": [],
    "current_page": 0,
    "total_pages": 0,
    "file_path": None,  # 新增，用于存储文件路径
}
# 全局缓存：存储已处理的 Sepia 图片
sepia_cache = {
    "images": []
}

def load_file(file: str | None) -> Tuple[Optional[Image.Image], str, Optional[Image.Image], Any]:
    """
    读取 PDF 或图片文件，并将其转换为图片列表以供预览和处理。

    Args:
        file (str | None): 上传文件的路径。

    Returns:
        Tuple[Optional[Image.Image], str, Optional[Image.Image], Any]:
            - 第一页的 PIL Image 对象，如果没有文件则为 None。
            - 包含页面信息的 HTML 字符串。
            - Sepia 效果组件，此处返回 None。
            - 更新页面预览组件为可见状态。
    """
    if file is None:
        # 清空所有缓存并返回空状态
        pdf_cache["images"] = []
        pdf_cache["current_page"] = 0
        pdf_cache["total_pages"] = 0
        pdf_cache["file_path"] = None
        sepia_cache["images"] = []
        return None, "<div id='page_info_box'>0 / 0</div>", None, gr.update(visible=False)

    print(f"Loading file: {file}")
    pdf_cache["file_path"] = file

    pages = []
    if file.endswith('.pdf'):
        try:
            doc = fitz.open(file)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pages.append(img)
            doc.close()
        except Exception as e:
            print(f"Failed to load PDF with PyMuPDF: {e}")
            return None, "<div id='page_info_box'>0 / 0</div>", None, gr.update(visible=False)
    else:
        try:
            img = Image.open(file)
            pages = [img]
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None, "<div id='page_info_box'>0 / 0</div>", None, gr.update(visible=False)

    pdf_cache["images"] = pages
    pdf_cache["current_page"] = 0
    pdf_cache["total_pages"] = len(pages)
    sepia_cache["images"] = []  # 清空 Sepia 缓存

    # 返回第一页图片和页面信息，并显示预览
    return pages[0], f"<div id='page_info_box'>1 / {len(pages)}</div>", None, gr.update(visible=True)

def turn_page(direction: str) -> Tuple[Optional[Image.Image], str, Optional[Image.Image]]:
    """
    翻转预览页面，并从缓存中读取对应的 Sepia 效果。

    Args:
        direction (str): 翻页方向，"prev" 或 "next"。

    Returns:
        Tuple[Optional[Image.Image], str, Optional[Image.Image]]:
            - 当前页的原始 PIL Image 对象，如果没有文件则为 None。
            - 包含页面信息的 HTML 字符串。
            - 当前页的 Sepia 效果 PIL Image 对象，如果未处理则为 None。
    """
    if not pdf_cache["images"]:
        return None, "<div id='page_info_box'>0 / 0</div>", None

    if direction == "prev":
        pdf_cache["current_page"] = max(0, pdf_cache["current_page"] - 1)
    elif direction == "next":
        pdf_cache["current_page"] = min(pdf_cache["total_pages"] - 1, pdf_cache["current_page"] + 1)

    index = pdf_cache["current_page"]

    # 从原始和 Sepia 缓存中读取当前页
    current_image = pdf_cache["images"][index]
    sepia_image = sepia_cache["images"][index] if sepia_cache["images"] else None

    return current_image, f"<div id='page_info_box'>{index + 1} / {pdf_cache['total_pages']}", sepia_image

def convert_to_markdown() -> str:
    """
    一个占位符函数，模拟将文件转换为 Markdown。

    Returns:
        str: 包含 Markdown 格式转换结果的字符串。
    """
    file_path = pdf_cache["file_path"]
    if file_path is None:
        return "请先上传一个文件。"

    filename = os.path.basename(file_path)
    markdown_output = f"""
### 文件转换结果：{filename}
这是一个占位符 Markdown 文档。
"""
    return markdown_output

def sepia(input_img: Image.Image) -> Image.Image | None:
    """
    对单张图像应用 sepia 滤镜效果。

    Args:
        input_img (Image.Image): 输入的 PIL Image 对象。

    Returns:
        Image.Image | None: 转换后的 PIL Image 对象，如果输入为 None 则返回 None。
    """
    if input_img is None:
        return None

    # 将 PIL Image 转换为 numpy 数组，并转换为 float 类型以便进行矩阵乘法
    input_img_np = np.array(input_img).astype(float)

    sepia_filter = np.array([
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131]
    ])
    # 应用 Sepia 滤镜
    sepia_img_np = input_img_np.dot(sepia_filter.T)

    # 关键修复：直接截断并转换数据类型，而不是归一化
    sepia_img_np = np.clip(sepia_img_np, 0, 255).astype(np.uint8)

    # 将 numpy 数组转换回 PIL Image 对象
    sepia_img = Image.fromarray(sepia_img_np)

    return sepia_img

def process_all() -> Tuple[Optional[Image.Image], str]:
    """
    处理所有页面，同时应用 Sepia 滤镜并转换为 Markdown。

    Returns:
        Tuple[Optional[Image.Image], str]:
            - 第一页的 Sepia 效果 PIL Image 对象。
            - 包含 Markdown 转换结果的字符串。
    """
    if not pdf_cache["images"]:
        return None, "## 🕐 请先上传一个文件。"

    # 1. 批量处理 Sepia 滤镜
    sepia_images = [sepia(img) for img in pdf_cache["images"]]
    sepia_cache["images"] = sepia_images

    # 2. 转换成 Markdown
    md_result = convert_to_markdown()

    # 返回第一页的 Sepia 效果和 Markdown 转换结果
    return sepia_images[0], md_result

def clear_all() -> Tuple[None, None, str, Any, None, None]:
    """
    清空所有输入和输出。

    Returns:
        Tuple[None, None, str, Any, None, None]:
            - 用于清空所有 Gradio 组件的元组。
    """
    pdf_cache["images"] = []
    pdf_cache["current_page"] = 0
    pdf_cache["total_pages"] = 0
    pdf_cache["file_path"] = None
    sepia_cache["images"] = []
    return (
        None,  # 清空文件输入
        None,  # 清空 PDF 预览
        "<div id='page_info_box'>0 / 0</div>",  # 清空页面信息
        gr.update(visible=False),  # 隐藏页面预览
        None,  # 清空 Markdown 输出
        None  # 清空 Sepia 结果
    )

css = """
#page_info_html {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    margin: 0 12px;
}
#page_info_box {
    padding: 8px 20px;
    font-size: 16px;
    border: 1px solid #bbb;
    border-radius: 8px;
    background-color: #f8f8f8;
    text-align: center;
    min-width: 80px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
footer {
    visibility: hidden;
}
#markdown_output {
    min-height: 800px;
    overflow: auto;
}
"""

with gr.Blocks(theme="ocean", css=css, title='文件转换与预览') as demo:
    gr.HTML("""
        <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 2em;"> pdf -> md </h1>
        </div>
        <div style="text-align: center; margin-bottom: 10px;">
            <em>上传文件并将其转换为 Markdown 文档</em>
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=1, variant="compact"):
            gr.Markdown("### 📥 上传文件")
            pdf_input = gr.File(label="选择文件", type="filepath", file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                                show_label=True)
            gr.Markdown("### ⚙️ 操作")
            # 按钮顺序
            process_button = gr.Button("🖼️ Process All", variant="primary")
            clear_button = gr.Button("🗑️ 清除", variant="huggingface")

        with gr.Column(scale=6, variant="compact"):
            with gr.Tabs():
                with gr.TabItem("文件预览"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 👁️ 文件预览")
                            pdf_view = gr.Image(label="文件预览", visible=False, height=900, show_label=False)
                            with gr.Row():
                                prev_btn = gr.Button("⬅ 上一页")
                                page_info = gr.HTML(value="<div id='page_info_box'>0 / 0</div>",
                                                    elem_id="page_info_html")
                                next_btn = gr.Button("下一页 ➡")
                        with gr.Column():
                            gr.Markdown("### ✨ Sepia 效果")
                            sepia_output = gr.Image(label="Sepia 滤镜效果", show_label=True)

                with gr.TabItem("Markdown 文档"):
                    gr.Markdown("### ✨ 转换结果")
                    md_view = gr.Markdown(value="## 🕐 等待转换结果...", elem_id="markdown_output")

    # 事件处理
    pdf_input.upload(
        fn=load_file,
        inputs=pdf_input,
        outputs=[pdf_view, page_info, sepia_output, pdf_view]
    )

    prev_btn.click(fn=lambda: turn_page("prev"), outputs=[pdf_view, page_info, sepia_output], show_progress=False)
    next_btn.click(fn=lambda: turn_page("next"), outputs=[pdf_view, page_info, sepia_output], show_progress=False)

    process_button.click(
        fn=process_all,
        inputs=None,
        outputs=[sepia_output, md_view],
        show_progress=True
    )

    clear_button.click(
        fn=clear_all,
        outputs=[pdf_input, pdf_view, page_info, pdf_view, md_view, sepia_output],
        show_progress=False
    )

demo.queue().launch(server_name="0.0.0.0", server_port=7860, debug=True)