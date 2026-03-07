import React, { useEffect, useMemo, useRef, useState } from 'react';
import useAuth from '../app/auth/useAuth';
import AppShell from '../app/shell/AppShell';
import CardModal from '../features/learningChat/components/CardModal';
import { enqueueCardsToChat, loadCardLibrary, saveCardLibrary } from '../features/learningChat/services/cardStorage';
import './library.css';

function createId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`.replaceAll('.', '');
}

export default function LibraryPage() {
  const { user, loading } = useAuth();
  const saveTimerRef = useRef(null);
  const [query, setQuery] = useState('');
  const [cards, setCards] = useState([]);
  const [openCard, setOpenCard] = useState(null);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newMeta, setNewMeta] = useState('');
  const [newContent, setNewContent] = useState('');
  const [toast, setToast] = useState('');
  const toastTimerRef = useRef(null);
  const [confirm, setConfirm] = useState({ open: false, ids: [] });

  useEffect(() => {
    if (!loading && !user) window.location.hash = '#/login';
  }, [loading, user]);

  useEffect(() => {
    if (!user?.id) return;
    const list = loadCardLibrary(user.id);
    setCards(list);
  }, [user?.id]);

  useEffect(() => {
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  const persist = (nextCards) => {
    if (!user?.id) return;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      saveCardLibrary(user.id, nextCards);
      saveTimerRef.current = null;
    }, 120);
  };

  const showToast = (msg) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast(String(msg || ''));
    toastTimerRef.current = setTimeout(() => {
      setToast('');
      toastTimerRef.current = null;
    }, 1300);
  };

  const filtered = useMemo(() => {
    const q = String(query || '').trim().toLowerCase();
    if (!q) return cards;
    return cards.filter((c) => {
      const hay = `${c.title || ''}\n${c.meta || ''}\n${c.content || ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [cards, query]);

  const selectedCount = useMemo(() => selectedIds.size, [selectedIds]);

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedIds(new Set());
    setSelectionMode(false);
  };

  const selectAllFiltered = () => {
    setSelectedIds(new Set(filtered.map((c) => c.id)));
    setSelectionMode(true);
  };

  const openCreate = () => {
    setCreating(true);
    setNewTitle('');
    setNewMeta('');
    setNewContent('');
  };

  const createCard = () => {
    const title = String(newTitle || '').trim() || '知识卡片';
    const meta = String(newMeta || '').trim();
    const content = String(newContent || '').trim();
    if (!content) return;
    const card = { id: createId(), title, meta, content };
    const next = [card].concat(cards);
    setCards(next);
    persist(next);
    setCreating(false);
    setOpenCard(card);
    showToast('已新增卡片');
  };

  const askDelete = (ids) => {
    const list = (ids || []).map((x) => String(x)).filter(Boolean);
    if (list.length === 0) return;
    setConfirm({ open: true, ids: list });
    setSelectionMode(true);
    setSelectedIds(new Set(list));
  };

  const confirmDelete = () => {
    const ids = (confirm?.ids || []).map((x) => String(x));
    if (ids.length === 0) {
      setConfirm({ open: false, ids: [] });
      return;
    }
    const next = cards.filter((c) => !ids.includes(String(c.id)));
    setCards(next);
    persist(next);
    if (openCard && ids.includes(String(openCard.id))) setOpenCard(null);
    setConfirm({ open: false, ids: [] });
    setSelectedIds(new Set());
    setSelectionMode(false);
    showToast(`已删除 ${ids.length} 张卡片`);
  };

  const insertSelectedToChat = () => {
    if (!user?.id) return;
    const selected = cards.filter((c) => selectedIds.has(c.id));
    if (selected.length === 0) return;
    enqueueCardsToChat(user.id, selected);
    showToast(`已加入 ${selected.length} 张到聊天上下文`);
    window.location.hash = '#/chat';
  };

  if (loading || !user) return null;

  return (
    <AppShell title="卡片库">
      <div className="libLayout">
        <div className="libTop">
          <div className="libSearch">
            <input
              className="libInput"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索卡片标题 / 内容…"
            />
            <div className="libCount">共 {filtered.length} 张</div>
          </div>

          <div className="libActions">
            {!selectionMode ? (
              <>
                <button type="button" className="libBtn libBtnGhost" onClick={() => setSelectionMode(true)} disabled={filtered.length === 0}>
                  选择
                </button>
                <button type="button" className="libBtn libBtnPrimary" onClick={openCreate}>
                  新增卡片
                </button>
              </>
            ) : (
              <>
                <div className="libSelMeta">已选 {selectedCount} / {filtered.length}</div>
                <button type="button" className="libBtn libBtnGhost" onClick={selectAllFiltered} disabled={filtered.length === 0}>
                  全选
                </button>
                <button type="button" className="libBtn libBtnPrimary" onClick={insertSelectedToChat} disabled={selectedCount === 0}>
                  插入到聊天卡片
                </button>
                <button type="button" className="libBtn libBtnDanger" onClick={() => askDelete(Array.from(selectedIds))} disabled={selectedCount === 0}>
                  删除
                </button>
                <button type="button" className="libBtn libBtnGhost" onClick={clearSelection}>
                  完成
                </button>
              </>
            )}
          </div>
        </div>

        <div className="libGrid">
          {filtered.map((c) => (
            <div
              key={c.id}
              className={[
                'libCard',
                selectionMode ? 'is-selecting' : '',
                selectedIds.has(c.id) ? 'is-selected' : ''
              ].filter(Boolean).join(' ')}
            >
              {selectionMode && (
                <label className="libCheck" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(c.id)}
                    onChange={() => toggleSelect(c.id)}
                  />
                </label>
              )}
              <button
                type="button"
                className="libCardMain"
                onClick={() => {
                  if (selectionMode) {
                    toggleSelect(c.id);
                    return;
                  }
                  setOpenCard(c);
                }}
              >
                <div className="libCardTitle">{c.title}</div>
                <div className="libCardMeta">{c.meta || '知识卡片'}</div>
              </button>
              {!selectionMode && (
                <div className="libCardActions">
                  <button type="button" className="libCardBtn" onClick={() => setOpenCard(c)}>
                    查看
                  </button>
                  <button
                    type="button"
                    className="libCardBtn libCardBtnPrimary"
                    title="插入至聊天卡片"
                    onClick={() => {
                      enqueueCardsToChat(user.id, [c]);
                      showToast('已加入到聊天上下文');
                      window.location.hash = '#/chat';
                    }}
                  >
                    插入
                  </button>
                  <button type="button" className="libCardBtn libCardBtnDanger" onClick={() => askDelete([c.id])}>
                    删除
                  </button>
                </div>
              )}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="libEmpty">
              暂无卡片。先在“新增卡片”创建，或从文件处理页保存到卡片库。
            </div>
          )}
        </div>

        <CardModal
          open={!!openCard}
          card={openCard}
          onClose={() => setOpenCard(null)}
          onInsert={(card) => {
            if (!user?.id) return;
            enqueueCardsToChat(user.id, [card]);
            showToast('已加入到聊天上下文');
            setOpenCard(null);
            window.location.hash = '#/chat';
          }}
        />

        {creating && (
          <div className="libModalMask" role="dialog" aria-modal="true">
            <div className="libModal">
              <div className="libModalHeader">
                <div className="libModalTitle">新增卡片</div>
                <button type="button" className="libModalX" onClick={() => setCreating(false)}>×</button>
              </div>
              <div className="libModalBody">
                <div className="libFormRow">
                  <div className="libFormLabel">标题</div>
                  <input className="libFormInput" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="例如：泰勒公式" />
                </div>
                <div className="libFormRow">
                  <div className="libFormLabel">标签</div>
                  <input className="libFormInput" value={newMeta} onChange={(e) => setNewMeta(e.target.value)} placeholder="例如：数学 · 复习卡片" />
                </div>
                <div className="libFormRow">
                  <div className="libFormLabel">内容（Markdown）</div>
                  <textarea className="libFormTextarea" value={newContent} onChange={(e) => setNewContent(e.target.value)} rows={10} placeholder="支持 Markdown，可粘贴图片链接…" />
                </div>
              </div>
              <div className="libModalActions">
                <button type="button" className="libBtn libBtnPrimary" onClick={createCard} disabled={!String(newContent || '').trim()}>
                  保存
                </button>
                <button type="button" className="libBtn libBtnGhost" onClick={() => setCreating(false)}>
                  取消
                </button>
              </div>
            </div>
          </div>
        )}

        {confirm.open && (
          <div className="libConfirmMask" role="dialog" aria-modal="true">
            <div className="libConfirm">
              <div className="libConfirmTitle">删除卡片</div>
              <div className="libConfirmDesc">
                将删除 {confirm.ids.length} 张卡片，此操作不可撤销。
              </div>
              <div className="libConfirmActions">
                <button type="button" className="libBtn libBtnDanger" onClick={confirmDelete}>
                  确认删除
                </button>
                <button type="button" className="libBtn libBtnGhost" onClick={() => setConfirm({ open: false, ids: [] })}>
                  取消
                </button>
              </div>
            </div>
          </div>
        )}

        {!!toast && (
          <div className="libToast" role="status" aria-live="polite">
            {toast}
          </div>
        )}
      </div>
    </AppShell>
  );
}
