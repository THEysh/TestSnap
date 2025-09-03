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
// 定义在 handleProcessFile 外面，全局共享
let checkProgress = null;
let timeout = null;

// 统一清理函数
const stopPolling = () => {
    if (checkProgress) {
        clearInterval(checkProgress);
        checkProgress = null;
    }
    if (timeout) {
        clearTimeout(timeout);
        timeout = null;
    }
};

// 处理已上传文件的函数
const handleProcessFile = async () => {
    if (!uploadedFileInfo || !file) {
        return;
    }

    setStatus('processing');
    setProgress(0); // 重置进度
    
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
        
        if (!processResponse.ok) {
            throw new Error(`处理请求失败: ${processResponse.status}`);
        }
        
        const processResult = await processResponse.json();
        if (!processResult.success || !processResult.task_id) {
            throw new Error(processResult.error || '启动处理失败');
        }
        
        const { task_id } = processResult;
        console.log(`任务已启动，ID: ${task_id}`);

        // 启动轮询
        checkProgress = setInterval(async () => {
            try {
                const progResponse = await fetch(`http://localhost:7861/api/task/progress/${task_id}`);
                if (!progResponse.ok) {
                    console.error(`获取进度失败: ${progResponse.status}`);
                    return;
                }
                
                const progress = await progResponse.json();
                if (!progress.success) {
                    console.error('获取进度失败:', progress.error);
                    stopPolling();
                    setStatus('error');
                    return;
                }
                
                setProgress(progress.progress || 0);
                console.log(`进度: ${progress.progress}% - ${progress.message || ''}`);
                
                if (progress.status === 'completed') {
                    stopPolling(); // ✅ 拿到结果立即停掉轮询
                    console.log('处理完成!', progress.result);

                    if (!progress.result || !progress.result.success) {
                        throw new Error(progress.result?.error || '处理结果无效');
                    }
                    const result = progress.result;
                    // 转换路径
                    const processedPath = result.processed_file.replace(/\\/g, '/'); 
                    const processed_md_path = result.md_path.replace(/\\/g, '/');
                    setProcessedFileUrl(`http://localhost:7861/api/files/${encodeURIComponent(processedPath)}`);
                    const filename = processedPath.split('/').pop();
                    setDownloadLink(filename);
                    setAutoLoadMarkdownPath(processed_md_path);
                    setStatus('completed');
                    setProgress(100);

                } else if (progress.status === 'failed') {
                    stopPolling(); // ✅ 失败时也要停掉
                    console.error('处理失败:', progress.message);
                    setStatus('error');
                    setProgress(0);
                }
                // processing 情况下继续轮询
                
            } catch (pollError) {
                console.error('轮询进度时出错:', pollError);
            }
        }, 3000);

        // 设置超时，避免无限轮询
        timeout = setTimeout(() => {
            stopPolling();
            console.error('处理超时');
            setStatus('error');
            setProgress(0);
        }, 5 * 60 * 1000); // 5分钟超时

    } catch (error) {
        stopPolling(); // ✅ 出现异常也要清理
        console.error('处理失败:', error);
        setStatus('error');
        setProgress(0);
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