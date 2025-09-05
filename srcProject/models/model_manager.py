"""
Model manager for coordinating multiple models.

Responsible for:
- Loading and managing all model instances
- Resource allocation across models
- Coordinating inference across different model types
- Corresponds to MonkeyOCR_model in the original implementation
"""
from srcProject.config.settings import LAYOUT_MODEL_NAME, LAYOUT_WEIGHTS_PATH, READ_MODEL_NAME, READ_WEIGHTS_PATH, \
    FLOW_API_NAME, FLOW_API_KEY, FLOW_URL, DEVICE, FLOW_USE_MODEL_NAME
from srcProject.models.google_api import Google
from srcProject.models.layout_detector import DocLayoutYOLO
from srcProject.models.layout_reader import LayoutReader
from srcProject.models.model_base import BaseModel
from srcProject.models.siliconflow_api import Silicon
from srcProject.models.reader_xy_cut import XY_CUT

class ModelFactory:
    @staticmethod
    def create(model_name: str='',
               model_Path: str='',
               device: str = 'cuda',
               api_key: list|str = None,
               base_url: str = '',
               api_name:str = 'api') -> BaseModel:
        if model_name.lower() == 'doclayout_yolo':
            return DocLayoutYOLO(model_Path, device)
        elif model_name.lower() == 'layoutlmv3':
            return LayoutReader(model_Path, device)
        elif model_name.lower() == 'xy_cut':
            return XY_CUT()
        elif api_name.lower() == 'siliconflow':
            return Silicon(api_keys=api_key, base_url=base_url, model_name=model_name)
        elif api_name.lower() == 'google':
            return Google(api_keys=api_key, model_name=model_name)
        else:
            raise ValueError(f"不支持的模型名称: {model_name}")

class ModelManager:
    def __init__(self,device: str = DEVICE):
        self.device = device
        print(f"使用{self.device}加载了模型")
        # 使用工厂创建布局检测器实例
        self.layout_detector = ModelFactory.create(
            model_name=LAYOUT_MODEL_NAME,
            model_Path=LAYOUT_WEIGHTS_PATH,
            device=device
        )
        # 现在可以通过检测器实例访问类别名称映射
        self.layout_category_names = self.layout_detector.names
        print(f"已加载布局模型: {LAYOUT_MODEL_NAME}，类别: {self.layout_category_names}")

        self.read_model = ModelFactory.create(
            model_name=READ_MODEL_NAME,
            model_Path=READ_WEIGHTS_PATH,
            device=device
        )
        print(f"已加载阅读顺序模型/算法: {READ_MODEL_NAME}")

        self.ocr_recognizer = ModelFactory.create(
            api_key=FLOW_API_KEY,
            base_url=FLOW_URL,
            api_name=FLOW_API_NAME,
            model_name= FLOW_USE_MODEL_NAME
        )
        print(f"已加载OCR-api模型: {FLOW_API_NAME},当前激活: {FLOW_USE_MODEL_NAME}")

    def change_read_model (self, model_name:str):
        self.read_model = ModelFactory.create(
            model_name=model_name,
            model_Path=READ_WEIGHTS_PATH,
            device=self.device
        )
        print(f"已加载阅读顺序模型/算法: {model_name}")

    def change_ocr_recognizer(self, model_name:str,
                               api_name=None,
                               api_key:list|str=None,
                               base_url=None):
        if model_name is None:
            print("model_name is None; 更新失败")
            return
        if api_name is None:
            api_name = FLOW_API_NAME
        if api_key is None:
            api_key = FLOW_API_KEY
        if base_url is None:
            base_url = FLOW_URL
        print("def change_ocr_recognizer :",api_key,base_url,api_name,model_name)
        self.ocr_recognizer = ModelFactory.create(
            api_key=api_key,
            base_url=base_url,
            api_name=api_name,
            model_name= model_name
        )
        print(f"已加载OCR-api模型: {api_name},当前激活: {model_name}")
if __name__ == '__main__':
    # 获取当前脚本所在的目录
    ModelManager(device='cpu').change_ocr_recognizer(model_name="models/gemma-3-27b-it",
                               api_name="google",
                               api_key="AIzaSyBNYS4c1SRY7aWdoK-jTqlHaH7ApgAtc9g")