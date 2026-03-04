// 重构后的 Controls.jsx
import './Controls.css';
import React from 'react';
import useFileSelector from '../hooks/useFileSelector';
import StatusMessage from './StatusMessage';
import { formatFileSize } from '../utils/fileUtils';
import ModelConfig from './ModelConfig.jsx';
const Controls = ({ onFileUpload, onFileProcess, onClearFile, file, status, fileType }) => {
  const { dragActive, fileInputRef, handleDrag, handleFileChange, openFileDialog } = useFileSelector();
  
  const getStatusMessage = () => {
    switch (status) {
      case 'uploading': return { message: '正在上传文件...', type: 'loading' };
      case 'processing': return { message: '文件上传成功，正在处理...', type: 'loading' };
      case 'success': return { 
        message: fileType === 'pdf' ? 'PDF处理完成' : '图片处理完成', 
        type: 'success' 
      };
      case 'error': return { message: '处理失败，请重试', type: 'error' };
      default: return null;
    }
  };
  
  const statusMessage = getStatusMessage();
  
  return (
    <div className="controls">
      <div className="upload-section">
        <div className={`upload-area ${dragActive ? 'dragover' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={(e) => {
            handleDrag(e);
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileChange({ target: { files: e.dataTransfer.files } }, onFileUpload);
            }
          }}
          onClick={openFileDialog}
        >
          <div className="upload-icon">
            {file && file.type.includes('pdf') ? '📄' : file && file.type.includes('image/') ? '🖼️' : '📄/🖼️'}
          </div>
          <div className="upload-text">点击选择文件或拖拽到此处</div>
          <div className="upload-hint">支持PDF和常见图片格式，最大50MB</div>
        </div>
        <ModelConfig className="model-config"/>

        <input
          type="file"
          id="file-input"
          accept=".pdf,.jpg,.jpeg,.png,.gif,.bmp"
          ref={fileInputRef}
          onChange={(e) => handleFileChange(e, onFileUpload)}
          style={{ display: 'none' }}
        />
        
      </div>
      

      {/* 其他UI部分 */}
      {file && (
        <div className="file-info">
          <h4>📁 文件信息</h4>
          <div className="file-details">
            <strong>文件名:</strong> <span>{file.name}</span>
            <strong>文件大小:</strong> <span>{formatFileSize(file.size)}</span>
            <strong>文件类型:</strong> <span>{file.type}</span>
          </div>
        </div>
      )}
      
      <div className="action-buttons">
        <button
          className="btn btn-primary"
          onClick={onFileProcess}
          disabled={!file || status === 'uploading' || status === 'processing'}
        >
          {file && file.type.includes('pdf') ? '处理PDF' : file && file.type.includes('image/') ? '处理图片' : '处理文件'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={onClearFile}
          disabled={!file}
        >
          清除文件
        </button>
      </div>
      
      {statusMessage && (
        <StatusMessage status={statusMessage.type} message={statusMessage.message} />
      )}
    </div>
  );
};

export default Controls;
