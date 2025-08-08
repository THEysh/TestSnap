import os.path
from typing import List, Dict, Any
import numpy as np

from srcProject.config.constants import FilterCategories_VALUES
from srcProject.utlis.common import find_project_root
from PIL import Image

# --- 辅助函数：将多边形坐标转换为四边形 (如果需要) ---
# 你的模型返回的是 poly: [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax]
# 有些绘图函数可能只需要 [x0, y0, x1, y1]
def poly_to_bbox(poly: List[float]) -> List[int]:
    """将四边形顶点列表转换为 [x0, y0, x1, y1] 格式的边界框。"""
    if len(poly) == 8:
        x_coords = [int(poly[0]), int(poly[2]), int(poly[4]), int(poly[6])]
        y_coords = [int(poly[1]), int(poly[3]), int(poly[5]), int(poly[7])]
        return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
    return poly  # 如果已经是 [x0,y0,x1,y1] 格式，则直接返回


def poly_to_bbox_scaled(poly: List[float], page_size: tuple) -> List[int]:
    """
    将多边形顶点列表转换为以1000为比例放缩的整数边界框 [x0, y0, x1, y1]。

    此函数首先将多边形（poly）转换为原始尺寸的边界框，然后根据页面尺寸
    (width, height) 将其放缩到1000x1000的比例。

    Args:
        poly (List[float]): 多边形顶点列表，格式为 [x0, y0, x1, y1, ...]。
                            如果是矩形，通常是8个元素或4个元素。
        page_size (tuple): 页面尺寸，格式为 (width, height)。

    Returns:
        List[int]: 放缩后的整数边界框，格式为 [x0, y0, x1, y1]。
    """
    width, height = page_size[0], page_size[1]

    # 步骤1: 将多边形顶点列表转换为原始尺寸的边界框
    if len(poly) == 8:
        x_coords = [poly[0], poly[2], poly[4], poly[6]]
        y_coords = [poly[1], poly[3], poly[5], poly[7]]
        original_bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
    elif len(poly) == 4:
        original_bbox = poly
    else:
        raise ValueError("poly 必须是包含4或8个元素的列表。")

    # 步骤2: 计算缩放比例并放缩边界框
    x_scale = 1000.0 / width
    y_scale = 1000.0 / height

    x0 = int(round(original_bbox[0] * x_scale))
    y0 = int(round(original_bbox[1] * y_scale))
    x1 = int(round(original_bbox[2] * x_scale))
    y1 = int(round(original_bbox[3] * y_scale))

    return [x0, y0, x1, y1]


def normalize_polygons_to_bboxes(data: List[List[Dict[str, Any]]]) -> List[List[int]]:
    """
    将包含多边形坐标和页面尺寸的嵌套字典列表转换为以 1000 为比例放缩的整数边界框列表。
    此实现借用了 poly_to_bbox 函数来简化逻辑。
    """
    result = []
    for page_data in data:
        page_bboxes = []
        for item in page_data:
            poly = item['poly']
            page_size = item['page_size']
            width, height = page_size[0], page_size[1]

            # 使用 poly_to_bbox 函数将多边形转换为原始尺寸的边界框
            original_bbox = poly_to_bbox(poly)

            # 计算缩放比例
            x_scale = 1000.0 / width
            y_scale = 1000.0 / height

            # 使用缩放比例计算并四舍五入为整数
            x0 = int(round(original_bbox[0] * x_scale))
            y0 = int(round(original_bbox[1] * y_scale))
            x1 = int(round(original_bbox[2] * x_scale))
            y1 = int(round(original_bbox[3] * y_scale))

            page_bboxes.append([x0, y0, x1, y1])

        result.append(page_bboxes)

    return result


def compute_iou(box1: List[float], box2: List[float]) -> float:
    """计算两个边界框的 IoU（Intersection over Union）。"""
    x0_1, y0_1, x1_1, y1_1 = box1
    x0_2, y0_2, x1_2, y1_2 = box2
    x0_inter = max(x0_1, x0_2)
    y0_inter = max(y0_1, y0_2)
    x1_inter = min(x1_1, x1_2)
    y1_inter = min(y1_1, y1_2)
    if x1_inter < x0_inter or y1_inter < y0_inter:
        return 0.0
    inter_area = (x1_inter - x0_inter) * (y1_inter - y0_inter)
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
    union_area = area1 + area2 - inter_area
    return inter_area / union_area if union_area > 0 else 0.0

def compute_area(box: List[float]) -> float:
    """计算边界框的面积。"""
    x0, y0, x1, y1 = box
    return (x1 - x0) * (y1 - y0)

def resize_image_for_mvl(image: Image.Image, min_size: int = 28) -> Image.Image:
    """
    调整图片尺寸，使其高度和宽度都大于等于 min_size。
    如果图片的某个维度小于 min_size，则进行填充（padding）。
    """
    width, height = image.size
    new_width = max(width, min_size)
    new_height = max(height, min_size)
    # 如果尺寸已经符合要求，直接返回原图
    if new_width == width and new_height == height:
        return image
    # 创建一个白色背景的新图片
    new_image = Image.new('RGB', (new_width, new_height), 'white')
    # 计算粘贴位置，居中放置
    x_offset = (new_width - width) // 2
    y_offset = (new_height - height) // 2
    # 将原图粘贴到新图片上
    new_image.paste(image, (x_offset, y_offset))
    return new_image

def preprocess_detections(
        detections: List[Dict[str, Any]],
        iou_threshold: float = 0.5  # 允许部分重叠，只在 IoU > 0.5 时删除
) -> List[Dict[str, Any]]:
    """
    预处理检测结果，先移除指定类别，然后移除完全包含的框，
    最后通过 IoU 阈值移除重叠的框。
    """
    if not detections:
        return []
    # 过滤指定类别

    valid_detections = [det for det in detections if det['category_id'] not in FilterCategories_VALUES]
    if not valid_detections:
        return []
    # 计算所有边界框和面积
    boxes = [poly_to_bbox(det['poly']) for det in valid_detections]
    areas = [compute_area(box) for box in boxes]
    # 标记要保留的检测
    keep = [True] * len(valid_detections)
    # 按面积从大到小排序
    indices = np.argsort([-area for area in areas])
    # 遍历检测
    for i in range(len(valid_detections)):
        cropped_process = valid_detections[i].get('cropped_image',None)
        if cropped_process is not None and isinstance(cropped_process, Image.Image):
            valid_detections[i]['cropped_image'] = resize_image_for_mvl(cropped_process)
        if not keep[indices[i]]:
            continue
        box_i = boxes[indices[i]]
        for j in range(i + 1, len(valid_detections)):
            if not keep[indices[j]]:
                continue
            box_j = boxes[indices[j]]
            # 用来判断 box_j 是否在 box_i 内部
            if is_contained(box_j, box_i):
                keep[indices[j]] = False
                continue  # 如果是包含关系，直接继续下一个框，不再计算 IoU
            # 如果不完全包含，则继续判断 IoU
            iou = compute_iou(box_i, box_j)
            if iou > iou_threshold:
                keep[indices[j]] = False

    # 收集保留的检测
    filtered_detections = [det for i, det in enumerate(valid_detections) if keep[i]]

    return filtered_detections

def is_contained(box_inner: List[float], box_outer: List[float]) -> bool:
    """
    判断一个边界框 (box_inner) 是否完全包含在另一个边界框 (box_outer) 内部。
    边界框格式为 [x0, y0, x1, y1]。
    """
    # 确保 box_inner 的左上角在 box_outer 的左上角以内或之上
    is_left_top_contained = (
            box_inner[0] >= box_outer[0] and
            box_inner[1] >= box_outer[1]
    )

    # 确保 box_inner 的右下角在 box_outer 的右下角以内或之下
    is_right_bottom_contained = (
            box_inner[2] <= box_outer[2] and
            box_inner[3] <= box_outer[3]
    )

    # 只有当两个角都包含时，才认为 box_inner 完全包含在 box_outer 中
    return is_left_top_contained and is_right_bottom_contained

def batch_preprocess_detections(
        batches_of_detections: List[List[Dict[str, Any]]],
        iou_threshold: float = 0.5
) -> List[List[Dict[str, Any]]]:
    """
    对多个批次的检测结果进行预处理。
    Args:
        batches_of_detections: 批次列表，每个批次包含一个检测结果字典列表。
                               格式: List[List[Dict[str, Any]]]
        iou_threshold: 用于删除重叠框的 IoU 阈值。
    Returns:
        经过预处理的批次列表。
    """
    processed_batches = []
    for detections_list in batches_of_detections:
        # 对每个批次调用原始的预处理函数
        filtered_batch = preprocess_detections(detections_list, iou_threshold)
        processed_batches.append(filtered_batch)
    return processed_batches

if __name__ == '__main__':
    pass