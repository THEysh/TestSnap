# src/config/constants.py
from enum import Enum
LAYOUT_SETTING_IMGSIZE = 1280
LAYOUT_SETTING_CONF = 0.3
LAYOUT_SETTING_IOU = 0.1
# --- 核心枚举：单一数据源 ---
class BlockType(Enum):
    TITLE = 0
    PLAIN_TEXT = 1
    ABANDON = 2
    FIGURE = 3
    FIGURE_CAPTION = 4
    TABLE = 5
    TABLE_CAPTION = 6
    TABLE_FOOTNOTE = 7
    ISOLATE_FORMULA = 8
    FORMULA_CAPTION = 9

# 在程序启动时，构建一个值到成员的映射字典
BlockType_MEMBER = BlockType._value2member_map_
# {
#     0: <BlockType.TITLE: 0>,
#     1: <BlockType.PLAIN_TEXT: 1>,
#     2: <BlockType.ABANDON: 2>,
#     3: <BlockType.FIGURE: 3>,
#     4: <BlockType.FIGURE_CAPTION: 4>,
#     5: <BlockType.TABLE: 5>,
#     6: <BlockType.TABLE_CAPTION: 6>,
#     7: <BlockType.TABLE_FOOTNOTE: 7>,
#     8: <BlockType.ISOLATE_FORMULA: 8>,
#     9: <BlockType.FORMULA_CAPTION: 9>
# }

class ParseMode(Enum):
    OCR = "ocr"
# 使用字典推导式从 BlockType 生成 CLASS_INF
CLASS_INF = {member.name.lower().replace('_', ' '): member.value for member in BlockType}
# 结果: {'title': 0, 'plain text': 1, 'abandon': 2, ...}

OCR_RECOGNITION_TYPES = {
    BlockType.TITLE,
    BlockType.PLAIN_TEXT,
    BlockType.FIGURE_CAPTION,
    BlockType.TABLE,
    BlockType.TABLE_CAPTION,
    BlockType.TABLE_FOOTNOTE,
    BlockType.ISOLATE_FORMULA,
}
# 动态生成 OCR_TEXT 列表
OCR_TEXT_VALUES = [member.value for member in OCR_RECOGNITION_TYPES]

FilterCategories_TYPES = {BlockType.ABANDON, BlockType.FORMULA_CAPTION}
FilterCategories_VALUES = [member.value for member in FilterCategories_TYPES]

# --- 颜色映射 ---
DEFAULT_COLORS = {
    BlockType.TITLE: (255, 0, 0),
    BlockType.PLAIN_TEXT: (0, 0, 255),
    BlockType.ABANDON: (128, 128, 128),
    BlockType.FIGURE: (0, 255, 0),
    BlockType.FIGURE_CAPTION: (0, 128, 0),
    BlockType.TABLE: (255, 165, 0),
    BlockType.TABLE_CAPTION: (255, 69, 0),
    BlockType.TABLE_FOOTNOTE: (139, 0, 0),
    BlockType.ISOLATE_FORMULA: (128, 0, 128),
    BlockType.FORMULA_CAPTION: (75, 0, 130),
}
DEFAULT_COLOR_UNKNOWN = (200, 200, 200)

# --- 指令映射 ---
latex_expression = "You don't need to worry about the line breaks in the image, don't use them when outputting. When handling non-formula content, please identify and output the text directly, without using formula editing symbols like `$` or `\mathrm`. For content containing formulas, you must use standard LaTeX notation and ensure formatting accuracy. You need to separate the mathematical formulas from the text. The formula part should be enclosed in `$···$' (only including mathematical symbols and expressions). The text part should be written as a regular paragraph. Please note that the current output only supports the MathJax/KaTeX rendering environment.# 使用 BlockType 枚举作为键"
INSTRUCTION = {
    BlockType.TITLE: "Please output the text content from the image.",
    BlockType.PLAIN_TEXT: f"Please output the text content from the image. {latex_expression}",
    BlockType.FIGURE_CAPTION: f"Please output the text content from the image.{latex_expression}",
    BlockType.TABLE: f"This image may be a table, if it is a table, please output the table in markdown format. {latex_expression}",
    BlockType.TABLE_CAPTION: f"Please output the text content from the image. {latex_expression}",
    BlockType.TABLE_FOOTNOTE: f"Please output the text content from the image. {latex_expression}",
    BlockType.ISOLATE_FORMULA:"Please transcribe the expression from the image into LaTeX format. You must use standard LaTeX notation and ensure formatting accuracy. The formula part should be enclosed in `$$···$$'(eg. including mathematical symbols and expressions). Please note that the current output only supports the MathJax/KaTeX rendering environment."
}
