
# **TextSnap**

### Intelligent Document Parsing & Structured Conversion Tool

---

**📘 English**
**📕 [中文](README.md)**

---

## 📌 Overview

**TextSnap** is an intelligent document processing system designed to automatically convert **unstructured PDF and image documents** into **well-structured Markdown files**.

By integrating **Computer Vision (CV)** and **Natural Language Processing (NLP)** technologies, TextSnap provides an end-to-end pipeline covering document input, layout understanding, content recognition, and structured output generation.

---

## 📷 Demo Results

You can find several example outputs in the directory:

```
srcProject/output
```

<p align="center">
  <img src="srcProject/output/Realization of superhuman intelligence in microstrip filter/image.png" width="47%">
  <img src="srcProject/output/Realization of superhuman intelligence in microstrip filter/img.png" width="47%">
</p>


![](https://pic1.imgdb.cn/item/69465d7929a616e52860fc82.png)

![](https://pic1.imgdb.cn/item/69465dcd29a616e52860ff57.png)

![](https://pic1.imgdb.cn/item/69465de929a616e528610089.png)

![](https://pic1.imgdb.cn/item/69465e2329a616e528610245.png)

![](https://pic1.imgdb.cn/item/69465e5429a616e528610424.png)

---

## 🚀 Core Features

* **Multi-format Document Parsing**
  Supports PDF and common image formats (PNG, JPG, BMP, etc.)

* **Intelligent Layout Detection**
  Uses YOLO-based deep learning models to automatically detect:

  * Titles
  * Paragraphs
  * Tables
  * Images
  * Mathematical formulas

* **High-Accuracy OCR Recognition**
  Performs OCR on detected text regions to extract textual content

* **Reading Order Prediction**
  Analyzes spatial relationships between elements to generate a reading order aligned with human reading habits

* **Visualized Results**
  Provides visual overlays of detected layouts and reading order for easy inspection and debugging

* **Markdown Generation**
  Automatically produces structured Markdown documents while preserving the original hierarchy of the source file

---

## 🧠 Technical Architecture

* **Backend Language / Framework**: Python with `asyncio`
* **Image Processing**: PIL / Pillow
* **Deep Learning Models**

  * `YOLOv8` for document layout detection
  * Custom OCR model API for text recognition
  * `LayoutLMv3` for reading order prediction
* **Model Management**: Unified management via `ModelManager`
* **Data Processing**: Batch processing with concurrency control

---

## ⚙️ Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/THEysh/TestSnap.git
cd TextSnap
```

---

### 2️⃣ Create and Activate Virtual Environment

> Required Python version: **3.10.18**

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Download Pretrained Models (Required)

Run the following script to automatically download all required models:

```bash
python scripts/download_models.py
```

Models will be downloaded to:

```
data/models/
```

⚠️ If you encounter network issues when downloading from Hugging Face, **manual download is strongly recommended**:

* **International users**
  [https://huggingface.co/THEYSH/testsnap](https://huggingface.co/THEYSH/testsnap)
* **Users in China**
  [https://hf-mirror.com/THEYSH/testsnap](https://hf-mirror.com/THEYSH/testsnap)

After downloading, ensure the directory structure is exactly as follows:

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

### 5️⃣ Configure LLM / VLM API (`config.yaml`)

Locate **`config.yaml`** in the project root and configure your preferred model API.

#### Example: SiliconFlow

```yaml
gpt-api:
  api_key: sk-cxr******
  api_name: Siliconflow
  base_url: https://api.siliconflow.cn/v1
  model_name: Pro/Qwen/Qwen2.5-VL-7B-Instruct
```

#### Example: Google Gemini

```yaml
gpt-api:
  api_key: ["AIzaSyB***", "AIza***", "AIzaS***"]
  api_name: google
  base_url: https://generativelanguage.googleapis.com
  model_name: models/gemini-2.0-flash
```

---

## ▶️ Usage

### Run from Command Line (or Directly Run in IDE)

```bash
python srcProject/main_process_sequence.py
```

After execution, results can be found in:

```
srcProject/output/visualizations
```

⚠️ **Note**
When using images for prediction, avoid spaces in file names to prevent path parsing issues.

---

## 📁 Project Structure

```
TextSnap/
├── .idea/                      # IDE configuration
├── configs.yaml                # Global configuration
├── data/
│   └── models/                 # Model files
├── requirements.txt            # Python dependencies
├── scripts/
│   └── download_models.py      # Model download script
├── srcProject/
│   ├── config/                 # Configuration modules
│   ├── data_loaders/           # Data loaders
│   ├── main_process_sequence.py# Main processing pipeline
│   ├── models/                 # Model definitions
│   ├── output/                 # Output results
│   └── utlis/                  # Utility functions
└── tests/
    └── test_data/              # Test datasets
```

---

## ⚛️ React Frontend (Optional)

### 1️⃣ Verify Node Environment (≥ 18)

```bash
node -v
npm -v
```

If not installed, download the **LTS version** from:
👉 [https://nodejs.org](https://nodejs.org)

---

### 2️⃣ Start React Frontend

Open the following directory in VS Code:

```
flask_react/testsnap-react
```

Run:

```bash
cd flask_react/testsnap-react
npm install
npm run dev
```

Access the frontend at:

```
http://localhost:5173
```

✅ React environment is ready.
You can configure API settings in:

```
flask_react/testsnap-react/src/constants/apiConfig.js
```

![](https://pic1.imgdb.cn/item/69465b8329a616e52860e904.png)

---

### 3️⃣ Start Backend Server

* Open the project in **PyCharm**
* Navigate to the `flask_react` directory
* Right-click and run `server.py`

The backend server runs on:

```
127.0.0.1
```

![](https://pic1.imgdb.cn/item/69465cc829a616e52860f4af.png)

---

## 📮 Contact

If you have any questions or suggestions, feel free to contact me:

**WeChat: theysh_**

---
