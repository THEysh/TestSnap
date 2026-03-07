import React from 'react';
import useAuth from '../auth/useAuth';
import './shell.css';

function getInitials(nameOrEmail) {
  const s = String(nameOrEmail || '').trim();
  if (!s) return '?';
  const parts = s.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

export default function AppShell({ children, title }) {
  const { user, signOut } = useAuth();

  return (
    <div className="appShell">
      <div className="appNav">
        <div className="appNavInner">
          <a className="appBrand" href="#/">
            <span className="appBrandDot" />
            AI 学伴
          </a>

          <div className="appNavLinks">
            <a className="appNavLink" href="#/app">学习中枢</a>
            <a className="appNavLink" href="#/chat">AI 学习聊天</a>
            <a className="appNavLink" href="#/library">卡片库</a>
            <a className="appNavLink" href="#/file-processing">文件处理</a>
            <a className="appNavLink" href="#/privacy">隐私协议</a>
          </div>

          <div className="appNavRight">
            <div className="appUser">
              <div className="appAvatar">{getInitials(user?.name || user?.email)}</div>
              <div className="appUserMeta">
                <div className="appUserName">{user?.name || '未登录'}</div>
                <div className="appUserSub">{user?.email || ''}</div>
              </div>
            </div>
            <button
              type="button"
              className="appNavBtn"
              onClick={() => {
                signOut();
                window.location.hash = '#/';
              }}
            >
              退出
            </button>
          </div>
        </div>
      </div>

      <div className="appMain">
        <div className="appMainInner">
          {title && <div className="appTitle">{title}</div>}
          {children}
        </div>
      </div>
    </div>
  );
}
