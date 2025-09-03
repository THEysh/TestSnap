import React from 'react';
import './PDFViewer.css'; // 对应样式文件

const PDFViewer = ({ title = "PDF预览", file, processedFileUrl, downloadLink }) => {
    const renderContent = () => {
        // 如果有处理后的文件URL，优先显示处理后的文件
        if (processedFileUrl) {
            return <iframe src={processedFileUrl} title="Processed PDF Viewer" type="application/pdf"></iframe>;
        }
        // 如果有原始文件，显示原始文件预览
        if (file) {
            const fileURL = URL.createObjectURL(file);
            return <iframe src={fileURL} title="Original PDF Viewer" type="application/pdf"></iframe>;
        }
        // 否则，显示占位符
        return (
            <div className="pdf-placeholder">
                <div className="pdf-placeholder-icon">📄</div>
                <p>请先上传PDF文件</p>
            </div>
        );
    };

    return (
        <div className="pdf-pane">
            <h2>{title}</h2>
            {processedFileUrl && (
                <a
                    href={processedFileUrl}
                    download={downloadLink}
                    className="btn btn-primary"
                >
                    下载处理后PDF
                </a>
            )}
            <div className="pdf-viewer">
                {renderContent()}
            </div>
        </div>
    );
};

export default PDFViewer;