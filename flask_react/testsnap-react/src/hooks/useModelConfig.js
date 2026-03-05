import { useState, useEffect } from 'react';

// 更新模型配置的API调用
// 注意：在实际应用中，这部分代码应该在单独的服务文件中
const modelConfigService = {
  updateModelConfig: async (configData) => {
    try {
      // 假设这是后端服务的URL
      // 实际使用时需要根据你的后端配置进行修改
      const API_BASE_URL = '/api';
      const response = await fetch(`${API_BASE_URL}/update/model_config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(configData)
      });

      if (!response.ok) {
        throw new Error(`HTTP错误 ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('更新模型配置失败:', error);
      throw error;
    }
  }
};


const useModelConfig = () => {
  // 定义可用的模型选项
  const [readModels] = useState([
    { api_name: 'read_model', model_name: 'Xy_Cut' },
    { api_name: 'read_model', model_name: 'LayoutLMv3' },
  ]);
  const [ocrApiModels] = useState([
    // Siliconflow 支持的模型
    { api_name: 'siliconflow', model_name: 'Pro/Qwen/Qwen2.5-VL-7B-Instruct' },
    { api_name: 'siliconflow', model_name: 'Qwen/Qwen2.5-VL-32B-Instruct' },
    { api_name: 'siliconflow', model_name: 'Qwen/Qwen2.5-VL-72B-Instruct' },
    { api_name: 'siliconflow', model_name: 'deepseek-ai/deepseek-vl2' },
    // Google 支持的模型
    { api_name: 'google', model_name: 'models/gemma-3-27b-it' },
    { api_name: 'google', model_name: 'models/gemini-2.0-flash' },
    { api_name: 'google', model_name: 'models/gemini-2.5-flash' }
  ]);

  // 状态管理：保存当前选中的模型
  const [selectedReadModel, setSelectedReadModel] = useState(readModels[0].model_name);
  const [selectedOcrApiModel, setSelectedOcrApiModel] = useState(ocrApiModels[0]);

  // 状态管理：用于处理 API 请求的加载和错误状态
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * 将当前选中的模型配置发送到后端进行更新。
   */
  const handleUpdateConfig = async () => {
    setLoading(true);
    setError(null);
    try {
      const configData = {
        read_model: selectedReadModel,
        ocr_api_model: selectedOcrApiModel
      };
      await modelConfigService.updateModelConfig(configData);
      // 如果需要，可以在这里处理更新成功后的逻辑，例如显示一个成功消息
    } catch (err) {
      setError('更新模型配置失败，请检查网络或后端服务。');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // 确保当可用模型列表更新时，选中的模型也在其中
  useEffect(() => {
    if (!readModels.some(m => m.model_name === selectedReadModel)) {
      setSelectedReadModel(readModels[0].model_name);
    }
    if (!ocrApiModels.some(m => m.model_name === selectedOcrApiModel.model_name)) {
      setSelectedOcrApiModel(ocrApiModels[0]);
    }
  }, [readModels, ocrApiModels, selectedReadModel, selectedOcrApiModel]);

  return {
    readModels,
    ocrApiModels,
    selectedReadModel,
    setSelectedReadModel,
    selectedOcrApiModel,
    setSelectedOcrApiModel,
    handleUpdateConfig,
    loading,
    error,
  };
};

export default useModelConfig;
