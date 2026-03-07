import React, { useEffect, useMemo } from 'react';
import ChatMarkdown from '../../../pages/ChatMarkdown';
import '../learningChat.css';

export default function GenerateCardModal({
  open,
  loading,
  error,
  title,
  markdown,
  onClose,
  onMinimize,
  onRetry,
  onSave
}) {
  const safeTitle = useMemo(() => String(title || '').trim() || '学习卡片', [title]);
  const safeMarkdown = useMemo(() => String(markdown || ''), [markdown]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="lcModalMask" role="dialog" aria-modal="true">
      <div className="lcModal">
        <div className="lcModalHeader">
          <div className="lcModalTitle">{safeTitle}</div>
          <div className="lcModalHeaderActions">
            {loading && typeof onMinimize === 'function' && (
              <button type="button" className="lcModalX" onClick={onMinimize} title="最小化">
                —
              </button>
            )}
            <button type="button" className="lcModalX" onClick={onClose}>×</button>
          </div>
        </div>
        <div className="lcModalBody">
          {loading && (
            <div className="lcMarkdown">
              <ChatMarkdown content={safeMarkdown || '正在生成学习卡片…'} />
            </div>
          )}
          {!loading && !!error && <div className="lcError">{error}</div>}
          {!loading && !error && (
            <div className="lcMarkdown">
              <ChatMarkdown content={safeMarkdown} />
            </div>
          )}
        </div>
        <div className="lcModalActions">
          {!loading && !error && (
            <button type="button" className="lcBtn lcBtnPrimary" onClick={onSave}>
              保存到卡片库
            </button>
          )}
          {!loading && !!error && (
            <button type="button" className="lcBtn lcBtnPrimary" onClick={onRetry}>
              重试
            </button>
          )}
          <button type="button" className="lcBtn lcBtnGhost" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
