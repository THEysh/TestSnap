from pathlib import Path


def find_project_root(marker_file: str = 'requirements.txt') -> Path:
    """
    通过向上遍历目录树，查找包含指定标记文件的项目根目录。
    """
    # 获取当前脚本文件的绝对路径，并转换为 Path 对象
    current_dir = Path(__file__).resolve().parent

    # 向上遍历目录树，直到达到文件系统的根目录
    while True:
        if (current_dir / marker_file).exists():
            return current_dir
        # 如果已经到达文件系统根目录，则停止
        if current_dir == current_dir.parent:
            return None
        # 向上移动一级
        current_dir = current_dir.parent


def get_key_by_value(dictionary, value):
    """
    通过字典的值获取键。

    Args:
        dictionary (dict): 待查找的字典。
        value: 要查找的值。

    Returns:
        str: 如果找到，返回对应的键；否则返回None。
    """
    for key, val in dictionary.items():
        if val == value:
            return key
    return None