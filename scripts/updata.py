from modelscope.hub.api import HubApi

YOUR_ACCESS_TOKEN = 'ms-25d9f4e4-32f2-4811-9c0a-ddfe760653e8'

api = HubApi()
api.login(YOUR_ACCESS_TOKEN)

repo_id = 'theysh/TestSnap_model'
local_folder_path = r'F:\ysh_loc_office\projects\practice\TextSnap\data\models\Relation'
path_in_repo = 'models/Relation'
max_workers = 1

api.upload_folder(
    repo_id=repo_id,
    folder_path=local_folder_path,
    path_in_repo=path_in_repo,
    max_workers=max_workers,
    commit_message='Upload Relation model files' # 这是一个可选的提交信息
)