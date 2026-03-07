import React, { useMemo, useState } from 'react';
import useAuth from '../app/auth/useAuth';
import './auth.css';

function getDefaultMode() {
  try {
    const hash = window.location.hash || '';
    return hash.includes('mode=signup') ? 'signup' : 'signin';
  } catch {
    return 'signin';
  }
}

export default function AuthPage() {
  const { user, loading, signIn, signUp } = useAuth();
  const [mode, setMode] = useState(getDefaultMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const title = useMemo(() => (mode === 'signup' ? '注册账号' : '欢迎回来'), [mode]);
  const subtitle = useMemo(() => (
    mode === 'signup'
      ? '创建你的专属学习空间，从一次上传与一次复盘开始。'
      : '登录后进入学习中枢：今日待办、建议与成长记录。'
  ), [mode]);

  if (!loading && user) {
    window.location.hash = '#/app';
    return null;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError('');
    try {
      const res = mode === 'signup'
        ? await signUp({ name, email, password })
        : await signIn({ email, password });
      if (!res.ok) {
        setError(res.error || '操作失败');
        return;
      }
      window.location.hash = '#/app';
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="authShell">
      <div className="authCard">
        <a className="authBrand" href="#/">
          <span className="authDot" />
          AI 学伴
        </a>

        <div className="authHeader">
          <h1 className="authTitle">{title}</h1>
          <div className="authSubtitle">{subtitle}</div>
        </div>

        <div className="authTabs">
          <button
            type="button"
            className={mode === 'signin' ? 'authTab is-active' : 'authTab'}
            onClick={() => setMode('signin')}
          >
            登录
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'authTab is-active' : 'authTab'}
            onClick={() => setMode('signup')}
          >
            注册
          </button>
        </div>

        <form className="authForm" onSubmit={onSubmit}>
          {mode === 'signup' && (
            <label className="authField">
              <div className="authLabel">昵称</div>
              <input
                className="authInput"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="例如：小明"
                autoComplete="nickname"
              />
            </label>
          )}
          <label className="authField">
            <div className="authLabel">邮箱</div>
            <input
              className="authInput"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              autoComplete="email"
            />
          </label>
          <label className="authField">
            <div className="authLabel">密码</div>
            <input
              className="authInput"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              placeholder="至少 6 位"
              autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
            />
          </label>

          {error && <div className="authError">{error}</div>}

          <button className="authSubmit" type="submit" disabled={submitting || loading}>
            {mode === 'signup' ? (submitting ? '注册中...' : '注册并进入') : (submitting ? '登录中...' : '登录')}
          </button>
        </form>

        <div className="authFooter">
          <a className="authLink" href="#/privacy">隐私协议</a>
          <a className="authLink" href="#/demo">先体验 Demo</a>
        </div>
      </div>
    </div>
  );
}

