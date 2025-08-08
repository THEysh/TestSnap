from collections import defaultdict
from typing import List, Dict
import torch
from transformers import LayoutLMv3ForTokenClassification

# 定义常量，用于表示特殊标记的ID
MAX_LEN = 510  # 最大序列长度
CLS_TOKEN_ID = 0  # [CLS] 标记的ID，表示序列的开始
UNK_TOKEN_ID = 3  # [UNK] 标记的ID，表示未知或占位符
EOS_TOKEN_ID = 2  # [EOS] 标记的ID，表示序列的结束


class DataCollator:
    def __call__(self, features: List[dict]) -> Dict[str, torch.Tensor]:
        """
        这个函数用于将一批（batch）训练样本整理成模型可接受的格式。
        它处理截断、添加特殊标记、填充和调整标签等步骤。
        """
        bbox = []
        labels = []
        input_ids = []
        attention_mask = []

        # 1. 截断边界框和标签至最大长度，并构建 input_ids 和 attention_mask
        for feature in features:
            _bbox = feature["source_boxes"]
            if len(_bbox) > MAX_LEN:
                _bbox = _bbox[:MAX_LEN]
            _labels = feature["target_index"]
            if len(_labels) > MAX_LEN:
                _labels = _labels[:MAX_LEN]
            _input_ids = [UNK_TOKEN_ID] * len(_bbox)  # 使用 UNK 标记作为占位符
            _attention_mask = [1] * len(_bbox)       # 所有有效标记的注意力掩码为1
            assert len(_bbox) == len(_labels) == len(_input_ids) == len(_attention_mask)
            bbox.append(_bbox)
            labels.append(_labels)
            input_ids.append(_input_ids)
            attention_mask.append(_attention_mask)

        # 2. 添加 [CLS] 和 [EOS] 特殊标记
        for i in range(len(bbox)):
            # 在序列前后添加占位边界框
            bbox[i] = [[0, 0, 0, 0]] + bbox[i] + [[0, 0, 0, 0]]
            # 在序列前后添加特殊标签（-100表示忽略计算损失）
            labels[i] = [-100] + labels[i] + [-100]
            # 在序列前后添加 [CLS] 和 [EOS] 标记的ID
            input_ids[i] = [CLS_TOKEN_ID] + input_ids[i] + [EOS_TOKEN_ID]
            # 更新注意力掩码
            attention_mask[i] = [1] + attention_mask[i] + [1]

        # 3. 填充到批次中的最大序列长度
        max_len = max(len(x) for x in bbox)
        for i in range(len(bbox)):
            # 填充边界框列表
            bbox[i] = bbox[i] + [[0, 0, 0, 0]] * (max_len - len(bbox[i]))
            # 填充标签列表
            labels[i] = labels[i] + [-100] * (max_len - len(labels[i]))
            # 填充 input_ids 列表
            input_ids[i] = input_ids[i] + [EOS_TOKEN_ID] * (max_len - len(input_ids[i]))
            # 填充注意力掩码列表
            attention_mask[i] = attention_mask[i] + [0] * (
                max_len - len(attention_mask[i])
            )

        # 4. 转换并返回张量字典
        ret = {
            "bbox": torch.tensor(bbox),
            "attention_mask": torch.tensor(attention_mask),
            "labels": torch.tensor(labels),
            "input_ids": torch.tensor(input_ids),
        }
        # 将原始标签中超出最大长度的部分设置为 -100，以便在计算损失时忽略
        ret["labels"][ret["labels"] > MAX_LEN] = -100
        # 原始标签通常是从1开始的索引，这里将其调整为从0开始
        ret["labels"][ret["labels"] > 0] -= 1
        return ret


def boxes2inputs(boxes: List[List[int]]) -> Dict[str, torch.Tensor]:
    """
    将边界框列表转换为模型推理所需的输入格式。
    此函数用于预测阶段，因此不包含标签（labels）。
    """
    # 在边界框前后添加 [CLS] 和 [EOS] 的占位符边界框
    bbox = [[0, 0, 0, 0]] + boxes + [[0, 0, 0, 0]]
    # 构建 input_ids，使用 [CLS]、[UNK] 和 [EOS] 标记
    input_ids = [CLS_TOKEN_ID] + [UNK_TOKEN_ID] * len(boxes) + [EOS_TOKEN_ID]
    # 构建注意力掩码，所有有效标记为1
    attention_mask = [1] + [1] * len(boxes) + [1]
    return {
        "bbox": torch.tensor([bbox]),
        "attention_mask": torch.tensor([attention_mask]),
        "input_ids": torch.tensor([input_ids]),
    }


def prepare_inputs(
    inputs: Dict[str, torch.Tensor], model: LayoutLMv3ForTokenClassification
) -> Dict[str, torch.Tensor]:
    """
    准备模型推理所需的张量。
    负责将张量移动到正确的设备（如GPU）并调整数据类型。
    """
    ret = {}
    for k, v in inputs.items():
        v = v.to(model.device)  # 将张量移动到模型所在的设备
        if torch.is_floating_point(v):
            v = v.to(model.dtype)  # 调整浮点数类型
        ret[k] = v
    return ret


def parse_logits(logits: torch.Tensor, length: int) -> List[int]:
    """
    解析模型的输出（logits）以生成唯一的阅读顺序。

    :param logits: 模型的原始 logits 输出
    :param length: 输入序列的原始长度（即边界框的数量）
    :return: 一个整数列表，表示排序后的索引
    """
    # 截取 logits 矩阵中与实际边界框对应的部分
    logits = logits[1 : length + 1, :length]
    # 对每个边界框，按 logits 排序，得到一个可能的顺序列表
    orders = logits.argsort(descending=False).tolist()
    # 初始顺序：取每个边界框最可能排在的位置
    ret = [o.pop() for o in orders]
    while True:
        order_to_idxes = defaultdict(list)
        # 将相同的预测顺序分组
        for idx, order in enumerate(ret):
            order_to_idxes[order].append(idx)
        # 筛选出有冲突（重复）的预测顺序
        order_to_idxes = {k: v for k, v in order_to_idxes.items() if len(v) > 1}
        if not order_to_idxes:
            break  # 没有冲突，循环结束
        # 解决冲突
        for order, idxes in order_to_idxes.items():
            # 找到有冲突的边界框在原始 logits 上的评分
            idxes_to_logit = {}
            for idx in idxes:
                idxes_to_logit[idx] = logits[idx, order]
            # 根据评分从高到低排序
            idxes_to_logit = sorted(
                idxes_to_logit.items(), key=lambda x: x[1], reverse=True
            )
            # 保留评分最高的作为该顺序，将其余的分配到下一个最可能的顺序
            for idx, _ in idxes_to_logit[1:]:
                ret[idx] = orders[idx].pop()

    return ret


def check_duplicate(a: List[int]) -> bool:
    """
    检查列表中是否有重复元素。
    """
    return len(a) != len(set(a))