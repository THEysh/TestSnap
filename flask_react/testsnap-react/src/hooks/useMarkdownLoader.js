// src/hooks/useMarkdownLoader.js
import { useState } from 'react';
import { apiRequest } from '../services/apiService';
import { ENDPOINTS } from '../constants/apiConfig';
const useMarkdownLoader = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [content, setContent] = useState('');
  const [fileDir, setFileDir] = useState('');
  const [error, setError] = useState(null);

  const loadMarkdownFile = async (path) => {
    if (!path.trim()) {
      setError('请输入文件路径');
      return false;
    }

    try {
      setIsLoading(true);
      setError(null);

      const response = await apiRequest(ENDPOINTS.MARKDOWN, {
        method: 'POST',
        body: JSON.stringify({ path })
      });

      if (response.success) {
        setFileDir(response.file_dir);
        setContent(response.content);
        return true;
      } else {
        setError(`加载失败: ${response.error}`);
        return false;
      }
    } catch (err) {
      console.error('请求失败:', err);
      setError('网络请求失败，请检查服务器是否启动');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    isLoading,
    content,
    fileDir,
    error,
    loadMarkdownFile,
    reset: () => {
      setContent('');
      setFileDir('');
      setError(null);
    }
  };
};

export default useMarkdownLoader;