import React, { useEffect, useMemo, useState } from 'react';
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
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= 860;
  });
  const [navOpen, setNavOpen] = useState(() => {
    if (typeof window === 'undefined') return true;
    const mobile = window.innerWidth <= 860;
    if (!mobile) return true;
    try {
      const raw = window.localStorage.getItem('ts_nav_open');
      if (raw === '1') return true;
      if (raw === '0') return false;
    } catch {
      void 0;
    }
    return false;
  });

  useEffect(() => {
    const onResize = () => {
      const mobile = window.innerWidth <= 860;
      setIsMobile(mobile);
      if (!mobile) setNavOpen(true);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    if (!isMobile) return;
    try {
      window.localStorage.setItem('ts_nav_open', navOpen ? '1' : '0');
    } catch {
      void 0;
    }
  }, [isMobile, navOpen]);

  const navClassName = useMemo(() => {
    if (!isMobile) return 'appNav';
    return navOpen ? 'appNav' : 'appNav is-collapsed';
  }, [isMobile, navOpen]);

  const linkProps = isMobile
    ? { onClick: () => setNavOpen(false) }
    : undefined;

  return (
    <div className="appShell">
      <div className={navClassName}>
        <div className="appNavInner">
          <div className="appNavTop">
            <a className="appBrand" href="#/" {...(linkProps || {})}>
              <span className="appBrandDot" />
              AI 学伴
            </a>
            {isMobile && (
              <button
                type="button"
                className="appNavToggle"
                aria-expanded={navOpen ? 'true' : 'false'}
                onClick={() => setNavOpen((v) => !v)}
              >
                {navOpen ? '收起' : '菜单'}
              </button>
            )}
          </div>

          <div className="appNavLinks">
            <a className="appNavLink" href="#/app" {...(linkProps || {})}>学习中枢</a>
            <a className="appNavLink" href="#/chat" {...(linkProps || {})}>AI 学习聊天</a>
            <a className="appNavLink" href="#/library" {...(linkProps || {})}>卡片库</a>
            <a className="appNavLink" href="#/file-processing" {...(linkProps || {})}>文件处理</a>
            <a className="appNavLink" href="#/privacy" {...(linkProps || {})}>隐私协议</a>
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
                setNavOpen(false);
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
