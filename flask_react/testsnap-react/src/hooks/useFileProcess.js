import { useState, useEffect } from 'react';
import { processFile, getTaskProgress } from '../services/apiService';
import { ENDPOINTS } from '../constants/apiConfig';

const useFileProcess = () => {
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [processedFileUrl, setProcessedFileUrl] = useState(null);
  const [downloadLink, setDownloadLink] = useState(null);
  const [autoLoadMarkdownPath, setAutoLoadMarkdownPath] = useState(null);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);

  const process = async (filename, isPdf) => {
    setStatus('processing');
    setProgress(0);
    setProgressMessage('');
    setError(null);
    
    try {
      const result = await processFile(filename, isPdf);
      
      if (!result.success || !result.task_id) {
        throw new Error(result.error || '启动处理失败');
      }
      
      const { task_id } = result;
      setTaskId(task_id);
      
      return { success: true, task_id };
    } catch (err) {
      setStatus('error');
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  // 轮询任务进度
  useEffect(() => {
    let checkProgress = null;
    let timeout = null;
    
    if (taskId && status === 'processing') {
      // 启动轮询
      checkProgress = setInterval(async () => {
        try {
          const progressData = await getTaskProgress(taskId);
          
          if (!progressData.success) {
            throw new Error(progressData.error || '获取进度失败');
          }
          
          setProgress(progressData.progress || 0);
          setProgressMessage(progressData.message || '处理中...');
          
          if (progressData.status === 'completed') {
            clearInterval(checkProgress);
            checkProgress = null;
            
            if (!progressData.result || !progressData.result.success) {
              throw new Error(progressData.result?.error || '处理结果无效');
            }
            
            const result = progressData.result;
            const processedPath = result.processed_file.replace(/\\/g, '/');
            const processed_md_path = result.md_path.replace(/\\/g, '/');
            
            setProcessedFileUrl(`${ENDPOINTS.FILES}${encodeURIComponent(processedPath)}`);
            setDownloadLink(processedPath.split('/').pop());
            setAutoLoadMarkdownPath(processed_md_path);
            setStatus('completed');
            setProgress(100);
            setProgressMessage('处理完成');
          } else if (progressData.status === 'failed') {
            clearInterval(checkProgress);
            checkProgress = null;
            
            setStatus('error');
            setError(progressData.message || '处理失败');
            setProgress(0);
          }
        } catch (err) {
          console.error('轮询进度时出错:', err);
        }
      }, 1000);

      // 设置超时
      timeout = setTimeout(() => {
        clearInterval(checkProgress);
        setStatus('error');
        setError('处理超时');
        setProgress(0);
      }, 5 * 60 * 1000); // 5分钟
    }

    return () => {
      if (checkProgress) clearInterval(checkProgress);
      if (timeout) clearTimeout(timeout);
    };
  }, [taskId, status]);

  return {
    status,
    progress,
    progressMessage,
    processedFileUrl,
    downloadLink,
    autoLoadMarkdownPath,
    error,
    process,
    reset: () => {
      setStatus('idle');
      setProgress(0);
      setProgressMessage('');
      setProcessedFileUrl(null);
      setDownloadLink(null);
      setAutoLoadMarkdownPath(null);
      setError(null);
      setTaskId(null);
    }
  };
};

export default useFileProcess;