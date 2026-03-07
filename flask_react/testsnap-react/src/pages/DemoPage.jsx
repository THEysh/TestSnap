import React, { useMemo, useState } from 'react';
import Header from '../components/Header';
import Controls from '../components/Controls';
import PDFViewer from '../components/PDFViewer';
import ImageViewer from '../components/ImageViewer';
import MarkdownViewer from '../components/MarkdownViewer';
import useFileUpload from '../hooks/useFileUpload';
import useFileProcess from '../hooks/useFileProcess';

export default function DemoPage({ routeParams }) {
  const embed = useMemo(() => {
    try {
      return String(routeParams?.get('embed') || '') === '1';
    } catch {
      return false;
    }
  }, [routeParams]);

  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('');

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
    streamContent,
    process,
    reset: resetProcess
  } = useFileProcess();

  const handleFileUpload = async (uploadedFile) => {
    resetProcess();
    setFile(uploadedFile);

    const result = await handleUpload(uploadedFile);
    if (result.success) {
      setFileType(result.fileType);
    }
  };

  const handleProcessFile = async () => {
    if (!uploadedFileInfo || !file) return;
    await process(uploadedFileInfo.unique_filename, fileType === 'pdf');
  };

  const handleClearFile = () => {
    setFile(null);
    setFileType('');
    resetUpload();
    resetProcess();
  };

  const getCurrentStatus = () => {
    if (processStatus !== 'idle') return processStatus;
    return uploadStatus;
  };

  return (
    <div className={embed ? 'demo-embed' : 'container'}>
      {!embed && <Header />}
      <Controls
        onFileUpload={handleFileUpload}
        onFileProcess={handleProcessFile}
        onClearFile={handleClearFile}
        file={file}
        status={getCurrentStatus()}
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
        <MarkdownViewer
          autoLoadPath={autoLoadMarkdownPath}
          streamContent={streamContent}
          streamActive={processStatus === 'processing'}
          progress={progress}
          progressMessage={progressMessage}
        />
      </div>
    </div>
  );
}

