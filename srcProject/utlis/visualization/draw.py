# srcProject/utils/visualization/draw.py
from PIL import ImageDraw, ImageFont
import pymupdf
from typing import List, Tuple, Any
from srcProject.utlis.aftertreatment import poly_to_bbox


def _draw_poly_on_pil_image(
        draw_obj: ImageDraw.ImageDraw,
        poly: List[float],
        label: str,
        color: Tuple[int, int, int],
        line_width: int,
        font: ImageFont.FreeTypeFont,
        font_size: int
):
    """在 PIL ImageDraw 对象上绘制多边形和标签。"""
    draw_obj.polygon(poly, outline=color, width=line_width)
    x0, y0, _, _ = poly_to_bbox(poly)
    text_bbox_coords = draw_obj.textbbox((x0, y0), label, font=font)
    text_x, text_y, text_x_end, text_y_end = text_bbox_coords
    text_y_offset = max(y0 - (text_y_end - text_y) - 5, 0)
    text_x_start = max(x0, 0)

    draw_obj.rectangle(
        [text_x_start, text_y_offset, text_x_start + (text_x_end - text_x), text_y_offset + (text_y_end - text_y)],
        fill=color)
    draw_obj.text((text_x_start, text_y_offset), label, font=font, fill=(255, 255, 255))


def _draw_poly_on_fitz_page(
        page: pymupdf.Page,
        poly: List[float],
        label: str,
        color: Tuple[float, float, float],
        line_width: float,
        font_size: float,
        scale_factor: float
):
    """在 PyMuPDF 页面对象上绘制多边形和标签。"""
    bbox_coords = poly_to_bbox([p * scale_factor for p in poly])
    x0, y0, x1, y1 = bbox_coords[0], bbox_coords[1], bbox_coords[2], bbox_coords[3]
    pdf_rect = pymupdf.Rect(x0, y0, x1, y1)
    page.draw_rect(pdf_rect, color=color, width=line_width)
    text_x = pdf_rect.x0
    text_y = pdf_rect.y0 - 2
    text_y = max(text_y, font_size)
    if label and font_size > 0:
        page.insert_text(
            (text_x, text_y),
            label,
            fontname="helv",
            fontsize=font_size,
            color=color,
        )


def _draw_page_order_on_fitz_page(
        page: pymupdf.Page,
        poly: List[float],
        order_number: int,
        scale_factor: float,
        font_size: float,
        text_color: Tuple[int, int, int] = (0, 0, 0),  # 0-255 整数元组
        bg_color: Tuple[int, int, int] = (255, 255, 255),  # 0-255 整数元组
        padding: float = 2.0
):
    """
    在 PyMuPDF 页面上，为给定的多边形在右上角绘制带有背景的阅读顺序编号。
    此函数接受 0-255 范围的整数颜色元组。
    """

    # 将 0-255 范围的整数颜色元组转换为 PyMuPDF 所需的 0.0-1.0 浮点数元组
    normalized_text_color = tuple(c / 255.0 for c in text_color)
    normalized_bg_color = tuple(c / 255.0 for c in bg_color)

    # 将像素 poly 坐标转换为 PDF 页面坐标
    bbox_coords = poly_to_bbox([p * scale_factor for p in poly])
    x0, y0, x1, y1 = bbox_coords[0], bbox_coords[1], bbox_coords[2], bbox_coords[3]

    order_text = str(order_number)
    text_width_approx = len(order_text) * font_size * 0.6
    text_height_approx = font_size

    bg_x0 = x1 - text_width_approx - 2 * padding
    bg_y0 = y0
    bg_x1 = x1
    bg_y1 = y0 + text_height_approx + 2 * padding

    bg_rect = pymupdf.Rect(bg_x0, bg_y0, bg_x1, bg_y1)

    # 使用标准化后的颜色
    page.draw_rect(bg_rect, fill=normalized_bg_color, color=normalized_bg_color, overlay=True)

    text_x = bg_x0 + padding
    text_y = bg_y0 + text_height_approx + padding

    page.insert_text(
        (text_x, text_y),
        order_text,
        fontname="helv",
        fontsize=font_size,
        color=normalized_text_color,
        overlay=True
    )

def _draw_page_order_on_pil_image(
        draw_obj: ImageDraw.ImageDraw,
        poly: List[float],
        order_number: int,
        font: ImageFont.FreeTypeFont,
        text_color: Tuple[int, int, int] = (255, 255, 255),
        bg_color: Tuple[int, int, int] = (0, 0, 0),
        padding: int = 5
):
    """在 PIL ImageDraw 对象上，为给定的多边形在右上角绘制带有背景的阅读顺序编号。"""
    x0, y0, x1, y1 = poly_to_bbox(poly)
    order_text = str(order_number)
    text_bbox = draw_obj.textbbox((0, 0), order_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    bg_x0 = x1 - text_width - 2 * padding
    bg_y0 = y0
    bg_x1 = x1
    bg_y1 = y0 + text_height + 2 * padding

    draw_obj.rectangle([bg_x0, bg_y0, bg_x1, bg_y1], fill=bg_color)
    text_x = bg_x0 + padding
    text_y = y0 + padding
    draw_obj.text((text_x, text_y), order_text, font=font, fill=text_color)