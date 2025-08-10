import os
from huggingface_hub import hf_hub_download
from srcProject.utlis.common import find_project_root

def download_if_not_exists(repo_id, local_path, hf_hub_path):
    """
    检查本地文件是否存在，如果不存在则从 Hugging Face Hub 下载。
    """
    # 提取远程文件名，用于构建本地路径
    remote_filename = os.path.basename(hf_hub_path)
    local_filepath = os.path.join(local_path, remote_filename)
    if not os.path.exists(local_filepath):
        print(f"文件 {local_filepath} 不存在，正在从 Hub 下载...")
        # 下载文件并保存到指定路径
        hf_hub_download(
            repo_id=repo_id,
            filename=hf_hub_path,  # 确保这里是完整的远程路径
            local_dir=os.path.join(find_project_root(),'data'),  # 下载到正确的本地目录
            local_dir_use_symlinks=False
        )
        print(f"文件 {local_filepath} 下载完成。")
    else:
        print(f"文件 {local_filepath} 已存在，跳过下载。")


if __name__ == '__main__':
    model_root_path = os.path.join(find_project_root(), "data/models")
    # 调整文件信息，使其更简洁
    files_to_download = [
        {
            "repo_id": "THEYSH/testsnap",
            "local_path": os.path.join(model_root_path, 'structure'),
            "hf_hub_path": "models/structure/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
        },
        {
            "repo_id": "THEYSH/testsnap",
            "local_path": os.path.join(model_root_path, 'relation'),
            "hf_hub_path": "models/relation/config.json"
        },
        {
            "repo_id": "THEYSH/testsnap",
            "local_path": os.path.join(model_root_path, 'relation'),
            "hf_hub_path": "models/relation/model.safetensors"
        }
    ]

    for file_info in files_to_download:
        download_if_not_exists(
            repo_id=file_info['repo_id'],
            local_path=file_info['local_path'],
            hf_hub_path=file_info['hf_hub_path']
        )