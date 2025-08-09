from argparse import ArgumentParser
import os
from modelscope import snapshot_download, model_file_download

from srcProject.utlis.common import find_project_root

if __name__ == '__main__':
    # 定义模型下载的目标目录
    model_path = os.path.join(find_project_root(), "data/models")
    # 定义需要检查的三个关键文件路径
    files_to_check = [
        os.path.join(model_path, 'structure', 'doclayout_yolo_docstructbench_imgsz1280_2501.pt'),
        os.path.join(model_path, 'Relation', 'config.json'),
        os.path.join(model_path, 'Relation', 'model.safetensors')
    ]
    network_model = [
        os.path.join('models/structure', 'doclayout_yolo_docstructbench_imgsz1280_2501.pt'),
        os.path.join('models/Relation', 'config.json'),
        os.path.join('models/Relation', 'model.safetensors')
    ]
    # model_dir = model_file_download(model_id='Qwen/QwQ-32B-GGUF', file_path='qwq-32b-q4_k_m.gguf')
    # 检查所有文件是否都已存在

    for i in range(len(files_to_check)):
        if os.path.exists(files_to_check[i]):
            continue
        else:
            model_dir = model_file_download(model_id='theysh/TestSnap_model',
                                            file_path=network_model[i],
                                            cache_dir=os.path.dirname(network_model[i]))
            print(f"模型已下载到：{model_dir}")
