import React, { useEffect, useMemo, useRef, useState } from 'react';
import { MessageSquare, Plus, Paperclip, Image as ImageIcon, FileText, Table } from 'lucide-react';
import './ChatPage.css';
import '../components/MarkdownViewer.css';
import { getConversations, createConversation, consumeQueue, addMessage, setTargetConversation, deleteConversation, updateLastAssistantMessage, updateLastAssistantReasoning } from '../utils/chatStorage';
import ChatMarkdown from './ChatMarkdown';
import { buildMessages } from '../utils/buildChatMessages';

function Sidebar({ convs, activeId, onSelect, onCreate, onDelete }) {
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
              <button
                className="sider-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(c.id);
                }}
                title="删除该对话"
              >
                删除
              </button>
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
  const previewContentRef = useRef(null);
  const [sending, setSending] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [siderWidth, setSiderWidth] = useState(300);
  const resizeRef = useRef({ dragging: false, startX: 0, startWidth: 300 });
  const modelOptions = useMemo(() => ([
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "Qwen/Qwen3-Next-80B-A3B-Thinking",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-32B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct-128K",
    "Qwen/Qwen2.5-7B-Instruct",
    "zai-org/GLM-4.6V",
    "zai-org/GLM-4.6",
    "deepseek-ai/DeepSeek-V3",
    "deepseek-ai/DeepSeek-V3.1-Terminus",
    "deepseek-ai/DeepSeek-V3.2",
    "deepseek-ai/DeepSeek-R1"

  ]), []);
  const canThinkModels = useMemo(() => ([
    "Pro/zai-org/GLM-5", 
    "Pro/zai-org/GLM-4.7", 
    "deepseek-ai/DeepSeek-V3.2",
    "Pro/deepseek-ai/DeepSeek-V3.2", 
    "zai-org/GLM-4.6", 
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-14B", 
    "Qwen/Qwen3-32B", 
    "Qwen/Qwen3-30B-A3B",
    "tencent/Hunyuan-A13B-Instruct", 
    "zai-org/GLM-4.5V",
    "deepseek-ai/DeepSeek-V3.1-Terminus", 
    "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"
  ]), []);
  const [selectedModel, setSelectedModel] = useState(modelOptions[0]);
  const [enableReasoning, setEnableReasoning] = useState(false);
  const canThink = useMemo(() => canThinkModels.includes(selectedModel), [canThinkModels, selectedModel]);

  const handleCopy = async (text, id) => {
    const value = (text || '').trim();
    if (!value) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const area = document.createElement('textarea');
        area.value = value;
        area.style.position = 'fixed';
        area.style.opacity = '0';
        document.body.appendChild(area);
        area.focus();
        area.select();
        document.execCommand('copy');
        document.body.removeChild(area);
      }
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId((prev) => (prev === id ? null : prev));
      }, 1500);
    } catch (_) {
      setCopiedId(null);
    }
  };

  const getCopyText = (msg) => {
    const content = msg?.content || '';
    const reasoning = msg?.meta?.reasoning || '';
    if (msg?.role === 'assistant' && reasoning) {
      return `思考过程:\n${reasoning}\n\n回复:\n${content}`;
    }
    return content;
  };

  const callChatAPI = async (payload) => {
    const endpoints = ['/api/chat'];
    if (typeof window !== 'undefined') {
      endpoints.push('http://localhost:7861/api/chat');
    }
    for (let i = 0; i < endpoints.length; i++) {
      const url = endpoints[i];
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const ct = res.headers.get('content-type') || '';
        const txt = await res.text();
        if (!txt) throw new Error(`空响应 ${res.status}`);
        if (ct.includes('application/json')) {
          try {
            return JSON.parse(txt);
          } catch (e) {
            throw new Error('JSON解析失败');
          }
        }
        try {
          return JSON.parse(txt);
        } catch (e) {
          return { success: false, error: txt.slice(0, 300) };
        }
      } catch (e) {
        if (i === endpoints.length - 1) {
          return { success: false, error: String(e) };
        }
        // 尝试下一个端点
      }
    }
    return { success: false, error: '未知错误' };
  };

  const streamChatAPI = async (payload, onChunk) => {
    const endpoints = ['/api/chat/stream'];
    if (typeof window !== 'undefined') {
      endpoints.push('http://localhost:7861/api/chat/stream');
    }
    for (let i = 0; i < endpoints.length; i++) {
      const url = endpoints[i];
      try {
        const res = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        if (!res.body) throw new Error('无可读流');
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        const readSep = () => {
          const nn = buffer.indexOf('\n\n');
          const rr = buffer.indexOf('\r\n\r\n');
          if (nn === -1 && rr === -1) return { idx: -1, len: 0 };
          if (nn === -1) return { idx: rr, len: 4 };
          if (rr === -1) return { idx: nn, len: 2 };
          return nn < rr ? { idx: nn, len: 2 } : { idx: rr, len: 4 };
        };
        const handleEvent = (evt) => {
          const lines = evt.split(/\r?\n/);
          const dataLines = lines
            .filter(l => l.trimStart().startsWith('data:'))
            .map(l => {
              const p = l.indexOf('data:');
              const rest = l.slice(p + 5);
              return rest.startsWith(' ') ? rest.slice(1) : rest;
            });
          if (dataLines.length === 0) return false;
          const payloadStr = dataLines.join('\n');
          if (payloadStr === '[DONE]') return true;
          let piece = '';
          try {
            const obj = JSON.parse(payloadStr);
            if (obj && typeof obj === 'object') {
              if (obj.type && obj.content) {
                if (onChunk) onChunk({ type: obj.type, content: obj.content });
                return false;
              }
              piece = obj.delta || obj.content || obj.text || obj.message || '';
              if (!piece && Array.isArray(obj.choices) && obj.choices[0]?.delta?.content) {
                piece = obj.choices[0].delta.content;
              }
            }
          } catch (_) {
            piece = '';
          }
          if (!piece) piece = payloadStr;
          if (onChunk) onChunk(piece);
          return false;
        };
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          while (true) {
            const { idx, len } = readSep();
            if (idx === -1) break;
            const event = buffer.slice(0, idx);
            buffer = buffer.slice(idx + len);
            const isDone = handleEvent(event);
            if (isDone) return { success: true };
          }
        }
        return { success: true };
      } catch (e) {
        if (i === endpoints.length - 1) {
          return { success: false, error: String(e) };
        }
      }
    }
    return { success: false, error: '未知错误' };
  };
  useEffect(() => {
    if (!canThink && enableReasoning) {
      setEnableReasoning(false);
    }
  }, [canThink, enableReasoning]);

  useEffect(() => {
    const handleMove = (e) => {
      if (!resizeRef.current.dragging) return;
      const dx = e.clientX - resizeRef.current.startX;
      const next = Math.min(520, Math.max(220, resizeRef.current.startWidth + dx));
      setSiderWidth(next);
    };
    const handleUp = () => {
      if (!resizeRef.current.dragging) return;
      resizeRef.current.dragging = false;
    };
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, []);

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

  // 预览弹窗内的表格/图片采用 HTML 注入，需在打开时触发 MathJax 渲染
  useEffect(() => {
    if (preview.open && previewContentRef.current && typeof window !== 'undefined' && window.MathJax) {
      try {
        window.MathJax.typesetPromise([previewContentRef.current]);
      } catch (e) {
        // ignore
      }
    }
  }, [preview]);

  // 监听其它页面追加的队列项，追加到当前聊天窗口的附件中
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'textsnap_chat_queue') {
        const items = consumeQueue();
        if (!items || items.length === 0) return;
        if (!activeId) {
          const conv = createConversation({ title: '新对话' });
          setConvs(getConversations());
          setActiveId(conv.id);
          setTargetConversation(conv.id);
          setAttachments((prev) => prev.concat(items));
          return;
        }
        const forMe = items.filter((it) => !it.convId || it.convId === activeId);
        const accept = forMe.length > 0 ? forMe : items;
        setAttachments((prev) => prev.concat(accept));
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
    if (sending) return;
    let convId = activeId;
    if (!convId) {
      const conv = createConversation({ title: '新对话' });
      setConvs(getConversations());
      setActiveId(conv.id);
      setTargetConversation(conv.id);
      convId = conv.id;
    }
    const hasInput = input.trim().length > 0;
    const hasAttach = attachments.length > 0;
    if (!hasInput && !hasAttach) return;
    const content = input;
    // 先记录用户消息
    addMessage(convId, { role: 'user', content, meta: { attachments } });
    setConvs(getConversations());
    setInput('');
    setAttachments([]);
    setSending(true);
    // 构造 messages：历史对话 + 当前用户输入 + 附件（文本拼接到用户输入末尾；图片按接口字段加入）
    const conv = (getConversations().find(c => c.id === convId) || { messages: [] });
    const history = (conv.messages || []).filter(m => m.role === 'user' || m.role === 'assistant');
    const messages = buildMessages(history, content, attachments);
    // 先插入一个空的 assistant 消息作为占位，用于流式追加
    addMessage(convId, { role: 'assistant', content: '' });
    setConvs(getConversations());
    // 流式优先
    const payload = {
      messages,
      model_name: selectedModel,
      enable_reasoning: enableReasoning && canThink
    };
    streamChatAPI(payload, (piece) => {
      if (typeof piece === 'string') {
        updateLastAssistantMessage(convId, piece);
      } else if (piece && typeof piece === 'object') {
        if (piece.type === 'reasoning') {
          updateLastAssistantReasoning(convId, piece.content || '');
        } else if (piece.type === 'content') {
          updateLastAssistantMessage(convId, piece.content || '');
        } else if (piece.type === 'error') {
          updateLastAssistantMessage(convId, `\n\n[错误] ${piece.content || ''}`);
        }
      }
      setConvs(getConversations());
    }).then((ret) => {
      if (!ret.success) {
        return callChatAPI(payload).then(data => {
          const reply = data && data.success ? (data.reply || '') : (data && data.error ? `调用失败：${data.error}` : '调用失败');
          updateLastAssistantMessage(convId, reply);
          setConvs(getConversations());
          return null;
        });
      }
      return null;
    }).catch(err => {
      updateLastAssistantMessage(convId, `\n\n[流式失败] ${String(err)}`);
      setConvs(getConversations());
    }).finally(() => {
      setSending(false);
      setAttachments([]);
    });
  };

  return (
    <div className="chat-page">
      <div className="chat-sider-wrap" style={{ width: siderWidth }}>
        <Sidebar
          convs={convs}
          activeId={activeId}
          onSelect={setActiveId}
          onCreate={handleCreate}
          onDelete={(id) => {
            const remained = deleteConversation(id);
            setConvs(remained);
            if (id === activeId) {
              if (remained.length > 0) {
                setActiveId(remained[0].id);
                setTargetConversation(remained[0].id);
              } else {
                const conv = createConversation({ title: '新对话' });
                setConvs(getConversations());
                setActiveId(conv.id);
                setTargetConversation(conv.id);
              }
            }
          }}
        />
      </div>
      <div
        className="chat-resizer"
        onMouseDown={(e) => {
          resizeRef.current.dragging = true;
          resizeRef.current.startX = e.clientX;
          resizeRef.current.startWidth = siderWidth;
        }}
      />
      <div className="chat-main">
        <div className="messages">
          {activeConv ? (
            activeConv.messages.map((m) => {
              const atts = m.meta?.attachments || [];
              const copyText = getCopyText(m);
              return (
                <div key={m.id} className={'msg ' + m.role}>
                  <div className="msg-actions">
                    <button
                      className="msg-copy"
                      onClick={() => handleCopy(copyText, m.id)}
                      title="复制"
                    >
                      {copiedId === m.id ? '已复制' : '复制'}
                    </button>
                  </div>
                  <div className="role">{m.role === 'user' ? '我' : 'AI'}</div>
                  <div className="content">
                    {m.role === 'assistant' && m.meta?.reasoning ? (
                      <details className="reasoning-block" open>
                        <summary className="reasoning-title">思考过程</summary>
                        <div className="reasoning-body">
                          <ChatMarkdown content={m.meta.reasoning} />
                        </div>
                      </details>
                    ) : null}
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
                              {a.type === 'image' ? (
                                <div
                                  className="card-thumb"
                                  dangerouslySetInnerHTML={{ __html: a.html || '' }}
                                />
                              ) : a.type === 'table' ? (
                                '点击查看表格'
                              ) : (
                                (a.text || '').slice(0, 60)
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {m.content
                      ? <ChatMarkdown content={m.content} />
                      : (m.role === 'assistant' && sending
                        ? <div className="typing-indicator"><span className="dot" /><span className="dot" /><span className="dot" /></div>
                        : null)}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="empty">请选择或创建一个对话</div>
          )}
        </div>
        <div className="composer">
          <details className="chat-settings-wrap" open>
            <summary className="chat-settings-summary">模型与思考</summary>
            <div className="chat-settings">
              <div className="chat-setting">
                <span className="chat-setting-label">模型</span>
                <select
                  className="chat-setting-select"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={sending}
                >
                  {modelOptions.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              {canThink ? (
                <label className="chat-setting chat-toggle">
                  <input
                    type="checkbox"
                    checked={enableReasoning}
                    onChange={(e) => setEnableReasoning(e.target.checked)}
                    disabled={sending}
                  />
                  <span>思考</span>
                </label>
              ) : null}
            </div>
          </details>
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
                        <div className="card-actions">
                          <button
                            className="attach-insert"
                            onClick={() => {
                              const insertText = a.rawMd || a.text || '';
                              setInput(insertText || '');
                            }}
                            title="插入到输入框"
                          >
                            插入
                          </button>
                          <button
                            className="attach-remove"
                            onClick={() => setAttachments((prev) => prev.filter((_, idx) => idx !== i))}
                          >
                            移除
                          </button>
                        </div>
                      </div>
                      <div
                        className="card-body clickable"
                        onClick={() => setPreview({ open: true, data: a })}
                        title="点击查看内容"
                      >
                        {a.type === 'image' ? (
                          <div
                            className="card-thumb"
                            dangerouslySetInnerHTML={{ __html: a.html || '' }}
                          />
                        ) : a.type === 'table' ? (
                          '点击查看表格'
                        ) : (
                          (a.text || '').slice(0, 80)
                        )}
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
          <button onClick={handleSend} disabled={sending || (!input.trim() && attachments.length === 0)}>
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
              <div className="preview-content markdown-container" ref={previewContentRef}>
                {preview.data?.rawMd
                  ? <ChatMarkdown content={preview.data?.rawMd} />
                  : preview.data?.type === 'text'
                    ? <ChatMarkdown content={preview.data?.text || ''} />
                    : null}
                {!preview.data?.rawMd && preview.data?.type === 'table' && (
                  <div className="preview-html" dangerouslySetInnerHTML={{ __html: preview.data?.html || '' }} />
                )}
                {!preview.data?.rawMd && preview.data?.type === 'image' && (
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
