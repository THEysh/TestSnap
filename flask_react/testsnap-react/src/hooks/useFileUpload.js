import { useState } from 'react';
import { uploadFile } from '../services/apiService';

const useFileUpload = () => {
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [uploadedFileInfo, setUploadedFileInfo] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (file) => {
    setStatus('uploading');
    setProgress(0);
    setError(null);

    try {
      const isPdf = file.type.includes('pdf');
      
      // 创建带进度监控的上传请求
      const response = await uploadFile(file, isPdf);
      
      if (!response.success) {
        throw new Error(response.message || '文件上传失败');
      }
      
      setStatus('uploaded');
      setUploadedFileInfo(response.file_info);
      setProgress(100);
      
      return { success: true, fileInfo: response.file_info, fileType: isPdf ? 'pdf' : 'image' };
    } catch (err) {
      setStatus('error');
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  return {
    status,
    progress,
    uploadedFileInfo,
    error,
    handleUpload,
    reset: () => {
      setStatus('idle');
      setProgress(0);
      setUploadedFileInfo(null);
      setError(null);
    }
  };
};

export default useFileUpload;