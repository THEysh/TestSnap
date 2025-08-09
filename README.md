# TextSnap: 智能文档解析与结构化转换工具

## 项目概述
TextSnap 是一个功能强大的文档智能处理系统，专注于将非结构化的 PDF 和图片文档转换为结构化的 Markdown 格式。该项目结合了先进的计算机视觉和自然语言处理技术，实现了从文档输入到结构化输出的完整流程。

## 核心功能
- **多格式文档解析**：支持 PDF 和各种图片格式（PNG、JPG、BMP 等）的导入与解析
- **智能布局检测**：使用 YOLO 深度学习模型自动识别文档中的标题、正文、表格、图片、公式等元素
- **高精度 OCR 识别**：对检测到的文本区域进行光学字符识别，提取文本内容
- **阅读顺序预测**：分析文档元素间的空间关系，确定符合人类阅读习惯的内容顺序
- **可视化展示**：将检测结果和阅读顺序以图形方式直观展示，便于验证和调整
- **Markdown 生成**：根据识别结果自动生成结构化的 Markdown 文档，保留原始文档的层次结构

## 技术架构
- **后端框架**：Python 异步编程 (asyncio)
- **图像处理**：PIL/Pillow
- **深度学习模型**：
  - YOLOv8 用于文档布局检测
  - 自定义 OCR 模型api用于文本识别
  - LayoutLMv3 用于阅读顺序预测
- **模型管理**：通过 ModelManager 统一管理各种模型
- **数据处理**：批量处理机制和并发控制

### 安装步骤
1. 克隆项目仓库
   ```bash
   git clone https://github.com/THEysh/TestSnap.git
   cd TextSnap
   ```

2. 创建并激活虚拟环境
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. 安装依赖包
   ```bash
   pip install -r requirements.txt
   ```

4. 下载预训练模型
   ```bash
   python scripts/download_models.py
   ```
5.在根目录中找到`config.yaml`写入修改VML的配置，当前支持硅基流动api
```markdown
gpt-api:
  api_key: sk-cxr******
  api_name: Siliconflow
  base_url: https://api.siliconflow.cn/v1
  model_name: Pro/Qwen/Qwen2.5-VL-7B-Instruct
```
## 使用方法
### 命令行运行或者直接run
```bash
python srcProject/main_process_sequence.py
```
随后在目录`srcProject/output/visualizations`, 查看结果

## 项目结构
```
TextSnap/
├── .idea/                  # IDE配置文件
├── .pytest_cache/          # 测试缓存
├── configs.yaml            # 配置文件
├── data/                   # 数据目录
│   └── models/             # 模型文件
├── requirements.txt        # 依赖包列表
├── scripts/                # 脚本文件
│   ├── download_models.py  # 下载模型脚本
│   ├── prepare_environment.sh # 环境准备脚本
│   └── run_cli.py          # 命令行入口
├── srcProject/             # 源代码
│   ├── config/             # 配置模块
│   ├── data_loaders/       # 数据加载器
│   ├── main_process_sequence.py # 主处理流程
│   ├── models/             # 模型定义
│   ├── output/             # 输出目录
│   └── utlis/              # 工具函数
└── tests/                  # 测试代码
    └── test_data/          # 测试数据
```

## 贡献指南
1.  Fork 项目仓库
2.  创建特性分支 (`git checkout -b feature/AmazingFeature`)
3.  提交更改 (`git commit -m 'Add some AmazingFeature'`)
4.  推送到分支 (`git push origin feature/AmazingFeature`)
5.  开启 Pull Request

## 联系方式
如有问题或建议，请联系我微信: theysh_