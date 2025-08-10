from huggingface_hub import HfApi
import os
from dotenv import load_dotenv # 导入 load_dotenv 函数
from srcProject.utlis.common import find_project_root
# 加载 .env 文件中的环境变量
load_dotenv()
api = HfApi(token=os.getenv("HF_TOKEN"))
api.upload_folder(
    folder_path=os.path.join(find_project_root(),"data/models/Relation"),
    repo_id="THEYSH/testsnap",
    repo_type="model",
    path_in_repo="models/relation"
)
