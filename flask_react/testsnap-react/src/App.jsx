import Header from './components/Header';
import Controls from './components/Controls';
import PDFViewer from './components/PDFViewer';
import ImageViewer from './components/ImageViewer';
import MarkdownViewer from './components/MarkdownViewer';
import './App.css'; // 使用模块化的CSS，或者直接放在App.css中
import React, { useState } from 'react';
function App() {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState('idle'); // idle, uploaded, processing, success, error
    const [progress, setProgress] = useState(0);
    const [processedFileUrl, setProcessedFileUrl] = useState(null);
    const [downloadLink, setDownloadLink] = useState(null);
    const [fileType, setFileType] = useState(''); // pdf 或 image
    const [uploadedFileInfo, setUploadedFileInfo] = useState(null); // 存储上传后的文件信息
    const [autoLoadMarkdownPath, setAutoLoadMarkdownPath] = useState(null); // 自动加载的Markdown文件路径

    // 仅负责上传文件的函数
    const handleUploadFile = async (uploadedFile) => {
        setFile(uploadedFile);
        setStatus('uploading');
        setProgress(0);
        setProcessedFileUrl(null);
        setDownloadLink(null);
        setUploadedFileInfo(null);
        // 设置文件类型
        const isPdf = uploadedFile.type.includes('pdf');
        setFileType(isPdf ? 'pdf' : 'image');
        try {
            // 上传文件
            const uploadFormData = new FormData();
            uploadFormData.append('file', uploadedFile);

            // 根据文件类型选择不同的上传API
            const uploadUrl = isPdf 
                ? 'http://localhost:7861/api/pdf/upload' 
                : 'http://localhost:7861/api/image/upload';

            const uploadResponse = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = (e.loaded / e.total) * 100;
                        setProgress(percent);
                    }
                });
                xhr.onload = () => {
                    if (xhr.status === 200) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(`上传失败: ${xhr.status}`));
                    }
                };
                xhr.onerror = () => reject(new Error('网络错误'));
                xhr.open('POST', uploadUrl);
                xhr.send(uploadFormData);
            });

            if (!uploadResponse.success) {
                throw new Error(uploadResponse.message || '文件上传失败');
            }
            // 文件上传成功后，存储文件信息并等待用户手动触发处理
            setStatus('uploaded');
            setUploadedFileInfo(uploadResponse.file_info);
            setProgress(100);

        } catch (error) {
            console.error('上传失败:', error);
            setStatus('error');
            setProcessedFileUrl(null);
        }
    };

    // 处理已上传文件的函数
    const handleProcessFile = async () => {
        if (!uploadedFileInfo || !file) {
            return;
        }

        setStatus('processing');
        
        try {
            // 处理文件
            const isPdf = file.type.includes('pdf');
            const processUrl = isPdf 
                ? 'http://localhost:7861/api/pdf/process' 
                : 'http://localhost:7861/api/image/process';
            
            const processResponse = await fetch(processUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: uploadedFileInfo.unique_filename }),
            });
            
            const processResult = await processResponse.json();

            if (!processResult.success) {
                throw new Error(processResult.message || '文件处理失败');
            }

            setStatus('success');
            
            // 确保processResult.processed_file存在
            if (processResult && processResult.processed_file) {
                // 根据文件类型设置处理后的文件URL
                if (isPdf) {
                    // 检查processed_file是否包含路径分隔符（表示它是一个相对路径）
                    // 注意：由于我们已经修改了后端的view_file函数，它现在可以处理相对路径
                    // 所以我们可以直接使用processResult.processed_file作为URL的一部分
                    setProcessedFileUrl(`http://localhost:7861/api/pdf/view/${encodeURIComponent(processResult.processed_file)}`);
                    // 对于下载链接，我们只需要文件名
                    const filename = processResult.processed_file.split('/').pop();
                    setDownloadLink(filename);
                    
                } else {
                    // 对于图片文件，同样需要使用encodeURIComponent来编码相对路径
                    setProcessedFileUrl(`http://localhost:7861/api/image/view/${encodeURIComponent(processResult.processed_file)}`);
                    // 对于下载链接，我们只需要文件名
                    const filename = processResult.processed_file.split('/').pop();
                    setDownloadLink(filename);
                }
            } else {
                console.error('处理结果中缺少processed_file字段');
                setStatus('error');
                setProcessedFileUrl(null);
            }

            // 如果存在md_path，设置自动加载的Markdown路径
            if (processResult.md_path) {
                setAutoLoadMarkdownPath(processResult.md_path);
            }

        } catch (error) {
            console.error('处理失败:', error);
            setStatus('error');
            setProcessedFileUrl(null);
        }
    };

    const handleClearFile = () => {
        setFile(null);
        setStatus('idle');
        setProgress(0);
        setProcessedFileUrl(null);
        setDownloadLink(null);
        setFileType('');
        setUploadedFileInfo(null);
    };

    return (
        <div className="container">
            <Header />
            <Controls
                onFileUpload={handleUploadFile}
                onFileProcess={handleProcessFile}
                onClearFile={handleClearFile}
                file={file}
                status={status}
                progress={progress}
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