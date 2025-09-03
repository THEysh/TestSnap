import './ImageViewer.css'; // 对应样式文件

const ImageViewer = ({ file, processedFileUrl }) => {
    const renderContent = () => {
        // 如果有处理后的文件URL，优先显示处理后的文件
        if (processedFileUrl) {
            return <img src={processedFileUrl} alt="Processed Image" className="processed-image" />;
        }
        // 如果有原始文件，显示原始文件预览
        if (file) {
            const fileURL = URL.createObjectURL(file);
            return <img src={fileURL} alt="Original Image" className="original-image" />;
        }
        // 否则，显示占位符
        return (
            <div className="image-placeholder">
                <div className="image-placeholder-icon">🖼️</div>
                <p>请先上传图片文件，如果上传无效，请刷新再尝试</p>
            </div>
        );
    };

    return (
        <div className="image-pane">
            <h2>图片预览</h2>
            {processedFileUrl && (
                <a
                    href={processedFileUrl}
                    download
                    className="btn btn-primary"
                >
                    下载处理后图片
                </a>
            )}
            <div className="image-viewer">
                {renderContent()}
            </div>
        </div>
    );
};

export default ImageViewer;