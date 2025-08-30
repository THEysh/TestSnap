# srcProject/utils/visualization/visualize_document.py

from PIL import Image, ImageDraw, ImageFont
import pymupdf
from typing import List, Dict, Any, Tuple, Union
import os
from srcProject.config.constants import DEFAULT_COLORS, DEFAULT_COLOR_UNKNOWN, BlockType
from srcProject.utlis.common import find_project_root
from srcProject.utlis.visualization.draw import _draw_poly_on_fitz_page, _draw_page_order_on_fitz_page, \
    _draw_poly_on_pil_image, _draw_page_order_on_pil_image


def visualize_document(
        input_path: str,
        detections_per_page: List[List[Dict[str, Any]]],
        category_names: Dict[int,  BlockType],
        page_order: List[List[int]],
        output_directory: str = "srcProject/output/visualizations",
        file_prefix: str = "layout_vis",
        dpi_for_image_output: int = 300
):
    """根据输入类型（PDF或图像），将所有布局检测结果可视化并保存。"""
    output_directory = os.path.join(find_project_root(), output_directory)
    output_directory = os.path.join(output_directory, file_prefix)
    os.makedirs(output_directory, exist_ok=True)
    file_extension = os.path.splitext(input_path)[1].lower()
    single_page_pdf_paths = []
    show_score = True

    if file_extension == '.pdf':
        for page_index, page_detections in enumerate(detections_per_page):
            pdf_output_path = os.path.join(output_directory, f"{file_prefix}_page_{page_index + 1}.pdf")
            doc = pymupdf.open(input_path)
            if not (0 <= page_index < doc.page_count):
                print(f"错误：页码 {page_index} 超出 PDF 范围。")
                doc.close()
                continue
            page = doc.load_page(page_index)
            scale_factor = 72 / dpi_for_image_output
            font_size = int(dpi_for_image_output / 300 * 8)
            current_page_order = page_order[page_index] if page_order and page_index < len(page_order) else None
            for det_idx, det in enumerate(page_detections):
                poly = det['poly']
                category_id = int(det['category_id'])
                score = det['score']
                category_name_enum = category_names.get(category_id, f"Unknown({category_id})")
                color_rgb_pil = DEFAULT_COLORS.get(category_name_enum, DEFAULT_COLOR_UNKNOWN)
                color_rgb_fitz = (color_rgb_pil[0] / 255, color_rgb_pil[1] / 255, color_rgb_pil[2] / 255)
                label = category_name_enum.name.lower()
                if show_score:
                    label += f" ({score:.2f})"
                _draw_poly_on_fitz_page(
                    page=page,
                    poly=poly,
                    label=label,
                    color=color_rgb_fitz,
                    line_width=1.0,
                    font_size=font_size,
                    scale_factor=scale_factor
                )
                _draw_page_order_on_fitz_page(
                    page=page,
                    poly=poly,
                    order_number=current_page_order[det_idx],
                    scale_factor=scale_factor,
                    font_size=font_size,
                    bg_color=(255, 165, 0)
                )
            try:
                new_doc = pymupdf.open()
                new_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_doc[0].show_pdf_page(new_doc[0].rect, doc, page.number)
                new_doc.save(pdf_output_path, garbage=4, deflate=True)
                new_doc.close()
            except Exception as e:
                print(f"保存 PDF 失败: {e}")
            finally:
                doc.close()
            single_page_pdf_paths.append(pdf_output_path)
        if single_page_pdf_paths:
            combined_pdf_path = os.path.join(output_directory, f"{file_prefix}_combined.pdf")
            try:
                combined_doc = pymupdf.open()
                for pdf_path in single_page_pdf_paths:
                    single_doc = pymupdf.open(pdf_path)
                    combined_doc.insert_pdf(single_doc)
                    single_doc.close()
                combined_doc.save(combined_pdf_path, garbage=4, deflate=True)
                combined_doc.close()
                print(f"合并后的 PDF 已保存至 {combined_pdf_path}")
                return combined_pdf_path   # ✅ 返回合并后的 PDF 路径
            except Exception as e:
                raise ValueError(f"合并 PDF 失败: {e}")
        return None

    elif file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
        if not detections_per_page:
            print("警告：图片输入没有检测结果可供可视化。")
            return
        if len(detections_per_page) > 1:
            print("警告：单张图片输入检测结果包含多页，仅可视化第一页。")
        image = Image.open(input_path).convert("RGB")
        image_output_path = os.path.join(output_directory, f"{file_prefix}_{os.path.basename(input_path)}")
        drawable_image = image.copy()
        draw = ImageDraw.Draw(drawable_image)
        font_size = 20
        line_width = 3
        try:
            current_font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            current_font = ImageFont.load_default()
            print("警告：未找到 'arial.ttf' 字体，使用 Pillow 默认字体。")
        page_detections = detections_per_page[0]
        # 图片只有一页，选择第一张
        page_order_list = page_order[0] if page_order and len(page_order) > 0 else None
        for det_idx, det in enumerate(page_detections):
            poly = det['poly']
            category_id = int(det['category_id'])
            score = det['score']
            category_name_enum = category_names.get(category_id, f"Unknown({category_id})")
            color_rgb = DEFAULT_COLORS.get(category_name_enum, DEFAULT_COLOR_UNKNOWN)
            label = category_name_enum.name.lower()
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
            _draw_page_order_on_pil_image(
                draw_obj=draw,
                poly=poly,
                order_number=page_order_list[det_idx],
                font=current_font,
                bg_color=(255, 165, 0),
                padding=5
            )
        try:
            drawable_image.save(image_output_path)
            print(f"可视化的图片已保存到: {image_output_path}")
            return image_output_path  # ✅ 返回处理后的图片路径
        except Exception as e:
            print(f"保存图片失败: {e}")
            return None
    else:
        print(f"不支持的可视化文件类型: {file_extension}")
        return None