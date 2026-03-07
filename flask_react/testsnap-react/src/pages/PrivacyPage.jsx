import React from 'react';

export default function PrivacyPage() {
  return (
    <div className="marketing-shell">
      <div className="marketing-card">
        <div className="marketing-cardHeader">
          <div className="marketing-badge">示例文本</div>
          <h1 className="marketing-title">隐私协议</h1>
          <p className="marketing-subtitle">此页面为展示占位，后续替换为正式内容。</p>
        </div>

        <div className="marketing-body">
          <p>我们尊重并保护用户隐私。当前版本仅用于演示展示，不会对外收集个人信息。</p>
          <p>后续上线正式版本时，将在此补充数据收集范围、用途、保存期限与删除机制。</p>
        </div>

        <div className="marketing-actions">
          <a className="marketing-btn marketing-btnGhost" href="#/">返回官网</a>
        </div>
      </div>
    </div>
  );
}

