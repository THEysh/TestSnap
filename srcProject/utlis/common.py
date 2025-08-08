from pathlib import Path
import os

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

def prepare_directory(path):
    """
    检查文件夹是否存在。如果存在，return；如果不存在，则创建。

    Args:
        path (str): 要处理的文件夹路径。
    """
    # 检查路径是否存在，并且是否是一个文件
    if os.path.exists(path) and os.path.isfile(path):
        raise ValueError(f"提供的路径 '{path}' 是一个文件，而不是文件夹。请提供一个文件夹路径。")
    if os.path.exists(path):
        # 文件夹存在
        return
    else:
        # 文件夹不存在，创建它
        print(f"文件夹 '{path}' 不存在，正在创建...")
        os.makedirs(path)
        print(f"文件夹 '{path}' 已创建。")