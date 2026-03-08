const ENV_API_BASE_URL = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : '';
const ENV_API_PORT = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_PORT : '';
const DEFAULT_API_PORT = '7861';

const resolveApiBaseUrl = () => {
  if (ENV_API_BASE_URL) {
    const raw = String(ENV_API_BASE_URL).replace(/\/+$/, '');
    if (/\/api$/i.test(raw)) return raw;
    return `${raw}/api`;
  }
  if (typeof window === 'undefined') return `http://127.0.0.1:${DEFAULT_API_PORT}/api`;
  const protocol = window.location.protocol || 'http:';
  const host = window.location.hostname || '127.0.0.1';
  const port = ENV_API_PORT || DEFAULT_API_PORT;
  return `${protocol}//${host}:${port}/api`;
};

export const API_BASE_URL = resolveApiBaseUrl();
export const API_ROOT_URL = API_BASE_URL.replace(/\/api\/?$/, '');
export const ENDPOINTS = {
  PDF_UPLOAD: `${API_BASE_URL}/pdf/upload`,
  PDF_PROCESS: `${API_BASE_URL}/pdf/process`,
  IMAGE_UPLOAD: `${API_BASE_URL}/image/upload`,
  IMAGE_PROCESS: `${API_BASE_URL}/image/process`,
  TASK_PROGRESS: `${API_BASE_URL}/task/progress/`,
  OCR_STREAM: `${API_BASE_URL}/task/ocr/stream/`,
  FILES: `${API_BASE_URL}/files/`,
  MARKDOWN: `${API_BASE_URL}/markdown`,
  MODEL_CONFIG: `${API_BASE_URL}/update/model_config`
};
