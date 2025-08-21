import os.path
from abc import ABC, abstractmethod
import torch
from PIL import Image, ImageDraw
from transformers import LayoutLMv3ForTokenClassification
from srcProject.models.helpers import boxes2inputs, prepare_inputs, parse_logits
from srcProject.models.model_base import BaseModel
from srcProject.utlis.aftertreatment import normalize_polygons_to_bboxes
from srcProject.utlis.common import find_project_root
from typing import List, Dict, Any


class LayoutReader(BaseModel):
    """
    一个基于 LayoutLMv3ForTokenClassification 的阅读顺序模型。
    它接收边界框列表，并预测它们的阅读顺序。
    """
    def __init__(self, model_path: str, device: str = 'cuda'):
        # BaseModel 的 __init__ 会自动调用 _load_model()
        super().__init__(model_path, device)
        self.name = "layout_reader"

    def _load_model(self):
        """
        从预训练路径加载 LayoutLMv3ForTokenClassification 模型。
        """
        print(f"正在 {self.device} 上从 {self.model_path} 加载 LayoutLMv3ForTokenClassification 模型")
        try:
            self.model = LayoutLMv3ForTokenClassification.from_pretrained(
                self.model_path
            )
            # 将模型移动到指定设备并设置为评估模式
            self.model.to(self.device).eval()
            print("加载 LayoutLMv3ForTokenClassification 模型成功")
        except Exception as e:
            raise RuntimeError(f"加载模型失败: {e}")

    def predict(self, boxes: List[List[int]]) -> List[int]:
        """
        预测单个页面中一组边界框的阅读顺序。
        Args:
            boxes (List[List[int]]): 页面上所有元素的边界框列表，格式为 [[x0, y0, x1, y1], ...]。
                                     注意：这里假设边界框已经归一化或模型内部处理。
        Returns:
            List[int]: 一个整数列表，表示原始输入列表的排序索引。
        """
        if not self.model:
            raise RuntimeError("模型未加载。")
        # 将边界框列表转换为模型输入
        inputs = boxes2inputs(boxes)
        # 准备模型输入
        inputs = prepare_inputs(inputs, self.model)
        with torch.no_grad():
            # 进行推理，获取 logits
            outputs = self.model(**inputs)
            logits = outputs.logits.cpu().squeeze(0)
        # 解析 logits，得到排序索引
        return parse_logits(logits, len(boxes))

    def batch_predict(self, data:List[List[Dict[str, Any]]]) -> List[List[int]]:
        """
        批量预测多个页面中边界框的阅读顺序。
        Args:
            data (List[List[Dict[str, Any]]]): 多个页面的边界框列表。

        Returns:
            List[List[int]]: 每个页面的排序索引列表。
        """
        list_of_boxes = normalize_polygons_to_bboxes(data)
        if not self.model:
            raise RuntimeError("模型未加载。")
        all_sorted_indices = []
        for boxes in list_of_boxes:
            # 批量预测实际上是对每个页面进行单次预测，然后收集结果
            # 如果模型支持真正的 batch-level 推理，这里可以优化
            # 但根据你的代码，它是在循环中逐页预测的
            sorted_indices = self.predict(boxes)
            all_sorted_indices.append(sorted_indices)

        return all_sorted_indices

    def names(self) -> Dict[int, str]:
        """
        LayoutReader 模型不预测类别，因此此属性返回一个空字典。
        """
        return {}


def find_reading_order_index(reading_order: List[List[int]]) -> List[List[int]]:
    """
    在一个阅读顺序的列表或嵌套列表中找到给定ID的索引位置。
    Args:
        reading_order (List[List[int]]): 包含内容块ID的阅读顺序列表或嵌套列表。
                                        例如: [[1, 2], [3, 4, 5], [6], ...]

    Returns:
        int: 给定索引在列表中的索引（即它的阅读顺序）。如果未找到，则返回 -1。
    """
    # 遍历外部列表
    res = []
    for i, sublist in enumerate(reading_order):
        temp_list = []
        for j, item in enumerate(sublist):
            temp_list.append(sublist.index(j))
        res.append(temp_list)
    # 如果遍历完所有列表都没有找到，返回 -1
    return res

if __name__ == '__main__':
    pass
