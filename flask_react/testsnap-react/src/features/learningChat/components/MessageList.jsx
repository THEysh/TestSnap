import React, { useEffect, useRef, useState } from 'react';
import ChatMarkdown from '../../../pages/ChatMarkdown';
import '../learningChat.css';

function copyToClipboard(text) {
  const value = String(text || '');
  if (!value) return Promise.resolve(false);
  if (navigator?.clipboard?.writeText) {
    return navigator.clipboard.writeText(value).then(() => true).catch(() => false);
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = value;
    ta.setAttribute('readonly', 'true');
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    ta.style.top = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return Promise.resolve(!!ok);
  } catch {
    return Promise.resolve(false);
  }
}

export default function MessageList({ messages, streaming }) {
  const endRef = useRef(null);
  const [copiedId, setCopiedId] = useState('');
  const copiedTimerRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' });
  }, [messages.length, streaming]);

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    };
  }, []);

  return (
    <div className="lcThread">
      {messages.map((m) => (
        <div key={m.id} className={m.role === 'user' ? 'lcMsg lcMsgUser' : 'lcMsg lcMsgAi'}>
          <div className="lcBubble">
            <div className="lcMsgActions">
              <button
                type="button"
                className="lcActionBtn"
                title={m.role === 'assistant' ? '复制原始 Markdown' : '复制内容'}
                onClick={async () => {
                  const ok = await copyToClipboard(m.content || '');
                  if (!ok) return;
                  setCopiedId(m.id);
                  if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
                  copiedTimerRef.current = setTimeout(() => {
                    setCopiedId('');
                    copiedTimerRef.current = null;
                  }, 900);
                }}
              >
                {copiedId === m.id ? '已复制' : '复制'}
              </button>
            </div>
            {m.role === 'assistant' ? (
              <div className="lcMarkdown">
                {m.reasoning && (
                  <details className="lcReasoning">
                    <summary className="lcReasoningSummary">思考</summary>
                    <pre className="lcReasoningBody">{String(m.reasoning || '')}</pre>
                  </details>
                )}
                <ChatMarkdown content={m.content} />
              </div>
            ) : (
              <div className="lcPlain">{m.content}</div>
            )}
          </div>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}
