# srcProject/utils/visualization/visualizers.py

from PIL import Image, ImageDraw, ImageFont
import pymupdf
from typing import List, Dict, Any, Tuple
import os
from srcProject.config.constants import DEFAULT_COLORS, DEFAULT_COLOR_UNKNOWN, BlockType
from srcProject.utlis.visualization.draw import _draw_poly_on_pil_image, _draw_poly_on_fitz_page

try:
    _DEFAULT_FONT = ImageFont.truetype("arial.ttf", 16)
except IOError:
    _DEFAULT_FONT = ImageFont.load_default()
    print("警告：未找到 'arial.ttf' 字体，使用 Pillow 默认字体。字体大小可能不受控制。")


def draw_detections_on_image(
        detections: List[Dict[str, Any]],
        output_path: str,
        page_order: List[int] = None,
        line_width: int = 2,
        font_size: int = 16
):
    """在空白 PIL 图像上绘制检测结果的多边形和标签，并保存为文件。"""
    category_names = {block_type.value: block_type.name.lower().replace('_', ' ') for block_type in BlockType}
    all_x = []
    all_y = []
    for det in detections:
        x_coords = det['poly'][0::2]
        y_coords = det['poly'][1::2]
        all_x.extend(x_coords)
        all_y.extend(y_coords)
    margin = 50
    min_x, max_x = max(0, min(all_x) - margin), max(all_x) + margin
    min_y, max_y = max(0, min(all_y) - margin), max(all_y) + margin
    image_width = int(max_x - min_x)
    image_height = int(max_y - min_y)
    image = Image.new('RGB', (image_width, image_height), (255, 255, 255))
    draw_obj = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
        print("警告：未找到 arial.ttf，使用默认字体")

    for det in detections:
        poly = det['poly']
        category_id = det['category_id']
        score = det['score']
        category_name = category_names.get(category_id, f"unknown({category_id})")
        color = DEFAULT_COLORS.get(category_name, DEFAULT_COLOR_UNKNOWN)
        label = category_name
        label += f" ({score:.2f})"
        adjusted_poly = []
        for i in range(0, len(poly), 2):
            adjusted_x = poly[i] - min_x
            adjusted_y = poly[i + 1] - min_y
            adjusted_poly.extend([adjusted_x, adjusted_y])
        _draw_poly_on_pil_image(
            draw_obj=draw_obj,
            poly=adjusted_poly,
            label=label,
            color=color,
            line_width=line_width,
            font=font,
            font_size=font_size
        )
    image.save(output_path)
    print(f"图像已保存至 {output_path}")


def visualize_layout_on_image(
        image: Image.Image,
        detections: List[Dict[str, Any]],
        category_names: Dict[int, str],
        output_path: str = None,
        line_width: int = 3,
        font_size: int = 16,
        show_score: bool = True
) -> Image.Image:
    """将布局检测结果绘制到 PIL Image 上。"""
    drawable_image = image.copy()
    draw = ImageDraw.Draw(drawable_image)

    current_font = _DEFAULT_FONT.font_variant(size=font_size) if hasattr(_DEFAULT_FONT,
                                                                         'font_variant') else _DEFAULT_FONT

    for det in detections:
        poly = det['poly']
        category_id = det['category_id']
        score = det['score']
        category_name = category_names.get(category_id, f"Unknown({category_id})")
        color_rgb = DEFAULT_COLORS.get(category_name.lower(), DEFAULT_COLOR_UNKNOWN)
        label = category_name
        if show_score:
            label += f" ({score:.2f})"
        _draw_poly_on_pil_image(
            draw_obj=draw,
            poly=poly,
            label=label,
            color=color_rgb,
            line_width=line_width,
            font=current_font,
            font_size=font_size
        )
    if output_path:
        try:
            drawable_image.save(output_path)
            print(f"绘制后的图片已保存到: {output_path}")
        except Exception as e:
            print(f"保存图片失败: {e}")
    return drawable_image


def visualize_layout_on_pdf(
        pdf_path: str,
        page_index: int,
        detections: List[Dict[str, Any]],
        category_names: Dict[int, str],
        output_pdf_path: str,
        dpi_used_for_detection: int = 300,
        line_width: float = 1.0,
        font_size: float = 8.0,
        show_score: bool = True
):
    """将布局检测结果绘制到 PDF 页面上，并保存为新的 PDF 文件。"""
    doc = pymupdf.open(pdf_path)
    if not (0 <= page_index < doc.page_count):
        print(f"错误：页码 {page_index} 超出 PDF 范围。")
        doc.close()
        return
    page = doc.load_page(page_index)
    scale_factor = 72 / dpi_used_for_detection

    for det in detections:
        poly = det['poly']
        category_id = det['category_id']
        score = det['score']
        category_name = category_names.get(category_id, f"Unknown({category_id})")
        color_rgb_pil = DEFAULT_COLORS.get(category_name.lower(), DEFAULT_COLOR_UNKNOWN)
        color_rgb_fitz = (color_rgb_pil[0] / 255, color_rgb_pil[1] / 255, color_rgb_pil[2] / 255)

        label = category_name
        if show_score:
            label += f" ({score:.2f})"
        _draw_poly_on_fitz_page(
            page=page,
            poly=poly,
            label=label,
            color=color_rgb_fitz,
            line_width=line_width,
            font_size=font_size,
            scale_factor=scale_factor
        )

    try:
        new_doc = pymupdf.open()
        new_doc.insert_pdf(doc, from_page=page_index, to_page=page_index)
        new_doc.save(output_pdf_path, garbage=4, deflate=True)
        new_doc.close()
    except Exception as e:
        print(f"保存 PDF 失败: {e}")
    finally:
        doc.close()