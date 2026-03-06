import React, { useState, useEffect } from 'react';
import './MarkdownViewer.css';
import useMarkdownLoader from '../hooks/useMarkdownLoader';
import useMarkdownRenderer from '../hooks/useMarkdownRenderer';
import ProgressBar from './ProgressBar';
import { updateImagePaths } from '../utils/markdownUtils';

const MarkdownViewer = ({ autoLoadPath, streamContent, streamActive, progress, progressMessage }) => {
  const [markdownContent, setMarkdownContent] = useState('');
  const [loadedPath, setLoadedPath] = useState('');
  // 使用自定义Hooks
  const { 
    content, 
    fileDir, 
    error, 
    loadMarkdownFile 
  } = useMarkdownLoader();
  
  const { 
    previewRef, 
    debouncedRender 
  } = useMarkdownRenderer();

  // 处理内容变化
  const handleContentChange = (e) => {
    setMarkdownContent(e.target.value);
    debouncedRender(e.target.value);
  };

  useEffect(() => {
    // 仅当 autoLoadPath 有值，且与当前路径不同时才执行
    if (autoLoadPath && loadedPath !== autoLoadPath) {
      const handleAutoLoad = async () => {
        const success = await loadMarkdownFile(autoLoadPath);
        if (success) {
          const updatedContent = updateImagePaths(content, fileDir);
          setMarkdownContent(updatedContent);
          debouncedRender(updatedContent);
          setLoadedPath(autoLoadPath);
        } else if (error) {
          setLoadedPath(autoLoadPath);
        }
      };
      // 调用异步函数
      handleAutoLoad();
    }
  }, [autoLoadPath, loadedPath, content, error]);
  
  // 当content或fileDir更新时，更新markdownContent并渲染预览
  useEffect(() => {
    // 只有当content不为空时才更新，避免初始渲染时的空内容
    if (content) {
      const updatedContent = updateImagePaths(content, fileDir);
      setMarkdownContent(updatedContent);
      debouncedRender(updatedContent);
    }
  }, [content, loadedPath, fileDir]);

  useEffect(() => {
    if (!streamActive) return;
    if (streamContent === null || streamContent === undefined) return;
    const updatedContent = updateImagePaths(streamContent, fileDir);
    setMarkdownContent(updatedContent);
    debouncedRender(updatedContent);
  }, [streamContent, streamActive, fileDir]);

  return (
    <div className="markdown-container">
      <div className="header">
        <p>image,LaTeX数学公式实时渲染</p>
        <p>    计算结果3小时后自动删除</p>
      </div>
      <ProgressBar progress={progress} message={progressMessage} />

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
