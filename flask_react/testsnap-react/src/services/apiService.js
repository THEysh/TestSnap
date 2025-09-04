import { ENDPOINTS } from '../constants/apiConfig';

// 通用请求函数
export const apiRequest = async (endpoint, options = {}) => {
  try {
    const response = await fetch(endpoint, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      throw new Error(`HTTP错误 ${response.status}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    return await response.text();
  } catch (error) {
    console.error('API请求错误:', error);
    throw error;
  }
};

// 文件上传函数
export const uploadFile = (file, isPdf) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    
    xhr.open('POST', isPdf ? ENDPOINTS.PDF_UPLOAD : ENDPOINTS.IMAGE_UPLOAD);
    
    xhr.onload = () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(`上传失败: ${xhr.status}`));
      }
    };
    
    xhr.onerror = () => reject(new Error('网络错误'));
    
    xhr.send(formData);
  });
};

// 获取任务进度
export const getTaskProgress = (taskId) => {
  return apiRequest(`${ENDPOINTS.TASK_PROGRESS}${taskId}`);
};

// 处理文件
export const processFile = (filename, isPdf) => {
  return apiRequest(isPdf ? ENDPOINTS.PDF_PROCESS : ENDPOINTS.IMAGE_PROCESS, {
    method: 'POST',
    body: JSON.stringify({ filename })
  });
};