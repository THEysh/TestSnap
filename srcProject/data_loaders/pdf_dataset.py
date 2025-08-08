"""
PDF 数据集实现。

PDFDataset 类用于：
- 加载 PDF 文件
- 解析 PDF 结构
- 将 PDF 页面转换为适合处理的格式
"""
import os
from typing import List, Dict, Any, Tuple
from PIL import Image
from pymupdf import pymupdf
from srcProject.data_loaders.Base_dataset import BaseDataset # 确保导入路径正确

class PDFDataset(BaseDataset):
    """
    PDF 数据集实现。
    负责：
    - 加载 PDF 文件
    - 解析 PDF 结构（获取页面图像和文本层）
    - 将 PDF 页面转换为适合处理的格式（PIL Image）
    """
    def __init__(self, file_path: str): # 明确 file_path 的类型提示
        # BaseDataset 的 __init__ 方法不接受 file_path 参数，因此不带参数调用。
        # super().__init__() 是正确的用法。
        super().__init__()
        self.file_path = file_path
        self._document = None # 初始化为 None
        self._open_document()

    def _open_document(self):
        """打开 PDF 文档并存储其引用。"""
        # 检查文件扩展名是否为 .pdf
        if not self.file_path.lower().endswith('.pdf'):
            raise ValueError(f"文件 {self.file_path} 不是有效的 PDF 文件。")

        # 检查文件是否存在
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"文件 {self.file_path} 不存在。")

        try:
            # 使用 pymupdf.open() 打开文档
            self._document = pymupdf.open(self.file_path)
            print(f"成功打开 PDF 文档: {self.file_path}，共 {len(self)} 页。")
        except Exception as e:
            # 捕获更具体的异常，例如文件损坏或权限问题
            raise IOError(f"无法打开或读取 PDF 文件 {self.file_path}: {e}")

    def __len__(self) -> int:
        """返回 PDF 文档的总页数。"""
        if self._document is None:
            return 0
        return self._document.page_count

    def __getitem__(self, page_index: int) -> Dict[str, Any]:
        """
        根据给定的页码获取 PDF 文档中的一个页面数据。
        这使得 PDFDataset 实例可以像列表一样通过索引访问页面。

        Args:
            page_index: 要获取的页码（从 0 开始）。

        Returns:
            Dict[str, Any]: 包含页面图像和文本跨度信息的字典。
                            例如：{'image': PIL.Image, 'spans': List[Dict]}
        Raises:
            IndexError: 如果页码超出文档范围。
        """
        if not (0 <= page_index < self.__len__()):
            raise IndexError(f"页码 {page_index} 超出范围。文档共有 {self.__len__()} 页。")

        # 这里你可以选择返回什么样的数据，通常是图像和文本信息
        page_image = self.get_page_image(page_index)
        page_spans = self.get_page_spans(page_index)

        return {
            "image": page_image,
            "spans": page_spans
        }

    def get_page_image(self, page_index: int, dpi: int = 300) -> Image.Image:
        """
        获取指定页码的渲染图像。
        Args:
            page_index: 页码（从 0 开始）。
            dpi: 渲染图像的分辨率（每英寸点数）。更高的 DPI 意味着更高的分辨率图像。

        Returns:
            页面的 PIL Image 对象。

        Raises:
            ValueError: 如果文档未打开或页码超出范围。
        """
        if not self._document:
            raise ValueError("PDF 文档未打开。请先调用 _open_document() 方法。")

        if not (0 <= page_index < self._document.page_count):
            raise ValueError(f"页码 {page_index} 超出范围。文档共有 {self._document.page_count} 页。")

        # 计算缩放因子：dpi / 72 (MuPDF 默认的 DPI)
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom) # 创建一个缩放矩阵

        page = self._document.load_page(page_index) # 加载指定页
        pix = page.get_pixmap(matrix=mat) # 渲染页面为 Pixmap 对象

        # 将 Pixmap 转换为 PIL Image 对象
        # pix.samples 是图像的原始字节数据
        # pix.width 和 pix.height 是图像的尺寸
        # pix.n 是每个像素的字节数 (3 for RGB, 4 for RGBA)
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        return img

    def get_page_spans(self, page_index: int) -> List[Dict[str, Any]]:
        """
        获取指定页码的文本跨度（spans）信息。

        Args:
            page_index: 页码（从 0 开始）。

        Returns:
            一个字典列表，每个字典代表一个文本跨度，包含其文本、边界框、字体、字号等信息。

        Raises:
            ValueError: 如果文档未打开或页码超出范围。
        """
        if not self._document:
            raise ValueError("PDF 文档未打开。请先调用 _open_document() 方法。")

        if not (0 <= page_index < self._document.page_count):
            raise ValueError(f"页码 {page_index} 超出范围。文档共有 {self._document.page_count} 页。")

        page = self._document.load_page(page_index)

        # 使用 get_text("dict") 获取页面的详细文本结构
        # 返回一个字典，其中包含 'blocks' 键，对应一个文本块列表
        text_info = page.get_text("dict")

        spans_data = []

        # 遍历文本块 (blocks)
        for block in text_info.get("blocks", []):
            if block["type"] == 0: # 0 表示文本块，1 表示图像块
                # 遍历行 (lines)
                for line in block.get("lines", []):
                    # 遍历跨度 (spans)
                    for span in line.get("spans", []):
                        # 提取我们关心的 span 信息
                        span_info = {
                            "text": span.get("text"),
                            "bbox": span.get("bbox"), # (x0, y0, x1, y1)
                            "font": span.get("font"),
                            "size": span.get("size"),
                            "color": span.get("color"), # 整数 RGB 值
                            "flags": span.get("flags") # 字体标志，如粗体、斜体等
                        }
                        spans_data.append(span_info)

        return spans_data

    def get_page_dimensions(self, page_index: int, dpi: int = 300, to_pixels: bool = True) -> Tuple[int, int]:
        """
        获取指定页面的尺寸。可以返回原始点单位或转换后的像素单位。
        Args:
            page_index (int): 页码（从 0 开始）。
            dpi (int): 如果 to_pixels 为 True，用于转换的 DPI 值。
            to_pixels (bool): 如果为 True，将点单位尺寸转换为像素。
        Returns:
            一个元组 (page_width, page_height)，表示页面的宽度和高度。
        Raises:
            ValueError: 如果文档未打开或页码超出范围。
        """
        if not self._document:
            raise ValueError("PDF 文档未打开。请先调用 _open_document() 方法。")

        if not (0 <= page_index < self._document.page_count):
            raise ValueError(f"页码 {page_index} 超出范围。文档共有 {self._document.page_count} 页。")

        page = self._document.load_page(page_index)

        # 内部函数：将点尺寸转换为像素尺寸
        def _to_pixels(point_width: float, point_height: float, dpi: int) -> Tuple[int, int]:
            """
            将点单位尺寸转换为像素。
            """
            # PDF 中 1 英寸 = 72 点
            # 像素 = (点数 / 72) * DPI
            pixel_width = int(round((point_width / 72.0) * dpi))
            pixel_height = int(round((point_height / 72.0) * dpi))
            return pixel_width, pixel_height

        # 获取原始点尺寸
        point_width, point_height = page.rect.width, page.rect.height

        if to_pixels:
            # 如果 to_pixels 为 True，则调用内部函数进行转换
            return _to_pixels(point_width, point_height, dpi)
        else:
            # 否则，返回原始点尺寸
            return int(round(point_width)), int(round(point_height))

    def close(self):
        """关闭 PDF 文档。"""
        if self._document:
            self._document.close()
            self._document = None
            print(f"PDF 文档 {self.file_path} 已关闭。")

    def __del__(self):
        """
        析构函数：确保在对象被销毁时关闭 PDF 文档，以释放资源。
        """
        # 确保在对象被垃圾回收时关闭文档
        self.close()

