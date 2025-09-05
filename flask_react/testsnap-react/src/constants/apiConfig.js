// API配置文件
export const API_BASE_URL = 'http://192.168.1.128:7861/api';
export const ENDPOINTS = {
  PDF_UPLOAD: `${API_BASE_URL}/pdf/upload`,
  PDF_PROCESS: `${API_BASE_URL}/pdf/process`,
  IMAGE_UPLOAD: `${API_BASE_URL}/image/upload`,
  IMAGE_PROCESS: `${API_BASE_URL}/image/process`,
  TASK_PROGRESS: `${API_BASE_URL}/task/progress/`,
  FILES: `${API_BASE_URL}/files/`,
  MARKDOWN: `${API_BASE_URL}/markdown`
};