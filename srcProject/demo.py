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
    "file_path": None,
}

output_cache = {
    "images": [],
    "current_page": 0,
    "total_pages": 0,
}

OUTPUT_PDF_PATH = r"F:\ysh_loc_office\projects\practice\TextSnap\srcProject\output\visualizations\demo1\demo1_combined.pdf"
# 定义你的Markdown文件路径
MARKDOWN_FILE_PATH = r"F:\ysh_loc_office\projects\practice\TextSnap\srcProject\output\visualizations\demo1\demo1.md"


def load_file(file: str | None) -> Tuple[Optional[Image.Image], str, Optional[Image.Image], Any]:
    """
    读取 PDF 或图片文件，并将其转换为图片列表以供预览和处理。
    """
    if file is None:
        pdf_cache["images"] = []
        pdf_cache["current_page"] = 0
        pdf_cache["total_pages"] = 0
        pdf_cache["file_path"] = None
        output_cache["images"] = []
        output_cache["current_page"] = 0
        output_cache["total_pages"] = 0
        return None, "<div id='page_info_box'>0 / 0</div>", None, gr.update(visible=False)

    print(f"Loading file: {file}")
    pdf_cache["file_path"] = file

    pages = []
    if file.endswith('.pdf'):
        try:
            doc = fitz.open(file)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
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

    output_cache["images"] = []
    output_cache["current_page"] = 0
    output_cache["total_pages"] = 0

    return pages[0], f"<div id='page_info_box'>1 / {len(pages)}</div>", None, gr.update(visible=True)


def load_output_pdf() -> List[Image.Image]:
    """
    加载指定路径的输出PDF文件并转换为图片列表。
    """
    output_images = []
    if os.path.exists(OUTPUT_PDF_PATH):
        try:
            doc = fitz.open(OUTPUT_PDF_PATH)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                output_images.append(img)
            doc.close()
            print(f"Successfully loaded output PDF: {OUTPUT_PDF_PATH}")
        except Exception as e:
            print(f"Failed to load output PDF: {e}")
    else:
        print(f"Output PDF not found: {OUTPUT_PDF_PATH}")

    return output_images


def turn_page(direction: str) -> Tuple[Optional[Image.Image], str, Optional[Image.Image]]:
    """
    翻转预览页面，并从缓存中读取对应的输出PDF页面。
    """
    if not pdf_cache["images"]:
        return None, "<div id='page_info_box'>0 / 0</div>", None

    if direction == "prev":
        pdf_cache["current_page"] = max(0, pdf_cache["current_page"] - 1)
    elif direction == "next":
        pdf_cache["current_page"] = min(pdf_cache["total_pages"] - 1, pdf_cache["current_page"] + 1)

    index = pdf_cache["current_page"]

    current_image = pdf_cache["images"][index]
    output_image = output_cache["images"][index] if index < len(output_cache["images"]) else None

    return current_image, f"<div id='page_info_box'>{index + 1} / {pdf_cache['total_pages']}", output_image


def convert_to_markdown() -> str:
    """
    读取指定路径的Markdown文件内容。

    Returns:
        str: Markdown文件中的内容，如果文件不存在则返回错误信息。
    """
    file_path = pdf_cache["file_path"]
    if file_path is None:
        return "### 请先上传一个文件。"

    # 检查Markdown文件是否存在
    if not os.path.exists(MARKDOWN_FILE_PATH):
        return f"### 错误：找不到Markdown文件。\n\n**路径:** `{MARKDOWN_FILE_PATH}`"

    try:
        # 使用utf-8编码读取文件内容
        with open(MARKDOWN_FILE_PATH, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # 返回文件内容
        return markdown_content
    except Exception as e:
        # 如果读取过程中出现错误，返回错误信息
        return f"### 错误：读取Markdown文件失败。\n\n**原因:** {e}"

def process_all() -> Tuple[Optional[Image.Image], str]:
    """
    处理所有页面，加载输出PDF并转换为包含LaTeX的HTML。
    """
    if not pdf_cache["images"]:
        return None, "### 🕐 请先上传一个文件。"

    output_images = load_output_pdf()
    output_cache["images"] = output_images
    output_cache["current_page"] = 0
    output_cache["total_pages"] = len(output_images)

    # 转换成 Markdown (包含LaTeX)
    markdown_result = convert_to_markdown()

    first_output_image = output_images[0] if output_images else None
    return first_output_image, markdown_result


def clear_all() -> Tuple[None, None, str, Any, None, str]:
    """
    清空所有输入和输出。
    """
    pdf_cache["images"] = []
    pdf_cache["current_page"] = 0
    pdf_cache["total_pages"] = 0
    pdf_cache["file_path"] = None
    output_cache["images"] = []
    output_cache["current_page"] = 0
    output_cache["total_pages"] = 0
    return (
        None,
        None,
        "<div id='page_info_box'>0 / 0</div>",
        gr.update(visible=False),
        None,
        "### 🕐 等待转换结果..."
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
    background-color: #ffffff;
    border: 1px solid #e1e5e9;
    border-radius: 8px;
}
.gradio-container .image-container {
    height: 800px !important;
    object-fit: contain !important;
}
.gradio-container .image-container img {
    max-height: 800px;
    width: auto;
    object-fit: contain;
    image-rendering: -webkit-optimize-contrast;
    image-rendering: crisp-edges;
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
            process_button = gr.Button("🖼️ Process All", variant="primary")
            clear_button = gr.Button("🗑️ 清除", variant="huggingface")

        with gr.Column(scale=6, variant="compact"):
            with gr.Tabs():
                with gr.TabItem("文件预览"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 👁️ 文件预览")
                            pdf_view = gr.Image(label="文件预览", visible=False, height=800, show_label=False,
                                                container=True, show_download_button=False)
                            with gr.Row():
                                prev_btn = gr.Button("⬅ 上一页")
                                page_info = gr.HTML(value="<div id='page_info_box'>0 / 0</div>",
                                                    elem_id="page_info_html")
                                next_btn = gr.Button("下一页 ➡")
                        with gr.Column():
                            gr.Markdown("### 📄 输出PDF预览")
                            output_display = gr.Image(label="输出PDF预览", show_label=True, height=800,
                                                      container=True, show_download_button=False)

                with gr.TabItem("Markdown 文档"):
                    gr.Markdown("### ✨ 转换结果")
                    # 使用 gr.Markdown 替代 gr.HTML
                    markdown_view = gr.Markdown(
                        value="### 🕐 等待转换结果...",
                        elem_id="markdown_output")

    pdf_input.upload(
        fn=load_file,
        inputs=pdf_input,
        outputs=[pdf_view, page_info, output_display, pdf_view]
    )

    prev_btn.click(fn=lambda: turn_page("prev"), outputs=[pdf_view, page_info, output_display], show_progress=False)
    next_btn.click(fn=lambda: turn_page("next"), outputs=[pdf_view, page_info, output_display], show_progress=False)

    process_button.click(
        fn=process_all,
        inputs=None,
        outputs=[output_display, markdown_view],  # 输出到 markdown_view
        show_progress=True
    )

    clear_button.click(
        fn=clear_all,
        outputs=[pdf_input, pdf_view, page_info, pdf_view, output_display, markdown_view],  # 输出到 markdown_view
        show_progress=False
    )

demo.queue().launch(server_name="0.0.0.0", server_port=7860, debug=True)