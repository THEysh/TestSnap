// 创建 src/utils/fileUtils.js
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

export const validateFile = (file) => {
  // 文件类型检查
  if (!file.type.includes('pdf') && !file.type.includes('image/')) {
    return { valid: false, message: '请选择PDF或图片文件' };
  }
  // 文件大小检查（50MB限制）
  if (file.size > 50 * 1024 * 1024) {
    return { valid: false, message: '请选择小于50MB的文件' };
  }
  return { valid: true };
};