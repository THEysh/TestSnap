import React, { useState } from "react";
import { ENDPOINTS } from "../constants/apiConfig"; // 导入 API 端点
import {
  BookOpen,
  Cpu,
  Key,
  Globe,
  FileText
} from "lucide-react"; // 引入图标
import "./ModelConfig.css";

const ModelConfig = () => {
  // read_model 下拉框的状态
  const [readModel, setReadModel] = useState("Xy_Cut");
  // ocr_api_model 下拉框的状态
  const [ocrApiModel, setOcrApiModel] = useState("");
  // API 配置输入框的状态
  const [config, setConfig] = useState({
    apiKey: "",
    apiName: "",
    baseUrl: "",
    modelName: ""
  });
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  // 处理 read_model 下拉菜单的变化
  const handleReadModelChange = (e) => {
    setReadModel(e.target.value);
  };

  // 处理 ocr_api_model 下拉菜单的变化
  const handleOcrApiModelChange = (e) => {
    setOcrApiModel(e.target.value);
    // 当选择新的API时，重置输入框内容
    setConfig({
      apiKey: "",
      apiName: "",
      baseUrl: "",
      modelName: ""
    });
  };

  // 处理文本输入框的变化
  const handleConfigChange = (e) => {
    const { name, value } = e.target;
    setConfig({
      ...config,
      [name]: value
    });
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

    // 如果选择了 ocr_api_model，则添加其配置
    if (ocrApiModel) {
      payload.ocr_api_model = {
        api_name: ocrApiModel,
        api_key: config.apiKey,
        base_url: config.baseUrl,
        model_name: config.modelName
      };
    }

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
        setStatusMessage(data.message || "配置更新成功！");
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
          <BookOpen size={18} className="icon" />
          <span>选择阅读模型：</span>
          <select value={readModel} onChange={handleReadModelChange}>
            <option value="Xy_Cut">Xy_Cut</option>
            <option value="LayoutLMv3">LayoutLMv3</option>
          </select>
        </label>

        {/* 下拉框2：ocr_api_model */}
        <label className="form-row">
          <Cpu size={18} className="icon" />
          <span>选择 API 模型：</span>
          <select value={ocrApiModel} onChange={handleOcrApiModelChange}>
            <option value="">--不使用--</option>
            <option value="Siliconflow">Siliconflow</option>
            <option value="google">Google</option>
          </select>
        </label>

        {/* 当选择了API模型时，才显示输入框 */}
        {ocrApiModel && (
          <>
            <label className="form-row">
              <Key size={18} className="icon" />
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
              <Globe size={18} className="icon" />
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
              <FileText size={18} className="icon" />
              <span>Model Name：</span>
              <input
                type="text"
                name="modelName"
                value={config.modelName}
                onChange={handleConfigChange}
                placeholder="请输入 Model Name"
              />
            </label>
          </>
        )}
      </div>

      {/* 更新配置按钮 */}
      <button
        className="btn-primary"
        onClick={handleUpdateConfig}
        disabled={isLoading}
      >
        {isLoading ? "更新中..." : "更新配置"}
      </button>

      {/* 状态消息显示 */}
      {statusMessage && (
        <p
          style={{
            color: isSuccess ? "green" : "red",
            marginTop: "10px",
            textAlign: "center"
          }}
        >
          {statusMessage}
        </p>
      )}
    </div>
  );
};

export default ModelConfig;
