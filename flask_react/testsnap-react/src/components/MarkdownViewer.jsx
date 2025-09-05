import React, { useState, useEffect, useRef } from 'react';
import './MarkdownViewer.css';
import useMarkdownLoader from '../hooks/useMarkdownLoader';
import useMarkdownRenderer from '../hooks/useMarkdownRenderer';
import { updateImagePaths } from '../utils/markdownUtils';

const MarkdownViewer = ({ autoLoadPath }) => {
  const [filePath, setFilePath] = useState('');
  const [markdownContent, setMarkdownContent] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('');
  // 使用自定义Hooks
  const { 
    isLoading, 
    content, 
    fileDir, 
    error, 
    loadMarkdownFile 
  } = useMarkdownLoader();
  
  const { 
    previewRef, 
    debouncedRender 
  } = useMarkdownRenderer();
  const showStatus = (message, type = 'info') => {
    setStatusMessage(message);
    setStatusType(type);
    
    if (type === 'success') {
      // 3秒后自动清除成功消息
      const timeoutId = setTimeout(() => {
        setStatusMessage('');
        setStatusType('');
      }, 3000);
      
      // 清除定时器
      return () => clearTimeout(timeoutId);
    }
  };
  // 处理内容变化
  const handleContentChange = (e) => {
    setMarkdownContent(e.target.value);
    debouncedRender(e.target.value);
  };
  // 处理文件路径变化
  const handleFilePathChange = (e) => {
    setFilePath(e.target.value);
  };
  // 处理加载按钮点击
  const handleLoadButtonClick = async () => {
    showStatus('正在加载文件...', 'loading');
    const success = await loadMarkdownFile(filePath);
    if (success) {
      // 处理图片路径并更新内容
      const updatedContent = updateImagePaths(content, fileDir);
      setMarkdownContent(updatedContent);
      debouncedRender(updatedContent);
      showStatus(`文件加载成功: ${filePath}`, 'success');
    } else if (error) {
      showStatus(error, 'error');
    }
  };
  // 处理回车键加载文件
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLoadButtonClick();
    }
  };

  useEffect(() => {
    // 仅当 autoLoadPath 有值，且与当前路径不同时才执行
    if (autoLoadPath && filePath !== autoLoadPath) {
      const handleAutoLoad = async () => {
        // 1. 设置路径状态
        setFilePath(autoLoadPath);
        // 2. 显示加载状态
        showStatus('正在加载文件...', 'loading');
        // 3. 异步等待文件加载完成
        const success = await loadMarkdownFile(autoLoadPath);
        // 4. 根据加载结果更新状态
        if (success) {
          const updatedContent = updateImagePaths(content, fileDir);
          setMarkdownContent(updatedContent);
          debouncedRender(updatedContent);
          showStatus(`文件加载成功: ${autoLoadPath}`, 'success');
        } else if (error) { // 这里的 error 是 useEffect 依赖项里的最新值
          showStatus(error, 'error');
        }
      };
      // 调用异步函数
      handleAutoLoad();
    }
  }, [autoLoadPath, filePath, content, error]);
  
  // 当content或fileDir更新时，更新markdownContent并渲染预览
  useEffect(() => {
    // 只有当content不为空时才更新，避免初始渲染时的空内容
    if (content) {
      const updatedContent = updateImagePaths(content, fileDir);
      setMarkdownContent(updatedContent);
      debouncedRender(updatedContent);
    }
  }, [content, filePath]);

  return (
    <div className="markdown-container">
      <div className="header">
        <p>image,LaTeX数学公式实时渲染</p>
        <p>    计算结果3小时后自动删除</p>
      </div>
      <div className="controls">
        <div className="path-input-group">
          <input
            type="text"
            id="file-path-input"
            placeholder="例如: srcProject/output/gae/gae.md"
            value={filePath}
            onChange={handleFilePathChange}
            onKeyPress={handleKeyPress}
          />
          <button 
            id="load-button"
            onClick={handleLoadButtonClick}
            disabled={isLoading}
          >
            加载文件
          </button>
        </div>
        {statusMessage && (
          <div className={`status-message status-${statusType}`}>
            {statusMessage}
          </div>
        )}
      </div>

      <div className="editor-container">
        <div className="editor-pane">
          <h2>Markdown 内容</h2>
          <textarea 
            id="markdown-input"
            value={markdownContent}
            onChange={handleContentChange}
            placeholder="在上方输入文件路径并点击加载，或直接在此处编辑Markdown内容..."
          />
        </div>
        <div className="preview-pane">
          <h2>渲染预览</h2>
          <div 
            id="preview"
            ref={previewRef}
          />
        </div>
      </div>
    </div>
  );
};

export default MarkdownViewer;