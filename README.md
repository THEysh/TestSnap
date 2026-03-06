
# **TextSnap**

### 智能文档解析与结构化转换工具

---

**📘 [English](README_EN.md)**
**📕 [中文](README.md)**

---

## 📌 项目概述

**TextSnap** 是一个面向复杂文档场景的智能解析系统，致力于将 **非结构化 PDF / 图片文档** 自动转换为 **结构化 Markdown**。
项目融合了 **计算机视觉（CV）** 与 **自然语言处理（NLP）** 技术，完整覆盖从文档输入、版式理解、内容识别到结构化输出的全流程。

---

## 📷 效果示例

在目录 **`srcProject/output`** 下可查看部分解析与可视化效果示例：

<p align="center">
  <img src="srcProject/output/Realization of superhuman intelligence in microstrip filter/image.png" width="47%">
  <img src="srcProject/output/Realization of superhuman intelligence in microstrip filter/img.png" width="47%">
</p>

前端效果示例：

![](https://pic1.imgdb.cn/item/69465d7929a616e52860fc82.png)

![](https://pic1.imgdb.cn/item/69465dcd29a616e52860ff57.png)

![](https://pic1.imgdb.cn/item/69465de929a616e528610089.png)

![](https://pic1.imgdb.cn/item/69465e2329a616e528610245.png)

![](https://pic1.imgdb.cn/item/69465e5429a616e528610424.png)

---

## 🚀 核心功能

* **多格式文档解析**
  支持 PDF 及常见图片格式（PNG / JPG / BMP 等）

* **智能布局检测**
  基于 YOLO 深度学习模型，自动识别：

  * 标题
  * 正文
  * 表格
  * 图片
  * 数学公式等结构元素

* **高精度 OCR 识别**
  对文本区域进行 OCR，精准提取文字内容

* **阅读顺序预测**
  利用布局与空间关系，预测符合人类阅读习惯的内容顺序

* **解析结果可视化**
  将检测框与阅读顺序进行图形化展示，便于验证与调试

* **Markdown 自动生成**
  输出结构清晰、层级合理的 Markdown 文档，最大程度还原原文档结构

---

## 🧠 技术架构

* **后端语言 / 框架**：Python（`asyncio` 异步编程）
* **图像处理**：PIL / Pillow
* **深度学习模型**

  * `YOLOv8`：文档版式检测
  * 自定义 OCR 模型 API：文本识别
  * `LayoutLMv3`：阅读顺序预测
* **模型管理**：统一由 `ModelManager` 管理
* **数据处理机制**：支持批量处理与并发控制

---

## ⚙️ 安装步骤

### 1️⃣ 克隆项目

```bash
git clone https://github.com/THEysh/TestSnap.git
cd TextSnap
```

---

### 2️⃣ 创建并激活虚拟环境

> Python 版本要求：**3.10.18**

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

---

### 3️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

---

### 4️⃣ 下载预训练模型（重要）

运行自动下载脚本：

```bash
python scripts/download_models.py
```

模型默认下载并存放至：

```
data/models/
```

⚠️ 若从 Hugging Face 直接下载遇到网络问题，**强烈建议手动下载**：

* **国外用户**
  [https://huggingface.co/THEYSH/testsnap](https://huggingface.co/THEYSH/testsnap)
* **国内用户**
  [https://hf-mirror.com/THEYSH/testsnap](https://hf-mirror.com/THEYSH/testsnap)

下载完成后，请确认模型目录结构如下（必须一致）：

```
├── data/
│   └── models/
│       ├── relation/
│       │   ├── config.json
│       │   └── model.safetensors
│       └── structure/
│           └── doclayout_yolo_docstructbench_imgsz1280_2501.pt
```

---

### 5️⃣ 配置大模型 API（`config.yaml`）

在项目根目录找到 **`configs.yaml`**，填写 VLM / LLM 相关配置。
当前项目已调整为 **仅支持硅基流动（SiliconFlow）** 作为 OCR/Chat 的 API 提供方。

#### 示例一：硅基流动（SiliconFlow）

```yaml
gpt-api:
  api_key: sk-cxr******
  api_name: Siliconflow
  base_url: https://api.siliconflow.cn/v1
  model_name: Pro/Qwen/Qwen2.5-VL-7B-Instruct

chat-api:
  api_key: sk-cxr******
  api_name: Siliconflow
  base_url: https://api.siliconflow.cn/v1
  model_name: Qwen/Qwen2.5-VL-32B-Instruct
```

模型名称建议从前端项目中的 [支持模型.md](file:///f:/ysh_loc_office/projects/practice/TextSnap/flask_react/testsnap-react/支持模型.md) 选择。

---

## ▶️ 使用方法

### 命令行运行（或直接 Run）

```bash
python srcProject/main_process_sequence.py
```

运行完成后，可在以下目录查看解析结果与可视化输出：

```
srcProject/output/visualizations
```

⚠️ **注意事项**
使用图片（img）预测时，**文件名请尽量不要包含空格**，以避免路径解析问题。

---

## 📁 项目结构

```
TextSnap/
├── .idea/                      # IDE 配置
├── configs.yaml                # 全局配置文件
├── data/                       # 数据目录
│   └── models/                 # 模型文件
├── requirements.txt            # Python 依赖
├── scripts/
│   └── download_models.py      # 模型下载脚本
├── srcProject/
│   ├── config/                 # 配置模块
│   ├── data_loaders/           # 数据加载
│   ├── main_process_sequence.py# 主处理流程
│   ├── models/                 # 模型定义
│   ├── output/                 # 输出结果
│   └── utlis/                  # 工具函数
└── tests/
    └── test_data/              # 测试数据
```

---

## ⚛️ React 前端启动（可选）

### 1️⃣ 确认 Node 环境（推荐 ≥ 20.19 或 ≥ 22.12）

```bash
node -v
npm -v
```

未安装请前往官网（选择 LTS）：
👉 [https://nodejs.org](https://nodejs.org)

---

### 2️⃣ 启动 React 前端

使用 VS Code 打开目录：

```
flask_react/testsnap-react
```

执行：

```bash
cd flask_react/testsnap-react
npm install
npm run dev
```

访问地址：

```
http://localhost:5173
```

✅ 前端启动完成
可在以下文件中配置 API：

```
flask_react/testsnap-react/src/constants/apiConfig.js
```

![](https://pic1.imgdb.cn/item/69465b8329a616e52860e904.png)

模型配置说明：
- 前端页面「模型配置」已简化为：Base URL / API Key / Model Name（下拉选择）
- API 提供方固定为 SiliconFlow，不再支持 Google

---

### 3️⃣ 启动后端服务

* 使用 **PyCharm** 打开项目
* 进入 `flask_react` 目录
* 右键运行 `server.py`

后端默认地址：

```
127.0.0.1
```

![](https://pic1.imgdb.cn/item/69465cc829a616e52860f4af.png)

---

## 📮 联系方式

如有问题或建议，欢迎联系：

**微信：theysh_**

---

