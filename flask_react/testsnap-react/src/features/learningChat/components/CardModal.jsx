import React, { useEffect, useMemo } from 'react';
import ChatMarkdown from '../../../pages/ChatMarkdown';
import '../learningChat.css';

export default function CardModal({ open, card, onClose, onInsert }) {
  const title = useMemo(() => card?.title || '知识卡片', [card]);
  const content = useMemo(() => card?.content || '', [card]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open || !card) return null;

  return (
    <div className="lcModalMask" role="dialog" aria-modal="true">
      <div className="lcModal">
        <div className="lcModalHeader">
          <div className="lcModalTitle">{title}</div>
          <button type="button" className="lcModalX" onClick={onClose}>×</button>
        </div>
        <div className="lcModalBody">
          <div className="lcMarkdown">
            <ChatMarkdown content={content} />
          </div>
        </div>
        <div className="lcModalActions">
          {typeof onInsert === 'function' && (
            <button type="button" className="lcBtn lcBtnPrimary" onClick={() => onInsert(card)}>
              插入到聊天上下文
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
