import React, { useEffect, useMemo, useState } from 'react';
import { MessageSquare, Plus, Paperclip, Image as ImageIcon, FileText, Table } from 'lucide-react';
import './ChatPage.css';
import { getConversations, createConversation, consumeQueue, addMessage, setTargetConversation } from '../utils/chatStorage';

function Sidebar({ convs, activeId, onSelect, onCreate }) {
  return (
    <div className="chat-sider">
      <div className="sider-header">
        <div className="sider-title">
          <MessageSquare size={18} />
          <span>聊天</span>
        </div>
        <button className="sider-new" onClick={onCreate} title="新建对话">
          <Plus size={16} />
          <span>新建</span>
        </button>
      </div>
      <div className="sider-body">
        {convs.length === 0 ? (
          <div className="empty">暂无对话</div>
        ) : (
          convs.map((c) => (
            <div
              key={c.id}
              className={c.id === activeId ? 'sider-item active' : 'sider-item'}
              onClick={() => onSelect(c.id)}
              title={new Date(c.createdAt).toLocaleString()}
            >
              <div className="sider-item-title">{c.title || '未命名对话'}</div>
              <div className="sider-item-meta">{new Date(c.createdAt).toLocaleString()}</div>
            </div>
          ))
        )}
      </div>
      <div className="sider-footer">
        <a
          className="back-link"
          href={typeof window !== 'undefined' ? window.location.origin + window.location.pathname : '/'}
          title="返回主页面"
        >
          返回主页面
        </a>
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [convs, setConvs] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [input, setInput] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [preview, setPreview] = useState({ open: false, data: null });

  useEffect(() => {
    const existing = getConversations();
    setConvs(existing);
    const queued = consumeQueue();
    const urlHasNew =
      typeof window !== 'undefined' && /[?#&]new=1\b/.test(window.location.hash || window.location.search);
    if (queued && queued.length > 0) {
      const conv = createConversation({
        title: '新的上下文对话',
        initialMessages: [],
      });
      setAttachments(queued);
      setConvs(getConversations());
      setActiveId(conv.id);
    } else if (existing.length > 0) {
      setActiveId(existing[0].id);
    } else if (urlHasNew) {
      const conv = createConversation({ title: '新对话' });
      setConvs(getConversations());
      setActiveId(conv.id);
    }
  }, []);

  // 将当前激活会话设置为目标接收对话
  useEffect(() => {
    if (activeId) {
      setTargetConversation(activeId);
    }
  }, [activeId]);

  // 监听其它页面追加的队列项，追加到当前聊天窗口的附件中
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'textsnap_chat_queue') {
        const items = consumeQueue();
        if (!items || items.length === 0) return;
        const forMe = items.filter((it) => !it.convId || it.convId === activeId);
        if (forMe.length > 0) {
          setAttachments((prev) => prev.concat(forMe));
        }
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, [activeId]);

  const activeConv = useMemo(() => convs.find((c) => c.id === activeId) || null, [convs, activeId]);

  const handleCreate = () => {
    const conv = createConversation({ title: '新对话' });
    setConvs(getConversations());
    setActiveId(conv.id);
  };

  const handleSend = () => {
    if (!activeId) return;
    const hasInput = input.trim().length > 0;
    const hasAttach = attachments.length > 0;
    if (!hasInput && !hasAttach) return;
    const content = hasInput ? input : '';
    addMessage(activeId, { role: 'user', content, meta: { attachments } });
    setConvs(getConversations());
    setInput('');
    setAttachments([]);
    setTimeout(() => {
      addMessage(activeId, {
        role: 'assistant',
        content: '（AI 回复占位，后端准备好后接入）',
      });
      setConvs(getConversations());
    }, 300);
  };

  return (
    <div className="chat-page">
      <Sidebar convs={convs} activeId={activeId} onSelect={setActiveId} onCreate={handleCreate} />
      <div className="chat-main">
        <div className="messages">
          {activeConv ? (
            activeConv.messages.map((m) => {
              const atts = m.meta?.attachments || [];
              return (
                <div key={m.id} className={'msg ' + m.role}>
                  <div className="role">{m.role === 'user' ? '我' : 'AI'}</div>
                  <div className="content">
                    {atts.length > 0 && (
                      <div className="msg-attachments">
                        {atts.map((a, i) => (
                          <div
                            className="attachment-card"
                            key={i}
                            onClick={() => setPreview({ open: true, data: a })}
                            title="点击查看内容"
                          >
                            <div className="card-head">
                              <span className="card-icon">
                                {a.type === 'image' ? (
                                  <ImageIcon size={14} />
                                ) : a.type === 'table' ? (
                                  <Table size={14} />
                                ) : (
                                  <FileText size={14} />
                                )}
                              </span>
                              <span className="card-title">
                                {a.type === 'image' ? '图片片段' : a.type === 'table' ? '表格片段' : '文本片段'}
                              </span>
                            </div>
                            <div className="card-body">
                              {a.type === 'text'
                                ? (a.text || '').slice(0, 60)
                                : a.type === 'table'
                                ? '点击查看表格'
                                : '点击查看图片'}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {m.content && <div className="msg-text">{m.content}</div>}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty">请选择或创建一个对话</div>
          )}
        </div>
        <div className="composer">
          {attachments.length > 0 && (
            <div className="attachments">
              <div className="attachments-title">
                <Paperclip size={14} />
                <span>已添加的上下文</span>
              </div>
              <div className="attachments-cards">
                {attachments.map((a, i) => {
                  return (
                    <div className="attachment-card" key={i}>
                      <div className="card-head">
                        <span className="card-icon">
                          {a.type === 'image' ? (
                            <ImageIcon size={14} />
                          ) : a.type === 'table' ? (
                            <Table size={14} />
                          ) : (
                            <FileText size={14} />
                          )}
                        </span>
                        <span className="card-title">
                          {a.type === 'image' ? '图片片段' : a.type === 'table' ? '表格片段' : '文本片段'}
                        </span>
                        <button
                          className="attach-remove"
                          onClick={() => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
                        >
                          移除
                        </button>
                      </div>
                      <div
                        className="card-body clickable"
                        onClick={() => setPreview({ open: true, data: a })}
                        title="点击查看内容"
                      >
                        {a.type === 'text'
                          ? (a.text || '').slice(0, 80)
                          : a.type === 'table'
                          ? '点击查看表格'
                          : '点击查看图片'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息，回车发送"
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button onClick={handleSend} disabled={!activeId || (!input.trim() && attachments.length === 0)}>
            发送
          </button>
        </div>
        {preview.open && (
          <div className="preview-modal" onClick={() => setPreview({ open: false, data: null })}>
            <div className="preview-dialog" onClick={(e) => e.stopPropagation()}>
              <div className="preview-header">
                <span>
                  {preview.data?.type === 'image'
                    ? '图片片段'
                    : preview.data?.type === 'table'
                    ? '表格片段'
                    : '文本片段'}
                </span>
                <button className="preview-close" onClick={() => setPreview({ open: false, data: null })}>
                  关闭
                </button>
              </div>
              <div className="preview-content">
                {preview.data?.type === 'text' && <div className="preview-text">{preview.data?.text || ''}</div>}
                {preview.data?.type === 'table' && (
                  <div className="preview-html" dangerouslySetInnerHTML={{ __html: preview.data?.html || '' }} />
                )}
                {preview.data?.type === 'image' && (
                  <div className="preview-html" dangerouslySetInnerHTML={{ __html: preview.data?.html || '' }} />
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
