"""
Layout detection model interface.

Provides classes for:
- Encapsulating layout detection models (e.g., YOLOv)
- Inference code for document layout analysis
- Detection result processing
"""
from doclayout_yolo import YOLOv10
from srcProject.config.constants import LAYOUT_SETTING_IOU, LAYOUT_SETTING_CONF, LAYOUT_SETTING_IMGSIZE, \
    BlockType_MEMBER
from srcProject.models.model_base import BaseModel, BatchDetections, PageDetections
from typing import List, Dict, Any

class DocLayoutYOLO(BaseModel):
    """
    DocLayoutYOLO 模型的具体实现。
    """
    def __init__(self,model_path: str, device: str = 'cuda'):
        super().__init__(model_path, device)
        self.name = "doclayout_yolo"

    def _load_model(self):
        print(f"正在 {self.device} 上从 {self.model_path} 加载 DocLayoutYOLO 模型")
        # 替换为你的 DocLayoutYOLO 模型的实际加载逻辑
        self.model = YOLOv10(self.model_path).to(self.device)
        print(f"加载 DocLayoutYOLO 模型成功")

    def batch_predict(self, images: list, batch_size: int) -> BatchDetections:
        # 检查 images 是否为列表
        if not isinstance(images, list):
            raise TypeError("参数 'images' 必须是一个列表。")
        # 检查列表中的元素是否都是字典
        if all(isinstance(item, dict) for item in images):
            connect = [item["image"] for item in images]
            # 在这里，您还需要添加对字典键的异常处理，"image" 键是否存在
            try:
                connect = [item["image"] for item in images]
                return self._batch_predict(connect, batch_size)
            except KeyError:
                raise KeyError("当 'images' 是字典列表时，每个字典必须包含 'image' 键。")
        else:
            return self._batch_predict(images, batch_size)

    def _batch_predict(self, images:List, batch_size:int) -> BatchDetections:
        images_layout_res = []
        for index in range(0, len(images), batch_size):
            # [image_res.cpu() for image_res in ...] (列表推导式)
            doclayout_yolo_res = [
                image_res.cpu()
                for image_res in self.model.predict(
                    images[index : index + batch_size],
                    imgsz=LAYOUT_SETTING_IMGSIZE,
                    conf=LAYOUT_SETTING_CONF,
                    iou=LAYOUT_SETTING_IOU,
                    verbose=False,
                    device=self.device,
                )
            ]
            for image_res in doclayout_yolo_res:
                layout_res = []
                for xyxy, conf, cla in zip(
                    image_res.boxes.xyxy,
                    image_res.boxes.conf,
                    image_res.boxes.cls,
                ):
                    xmin, ymin, xmax, ymax = [int(p.item()) for p in xyxy]
                    new_item = {
                        "category_id": int(cla.item()),
                        "poly": [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax],
                        "score": round(float(conf.item()), 3),
                    }
                    layout_res.append(new_item)
                images_layout_res.append(layout_res)

        return images_layout_res

    def predict(self, image)-> PageDetections:
        layout_res = []  # 最终要返回的列表
        doclayout_yolo_res = self.model.predict(
            image,
            imgsz=LAYOUT_SETTING_IMGSIZE,
            conf=LAYOUT_SETTING_CONF,
            iou=LAYOUT_SETTING_IOU,
            verbose=False, device=self.device
        )[0]  # [0] 表示取第一个（也是唯一一个）图像的预测结果
        for xyxy, conf, cla in zip(
                doclayout_yolo_res.boxes.xyxy.cpu(),  # 边界框坐标
                doclayout_yolo_res.boxes.conf.cpu(),  # 置信度
                doclayout_yolo_res.boxes.cls.cpu(),  # 类别ID
        ):
            xmin, ymin, xmax, ymax = [int(p.item()) for p in xyxy]  # 将 tensor 转为 int
            new_item = {
                "category_id": int(cla.item()),  # 类别ID
                "poly": [xmin, ymin, xmax, ymin, xmax, ymax, xmin, ymax],  # 四边形顶点坐标
                "score": round(float(conf.item()), 3),  # 置信度，保留三位小数
            }
            layout_res.append(new_item)
        print(layout_res)
        return layout_res

    @property
    def names(self) -> Dict[int, str]:
        """
        Returns the model's class ID to name mapping, prioritizing BlockType names.
        This property is accessed by ModelManager to set layout_category_names.
        """

        return BlockType_MEMBER