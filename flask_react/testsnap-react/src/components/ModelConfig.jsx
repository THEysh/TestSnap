import React, { useState } from "react";
import { ENDPOINTS } from "../constants/apiConfig"; // 导入 API 端点
import {
  BookOpen,
  Key,
  Globe,
  FileText
} from "lucide-react"; // 引入图标
import "./ModelConfig.css";

const SUPPORTED_OCR_MODELS = [
  "Qwen/Qwen3-VL-30B-A3B-Instruct",
  "Qwen/Qwen3-VL-8B-Instruct",
  "Qwen/Qwen3-VL-32B-Instruct",
  "Qwen/Qwen2.5-VL-72B-Instruct",
  "Qwen/Qwen2.5-VL-32B-Instruct",
  "Pro/Qwen/Qwen2.5-VL-7B-Instruct",
  "Qwen/Qwen2-VL-72B-Instruct",
  "deepseek-ai/deepseek-vl2",
  "deepseek-ai/DeepSeek-OCR",
  "zai-org/GLM-4.5V",
  "zai-org/GLM-4.6V"
];

const ModelConfig = () => {
  // read_model 下拉框的状态
  const [readModel, setReadModel] = useState("Xy_Cut");
  // API 配置输入框的状态
  const [config, setConfig] = useState({
    apiKey: "",
    baseUrl: "https://api.siliconflow.cn/v1",
    modelName: SUPPORTED_OCR_MODELS[0] || ""
  });
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);
  // 处理 read_model 下拉菜单的变化
  const handleReadModelChange = (e) => {
    setReadModel(e.target.value);
  };
  // 状态消息的HTML内容
  const createMarkup = () => {
    return { __html: statusMessage };
  };

  // 处理文本输入框的变化
  const handleConfigChange = (e) => {
    const { name, value } = e.target;
    setConfig((prev) => ({
      ...prev,
      [name]: value,
    }));
  };
  
  // 封装API调用逻辑
  const handleUpdateConfig = async () => {
    setIsLoading(true);
    setStatusMessage("");
    setIsSuccess(false);

    // 根据选中的模型类型构建请求体
    const payload = {
      read_model: readModel
    };

    const apiKey = (config.apiKey || "").trim();
    const baseUrl = (config.baseUrl || "").trim();
    const modelName = (config.modelName || "").trim();
    if (!apiKey || !baseUrl || !modelName) {
      setStatusMessage("请填写 Base URL / API Key，并选择 Model Name。");
      setIsSuccess(false);
      setIsLoading(false);
      return;
    }

    payload.ocr_api_model = {
      api_name: "siliconflow",
      api_key: apiKey,
      base_url: baseUrl,
      model_name: modelName
    };

    try {
      const response = await fetch(ENDPOINTS.MODEL_CONFIG, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      const data = await response.json();


      if (response.ok) {
        // 构建详细的状态信息
        let detailsMessage = "";
        if (data.details) {
          for (const [key, value] of Object.entries(data.details)) {
            const modelInfo = value.model_name || "";
            const apiInfo = value.api_name ? ` (${value.api_name})` : "";
            const statusText = value.updated ? "✅ 更新成功" : "❌ 更新失败";
            detailsMessage += `${key}: ${modelInfo}${apiInfo} -> ${statusText}<br/>`;
          }
        }
  
        setStatusMessage(`${data.message || "配置更新成功！"}<br/>${detailsMessage}`);
        setIsSuccess(true);
      } else {
        setStatusMessage(data.message || "配置更新失败，请重试。");
        setIsSuccess(false);
      }
    } catch (error) {
      console.error("更新模型配置时发生错误:", error);
      setStatusMessage(`请求失败: ${error.message}`);
      setIsSuccess(false);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="model-config">
      <h3>模型配置</h3>
      <div className="controls">
        {/* 下拉框1：read_model */}
        <label className="form-row">
          <BookOpen className="icon" />
          <span>选择阅读模型：</span>
          <select value={readModel} onChange={handleReadModelChange}>
            <option value="Xy_Cut">Xy_Cut</option>
            <option value="LayoutLMv3">LayoutLMv3</option>
          </select>
        </label>

        <label className="form-row">
          <Key className="icon" />
          <span>API Key：</span>
          <input
            type="text"
            name="apiKey"
            value={config.apiKey}
            onChange={handleConfigChange}
            placeholder="请输入 API Key"
          />
        </label>

        <label className="form-row">
          <Globe className="icon" />
          <span>Base URL：</span>
          <input
            type="text"
            name="baseUrl"
            value={config.baseUrl}
            onChange={handleConfigChange}
            placeholder="请输入 Base URL"
          />
        </label>

        <label className="form-row">
          <FileText className="icon" />
          <span>Model Name：</span>
          <select name="modelName" value={config.modelName} onChange={handleConfigChange}>
            {SUPPORTED_OCR_MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
      </div>

      {/* 更新配置按钮 */}
      <button
        className="btn-primary"
        onClick={handleUpdateConfig}
        disabled={isLoading}
      >
        {isLoading ? "更新中..." : "更新配置"}
      </button>

      {statusMessage && (
        <p
        style={{
          color: isSuccess ? "green" : "red",
          marginTop: "10px",
          fontWeight: "bold",
          textAlign: "center"
        }}
        // 将这里改为使用 dangerouslySetInnerHTML
        dangerouslySetInnerHTML={createMarkup()}
      >
        {/* 当使用 dangerouslySetInnerHTML 时，p 标签内部不能再有子元素 */}
      </p>
    )}
  </div>
  );
};

export default ModelConfig;
