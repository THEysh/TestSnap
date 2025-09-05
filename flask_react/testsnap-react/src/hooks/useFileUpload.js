import { useState } from 'react';
import { uploadFile } from '../services/apiService';

const useFileUpload = () => {
  const [status, setStatus] = useState('idle');
  const [uploadedFileInfo, setUploadedFileInfo] = useState(null);
  const [error, setError] = useState(null);

  const handleUpload = async (file) => {
    setStatus('uploading');
    setError(null);

    try {
      const isPdf = file.type.includes('pdf');
      const response = await uploadFile(file, isPdf);
      
      if (!response.success) {
        throw new Error(response.message || '文件上传失败');
      }
      
      setStatus('uploaded');
      setUploadedFileInfo(response.file_info);
      
      return { success: true, fileInfo: response.file_info, fileType: isPdf ? 'pdf' : 'image' };
    } catch (err) {
      setStatus('error');
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  return {
    status,
    uploadedFileInfo,
    error,
    handleUpload,
    reset: () => {
      setStatus('idle');
      setUploadedFileInfo(null);
      setError(null);
    }
  };
};

export default useFileUpload;