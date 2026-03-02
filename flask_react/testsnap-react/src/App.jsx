import Header from './components/Header';
import Controls from './components/Controls';
import PDFViewer from './components/PDFViewer';
import ImageViewer from './components/ImageViewer';
import MarkdownViewer from './components/MarkdownViewer';
import './App.css';
import React, { Suspense, useEffect, useMemo, useState } from 'react';
import useFileUpload from './hooks/useFileUpload';
import useFileProcess from './hooks/useFileProcess';

const ChatPage = React.lazy(() => import('./pages/ChatPage'));

function App() {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('');
  const [route, setRoute] = useState(
    typeof window !== 'undefined' ? (window.location.hash || '#/') : '#/'
  );
  useEffect(() => {
    const handler = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);
  const isChat = useMemo(() => route.startsWith('#/chat'), [route]);
  
  // 使用自定义Hooks
  const { 
    status: uploadStatus, 
    uploadedFileInfo, 
    handleUpload, 
    reset: resetUpload 
  } = useFileUpload();
  
  const { 
    status: processStatus, 
    progress, 
    progressMessage, 
    processedFileUrl, 
    downloadLink, 
    autoLoadMarkdownPath, 
    process, 
    reset: resetProcess 
  } = useFileProcess();
  
  // 处理文件上传
  const handleFileUpload = async (uploadedFile) => {
    // 在上传新文件前重置处理状态
    resetProcess();
    setFile(uploadedFile);
    
    const result = await handleUpload(uploadedFile);
    if (result.success) {
      setFileType(result.fileType);
    }
  };
  
  // 处理文件处理
  const handleProcessFile = async () => {
    if (!uploadedFileInfo || !file) {
      return;
    }
    
    await process(uploadedFileInfo.unique_filename, fileType === 'pdf');
  };
  
  // 清除文件
  const handleClearFile = () => {
    setFile(null);
    setFileType('');
    resetUpload();
    resetProcess();
  };

  // 确定当前状态
  const getCurrentStatus = () => {
    if (processStatus !== 'idle') return processStatus;
    return uploadStatus;
  };

  return isChat ? (
    <Suspense fallback={<div style={{ padding: 20 }}>加载聊天页面...</div>}>
      <ChatPage />
    </Suspense>
  ) : (
    <div className="container">
      <Header />
      <Controls
        onFileUpload={handleFileUpload}
        onFileProcess={handleProcessFile}
        onClearFile={handleClearFile}
        file={file}
        status={getCurrentStatus()}
        progress={progress}
        progressMessage={progressMessage}
        fileType={fileType}
      />
      <div className="pdf-container">
        {fileType === 'pdf' ? (
          <PDFViewer
            title="PDF预览"
            file={file}
            processedFileUrl={processedFileUrl}
            downloadLink={downloadLink}
          />
        ) : fileType === 'image' ? (
          <ImageViewer
            file={file}
            processedFileUrl={processedFileUrl}
          />
        ) : (
          <div className="viewer-placeholder">
            <div className="placeholder-icon">📄/🖼️</div>
            <p>请上传PDF或图片文件</p>
          </div>
        )}
      </div>
      <div className="markdown-container">
        <MarkdownViewer autoLoadPath={autoLoadMarkdownPath} />
      </div>
    </div>
  );
}

export default App;
