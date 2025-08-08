import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseDataset(ABC):
    """
    所有数据集类的抽象基类。
    定义了数据集应遵循的基本接口，例如支持通过索引访问元素和获取数据集长度。
    """
    @abstractmethod
    def __len__(self) -> int:
        """
        返回数据集中元素的总数。
        所有继承此基类的子类都必须实现此方法。
        """
        pass

    @abstractmethod
    def __getitem__(self, index: int) -> Any:
        """
        根据给定的索引获取数据集中的一个元素。
        所有继承此基类的子类都必须实现此方法。

        Args:
            index: 要获取的元素的索引。

        Returns:
            Any: 数据集中索引对应的元素。
        """
        pass

    def __iter__(self):
        """
        使数据集可迭代。
        默认实现通过调用 __getitem__ 和 __len__ 来实现迭代。
        """
        for i in range(len(self)):
            yield self[i]
