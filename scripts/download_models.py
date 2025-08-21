import os
from huggingface_hub import snapshot_download

from srcProject.config.settings import READ_MODEL_NAME
from srcProject.utlis.common import find_project_root

# https://huggingface.co/THEYSH/testsnap/tree/main/models
# 可以直接进入手动下载models，下载好models后，手动放入./data目录

DOWNLOAD_CONFIG = {
    "models/structure": [
        "models/structure/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
    ],
    "models/relation": [
        "models/relation/model.safetensors",
        "models/relation/config.json"
    ]
}

def check_files_exist(local_dir, subfolder):
    """
    检查指定子目录下的所有必要文件是否存在。

    Args:
        local_dir (str): 本地保存路径，例如 'data/'
        subfolder (str): Hugging Face 仓库中的子目录

    Returns:
        bool: 所有文件都存在返回 True，否则返回 False。
    """
    files_to_check = DOWNLOAD_CONFIG.get(subfolder)
    if not files_to_check:
        print(f"警告：未找到 {subfolder} 的配置信息。")
        return False

    all_exist = True
    for file_path in files_to_check:
        full_path = os.path.join(local_dir, file_path)
        exists = os.path.exists(full_path)
        print(f"检查文件 {full_path}：{'存在' if exists else '不存在'}")
        if not exists:
            all_exist = False

    return all_exist


def download_and_verify_model(repo_id, subfolder, local_dir):
    """
    检查本地模型文件，如果缺失则从 Hugging Face Hub 下载，并进行验证。
    Args:
        repo_id (str): Hugging Face 仓库 ID
        subfolder (str): 要下载的子目录
        local_dir (str): 本地保存路径
    """
    local_path = os.path.join(local_dir, subfolder)

    if check_files_exist(local_dir, subfolder):
        print(f"目录 {local_path} 的必要文件已存在，跳过下载。")
        return
    print(f"目录 {local_path} 的必要文件缺失，正在从 Hub 下载...")
    # 使用 allow_patterns 精确下载指定子目录下的所有文件，避免下载不必要的文件
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        allow_patterns=[f"{subfolder}/*"]
    )
    print(f"目录 {local_path} 下载完成。")


if __name__ == '__main__':
    model_root_path = os.path.join(find_project_root(), "data")

    dirs_to_download = [{"repo_id": "THEYSH/testsnap", "subfolder": "models/structure"},]
    if READ_MODEL_NAME.lower() == "layoutLMv3":
        dirs_to_download.append({"repo_id": "THEYSH/testsnap", "subfolder": "models/relation"})

    for dir_info in dirs_to_download:
        download_and_verify_model(
            repo_id=dir_info['repo_id'],
            subfolder=dir_info['subfolder'],
            local_dir=model_root_path
        )
        print("-" * 50)
