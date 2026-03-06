"""
Model manager for coordinating multiple models.

Responsible for:
- Loading and managing all model instances
- Resource allocation across models
- Coordinating inference across different model types
- Corresponds to MonkeyOCR_model in the original implementation
"""
from srcProject.config.settings import LAYOUT_MODEL_NAME, LAYOUT_WEIGHTS_PATH, READ_MODEL_NAME, READ_WEIGHTS_PATH, \
    FLOW_API_NAME, FLOW_API_KEY, FLOW_URL, DEVICE, FLOW_USE_MODEL_NAME, \
    CHAT_API_NAME, CHAT_API_KEY, CHAT_URL, CHAT_MODEL_NAME
from srcProject.models.layout_detector import DocLayoutYOLO
from srcProject.models.layout_reader import LayoutReader
from srcProject.models.model_base import BaseModel
from srcProject.models.siliconflow_api import Silicon
from srcProject.models.reader_xy_cut import XY_CUT
from srcProject.models.chat_model import SiliconChatModel

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
        elif api_name.lower() == 'siliconflow_chat':
            return SiliconChatModel(api_keys=api_key, base_url=base_url, model_name=model_name, device='api')
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
        self._read_model_name = READ_MODEL_NAME
        print(f"已加载阅读顺序模型/算法: {READ_MODEL_NAME}")

        self.ocr_recognizer = ModelFactory.create(
            api_key=FLOW_API_KEY,
            base_url=FLOW_URL,
            api_name=FLOW_API_NAME,
            model_name= FLOW_USE_MODEL_NAME
        )
        self._ocr_api_name = FLOW_API_NAME
        self._ocr_base_url = FLOW_URL
        self._ocr_model_name = FLOW_USE_MODEL_NAME
        self._ocr_api_keys = self._normalize_api_keys(FLOW_API_KEY)
        print(f"已加载OCR-api模型: {FLOW_API_NAME},当前激活: {FLOW_USE_MODEL_NAME}")

        # 加载聊天模型
        chat_api_name = 'siliconflow_chat' if CHAT_API_NAME.lower() == 'siliconflow' else CHAT_API_NAME.lower()
        self.chat_model = ModelFactory.create(
            api_key=CHAT_API_KEY,
            base_url=CHAT_URL,
            api_name=chat_api_name,
            model_name=CHAT_MODEL_NAME
        )
        print(f"已加载Chat-api模型: {CHAT_API_NAME}, 当前激活: {CHAT_MODEL_NAME}")

    def _normalize_api_keys(self, api_key: list | str | None) -> tuple[str, ...]:
        if api_key is None:
            return tuple()
        if isinstance(api_key, str):
            k = api_key.strip()
            return (k,) if k else tuple()
        if isinstance(api_key, list):
            out: list[str] = []
            for it in api_key:
                if not it:
                    continue
                s = str(it).strip()
                if s:
                    out.append(s)
            return tuple(out)
        s = str(api_key).strip()
        return (s,) if s else tuple()

    def change_read_model (self, model_name:str):
        if model_name and model_name == getattr(self, "_read_model_name", None):
            return True
        self.read_model = ModelFactory.create(
            model_name=model_name,
            model_Path=READ_WEIGHTS_PATH,
            device=self.device
        )
        self._read_model_name = model_name
        print(f"已加载阅读顺序模型/算法: {model_name}")
        return True

    def change_ocr_recognizer(self, model_name:str,
                               api_name:str =None,
                               api_key:list|str =None,
                               base_url:str =None):
        if not model_name:  # 等价于 model_name is None or model_name == ""
            print("model_name is None or empty; 更新失败")
            return False
        if not api_key:
            print("api_key is None or empty; 更新失败")
            return False
        if not base_url:
            print("base_url is None or empty; 更新失败")
            return False
        if not api_name:
            api_name = FLOW_API_NAME
        if str(api_name).lower() != 'siliconflow':
            raise ValueError("仅支持 siliconflow 作为 OCR API")

        next_keys = self._normalize_api_keys(api_key)
        next_url = str(base_url or "").strip()
        next_model = str(model_name or "").strip()
        cur_keys = getattr(self, "_ocr_api_keys", tuple())
        cur_url = str(getattr(self, "_ocr_base_url", "") or "").strip()
        cur_model = str(getattr(self, "_ocr_model_name", "") or "").strip()

        if next_keys == cur_keys and next_url == cur_url and next_model == cur_model:
            return True

        if next_keys == cur_keys and next_url == cur_url and hasattr(self.ocr_recognizer, "api_model_name"):
            try:
                setattr(self.ocr_recognizer, "api_model_name", next_model)
                self._ocr_model_name = next_model
                print(f"已加载OCR-api模型: {api_name},当前激活: {next_model}")
                return True
            except Exception:
                pass

        self.ocr_recognizer = ModelFactory.create(
            api_key=api_key,
            base_url=base_url,
            api_name=api_name,
            model_name= model_name
        )
        self._ocr_api_name = api_name
        self._ocr_base_url = next_url
        self._ocr_model_name = next_model
        self._ocr_api_keys = next_keys
        print(f"已加载OCR-api模型: {api_name},当前激活: {model_name}")
        return True

    def change_chat_model(self, model_name:str,
                          api_name:str =None,
                          api_key:list|str =None,
                          base_url:str =None):
        if not model_name:
            print("model_name is None or empty; 更新失败")
            return False
        if not api_key:
            print("api_key is None or empty; 更新失败")
            return False
        if not base_url:
            print("base_url is None or empty; 更新失败")
            return False
        if not api_name:
            api_name = CHAT_API_NAME
        if str(api_name).lower() != 'siliconflow':
            raise ValueError("仅支持 siliconflow 作为 Chat API")
        chat_api_name = 'siliconflow_chat' if api_name.lower() == 'siliconflow' else api_name.lower()
        self.chat_model = ModelFactory.create(
            api_key=api_key,
            base_url=base_url,
            api_name=chat_api_name,
            model_name=model_name
        )
        print(f"已加载Chat-api模型: {api_name},当前激活: {model_name}")
        return True
