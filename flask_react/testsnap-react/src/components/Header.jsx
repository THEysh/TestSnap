import React from 'react';
import './Header.css'; // 导入样式文件

const Header = () => {
    return (
        <div className="header">
            <div className="header-content">
                <h1>PDF 处理器</h1>
                <p>上传、处理并对比PDF文件</p>
            </div>
        </div>
    );
};

export default Header;