# src/models/layout_detector.py
from abc import ABC, abstractmethod # 导入抽象基类模块
from PIL import Image
from typing import List, Dict, Any
# 字典，例如 {'bbox': [x0,y0,x1,y1], 'category_id': int, 'score': float}
LayoutDetection = Dict[str, Any]
# 列表，包含一张的所有检测结果
PageDetections = List[LayoutDetection]
# 列表，包含多张的检测结果 (每项对应一页的PageDetections)
BatchDetections = List[PageDetections]
class BaseModel(ABC):
    """
    所有模型的抽象基类。
    定义了加载和预测布局的通用接口。
    """
    def __init__(self, model_path: str, device: str = 'cuda'):
        self.model_path = model_path
        self.device = device
        self._load_model() # 调用内部方法加载模型

    @abstractmethod
    def _load_model(self):
        """
        加载具体布局检测模型的抽象方法。
        每个具体实现必须定义其模型如何加载。
        """
        pass

    @property
    @abstractmethod
    def names(self) -> Dict[int, str]:
        """
        返回模型类别 ID 到名称映射的抽象属性。
        """
        pass
