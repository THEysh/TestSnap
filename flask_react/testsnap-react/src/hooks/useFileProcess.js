import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { processFile, getTaskProgress } from '../services/apiService';
import { ENDPOINTS } from '../constants/apiConfig';

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function readPersisted(key) {
  if (typeof window === 'undefined') return null;
  if (!key) return null;
  const raw = window.localStorage.getItem(key);
  const data = safeJsonParse(raw, null);
  if (!data || typeof data !== 'object') return null;
  const ts = Number(data.ts || 0);
  if (!ts) return null;
  if (Date.now() - ts > 24 * 60 * 60 * 1000) return null;
  return data;
}

const useFileProcess = ({ persistKey } = {}) => {
  const persisted = useMemo(() => readPersisted(persistKey), [persistKey]);

  const [status, setStatus] = useState(() => persisted?.status || 'idle');
  const [progress, setProgress] = useState(() => Number(persisted?.progress || 0));
  const [progressMessage, setProgressMessage] = useState(() => persisted?.progressMessage || '');
  const [processedFileUrl, setProcessedFileUrl] = useState(() => persisted?.processedFileUrl || null);
  const [downloadLink, setDownloadLink] = useState(() => persisted?.downloadLink || null);
  const [autoLoadMarkdownPath, setAutoLoadMarkdownPath] = useState(() => persisted?.autoLoadMarkdownPath || null);
  const [error, setError] = useState(() => persisted?.error || null);
  const [taskId, setTaskId] = useState(() => persisted?.taskId || null);
  const [streamContent, setStreamContent] = useState(() => persisted?.streamContent || '');

  const persistTimerRef = useRef(null);

  const writePersisted = useCallback((data) => {
    if (typeof window === 'undefined') return;
    if (!persistKey) return;
    if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    persistTimerRef.current = setTimeout(() => {
      try {
        window.localStorage.setItem(persistKey, JSON.stringify({ ...data, ts: Date.now() }));
      } catch {
        void 0;
      } finally {
        persistTimerRef.current = null;
      }
    }, 120);
  }, [persistKey]);

  const clearPersisted = useCallback(() => {
    if (typeof window === 'undefined') return;
    if (!persistKey) return;
    try {
      window.localStorage.removeItem(persistKey);
    } catch {
      void 0;
    }
  }, [persistKey]);

  const process = async (filename, isPdf) => {
    setStatus('processing');
    setProgress(0);
    setProgressMessage('');
    setError(null);
    setStreamContent('');
    
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

  useEffect(() => {
    if (!persistKey) return;
    writePersisted({
      status,
      progress,
      progressMessage,
      processedFileUrl,
      downloadLink,
      autoLoadMarkdownPath,
      error,
      taskId,
      streamContent
    });
    return () => void 0;
  }, [
    persistKey,
    writePersisted,
    status,
    progress,
    progressMessage,
    processedFileUrl,
    downloadLink,
    autoLoadMarkdownPath,
    error,
    taskId,
    streamContent
  ]);

  useEffect(() => {
    return () => {
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    };
  }, []);

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
            clearInterval(checkProgress);
            checkProgress = null;
            setStatus('error');
            setError(progressData.error || '获取进度失败');
            setProgress(0);
            return;
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
          if (checkProgress) {
            clearInterval(checkProgress);
            checkProgress = null;
          }
          setStatus('error');
          setError(err.message || '获取进度失败');
          setProgress(0);
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

  useEffect(() => {
    if (!taskId || status !== 'processing') return;
    const controller = new AbortController();
    const run = async () => {
      try {
        const res = await fetch(`${ENDPOINTS.OCR_STREAM}${taskId}`, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          signal: controller.signal
        });
        if (!res.ok || !res.body) {
          setStatus('error');
          setError(`OCR流式通道异常: ${res.status}`);
          return;
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          while (true) {
            const idx = buffer.indexOf('\n\n');
            if (idx === -1) break;
            const event = buffer.slice(0, idx);
            buffer = buffer.slice(idx + 2);
            const lines = event.split('\n');
            let eventType = 'message';
            const dataLines = [];
            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                dataLines.push(line.slice(5).trimStart());
              }
            }
            const dataStr = dataLines.join('\n');
            if (eventType === 'done' || dataStr === '[DONE]') {
              return;
            }
            if (!dataStr) continue;
            try {
              const payload = JSON.parse(dataStr);
              if (payload?.type === 'append' && payload.content) {
                setStreamContent(prev => prev + payload.content);
              } else if (payload?.type === 'error') {
                setStatus('error');
                setError(String(payload.content || '处理失败'));
                setProgress(0);
                return;
              }
            } catch {
              continue;
            }
          }
        }
      } catch {
        return;
      }
    };
    run();
    return () => controller.abort();
  }, [taskId, status]);

  return {
    status,
    progress,
    progressMessage,
    processedFileUrl,
    downloadLink,
    autoLoadMarkdownPath,
    streamContent,
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
      setStreamContent('');
      clearPersisted();
    }
  };
};

export default useFileProcess;
