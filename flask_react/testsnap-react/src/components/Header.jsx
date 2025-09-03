import React from 'react';
import './Header.css'; // 导入样式文件

const Header = () => {
    return (
        <div className="header">
            <div className="header-content">
                <h1>TextSnap</h1>
                <p>上传pdf,image。把它们转换为md文档</p>
            </div>
        </div>
    );
};

export default Header;