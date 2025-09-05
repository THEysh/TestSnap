import './Controls.css'; // 对应样式文件
import React, { useState, useRef } from 'react';

const Controls = ({ onFileUpload, onFileProcess, onClearFile, file, status, progress, progressMessage, fileType }) => {
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef(null);
    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            const fileType = selectedFile.type;
            // 检查是否为PDF或图片文件
            if (!fileType.includes('pdf') && !fileType.includes('image/')) {
                alert('请选择PDF或图片文件');
                return;
            }
            // 检查文件大小（50MB限制）
            if (selectedFile.size > 50 * 1024 * 1024) {
                alert('请选择小于50MB的文件');
                return;
            }
            onFileUpload(selectedFile);
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragover' || e.type === 'dragenter') {
            setDragActive(true);
        } else if (e.type === 'dragleave' || e.type === 'drop') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileChange({ target: { files: e.dataTransfer.files } });
        }
    };

    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    };

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
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current.click()}>
                    <div className="upload-icon">
                        {file && file.type.includes('pdf') ? '📄' : file && file.type.includes('image/') ? '🖼️' : '📄/🖼️'}
                    </div>
                    <div className="upload-text">点击选择文件或拖拽到此处</div>
                    <div className="upload-hint">支持PDF和常见图片格式，最大50MB</div>
                </div>
                <input
                    type="file"
                    id="file-input"
                    accept=".pdf,.jpg,.jpeg,.png,.gif,.bmp"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    style={{ display: 'none' }}
                />
            </div>

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

            {/* 进度条组件 - 只显示处理阶段进度 */}
            {status === 'processing' && progress > 0 && (
                <div className="progress-container">
                    <div className="progress-bar">
                        <div 
                            className="progress-fill"
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                    <div className="progress-text">
                        {progressMessage || `${progress.toFixed(2)}%`}
                    </div>
                </div>
            )}

            <div className="action-buttons">
                <button
                    className="btn btn-primary"
                    onClick={() => onFileProcess()}
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
                <div className={`status-message status-${statusMessage.type}`}>
                    {statusMessage.message}
                </div>
            )}
        </div>
    );
};

export default Controls;