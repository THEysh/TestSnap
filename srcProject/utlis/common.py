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


def find_file_with_suffix(directory_path, filename_base, file_extension):
    """
    在一个目录下查找文件名以特定后缀结尾的文件。

    Args:
        directory_path (str): 要搜索的目录路径。
        filename_base (str): 文件名的主体部分，例如 'demo1_页面_1'。
        file_extension (str): 文件的扩展名，例如 '.png'。

    Returns:
        str or None: 如果找到文件，返回它的完整路径；否则返回 None。
    """
    # 组合成完整的后缀，例如 'demo1_页面_1.png'
    target_suffix = f"{filename_base}{file_extension}"

    # 检查目录是否存在
    if not os.path.isdir(directory_path):
        print(f"错误: 目录 '{directory_path}' 不存在。")
        return None

    # 遍历目录中的所有文件和文件夹
    for item in os.listdir(directory_path):
        # 构造完整的路径
        item_path = os.path.join(directory_path, item)

        # 只处理文件，并检查文件名是否以目标后缀结尾
        if os.path.isfile(item_path) and item.endswith(target_suffix):
            # 找到第一个匹配的文件，返回它的路径
            return item_path

    # 如果遍历完所有文件都没有找到
    print(f"在目录 '{directory_path}' 中未找到以 '{target_suffix}' 结尾的文件。")
    return None
