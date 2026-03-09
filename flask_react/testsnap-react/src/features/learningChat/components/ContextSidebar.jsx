import React, { useEffect, useMemo, useRef, useState } from 'react';
import '../learningChat.css';

export default function ContextSidebar({
  tasks,
  activeTaskId,
  onCompleteTask,
  onSelectTask,
  personalities,
  activePersonalityId,
  onSelectPersonality,
  cards,
  onOpenCard,
  onDeleteCard
}) {
  const [personaOpen, setPersonaOpen] = useState(false);
  const [personaQuery, setPersonaQuery] = useState('');
  const [personaOpenUp, setPersonaOpenUp] = useState(false);
  const personaWrapRef = useRef(null);
  const personaSearchRef = useRef(null);

  const activePersonality = useMemo(() => {
    const list = Array.isArray(personalities) ? personalities : [];
    return list.find((p) => p.id === activePersonalityId) || list[0] || null;
  }, [personalities, activePersonalityId]);

  const filteredPersonalities = useMemo(() => {
    const list = Array.isArray(personalities) ? personalities : [];
    const q = String(personaQuery || '').trim().toLowerCase();
    if (!q) return list;
    return list.filter((p) => {
      const t = String(p?.title || '').toLowerCase();
      const d = String(p?.desc || '').toLowerCase();
      return t.includes(q) || d.includes(q);
    });
  }, [personalities, personaQuery]);

  useEffect(() => {
    if (!personaOpen) return;
    const onDown = (e) => {
      const root = personaWrapRef.current;
      if (!root) return;
      if (root.contains(e.target)) return;
      setPersonaOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setPersonaOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [personaOpen]);

  useEffect(() => {
    if (!personaOpen) return;
    const t = setTimeout(() => personaSearchRef.current?.focus?.(), 0);
    return () => clearTimeout(t);
  }, [personaOpen]);

  return (
    <div className="lcSidebar">
      <div className="lcPanel">
        <div className="lcPanelTitle">当前学习任务</div>
        <div className="lcTaskList">
          {tasks.map((t) => (
            <div key={t.id} className={t.id === activeTaskId ? 'lcTask is-active' : 'lcTask'}>
              <button type="button" className="lcTaskMain" onClick={() => onSelectTask(t.id)}>
                <div className="lcTaskName">{t.title}</div>
                {!!t.desc && <div className="lcTaskDesc">{t.desc}</div>}
              </button>
              <button type="button" className="lcTaskDone" onClick={() => onCompleteTask(t.id)}>
                完成
              </button>
            </div>
          ))}
          {tasks.length === 0 && <div className="lcEmpty">暂无任务</div>}
        </div>
      </div>

      <div className="lcPanel">
        <div className="lcPanelTitle">学伴性格</div>
        <div ref={personaWrapRef} className="lcPersonaPicker">
          <button
            type="button"
            className="lcPersonaBtn"
            title={activePersonality?.desc || ''}
            onClick={() => {
              const btn = personaWrapRef.current?.querySelector?.('button');
              if (btn && typeof window !== 'undefined') {
                const rect = btn.getBoundingClientRect();
                const spaceBelow = window.innerHeight - rect.bottom;
                const spaceAbove = rect.top;
                setPersonaOpenUp(spaceBelow < 320 && spaceAbove > spaceBelow);
              }
              setPersonaOpen((v) => !v);
            }}
          >
            <span className="lcPersonaBtnText">{activePersonality?.title || '选择性格'}</span>
            <span className={personaOpen ? 'lcPersonaCaret is-open' : 'lcPersonaCaret'} aria-hidden="true" />
          </button>
          {!!activePersonality?.desc && <div className="lcPersonaDesc">{activePersonality.desc}</div>}

          {personaOpen && (
            <div className={personaOpenUp ? 'lcPersonaMenu is-up' : 'lcPersonaMenu'} role="listbox" aria-label="学伴性格列表">
              <div className="lcPersonaMenuTop">
                <input
                  ref={personaSearchRef}
                  className="lcPersonaSearch"
                  value={personaQuery}
                  onChange={(e) => setPersonaQuery(e.target.value)}
                  placeholder="搜索性格…"
                />
              </div>
              <div className="lcPersonaList">
                {filteredPersonalities.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={p.id === activePersonalityId ? 'lcPersonaItem is-active' : 'lcPersonaItem'}
                    onClick={() => {
                      onSelectPersonality?.(p.id);
                      setPersonaOpen(false);
                      setPersonaQuery('');
                    }}
                  >
                    <div className="lcPersonaItemTitle">{p.title}</div>
                    {!!p.desc && <div className="lcPersonaItemDesc">{p.desc}</div>}
                  </button>
                ))}
                {filteredPersonalities.length === 0 && <div className="lcPersonaEmpty">无匹配性格</div>}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="lcPanel">
        <div className="lcPanelTitle">知识卡片</div>
        <div className="lcCardList">
          {cards.map((c) => (
            <div key={c.id} className="lcMiniCardRow">
              <button type="button" className="lcMiniCard" onClick={() => onOpenCard(c)}>
                <div className="lcMiniCardTitle">{c.title}</div>
                <div className="lcMiniCardMeta">{c.meta}</div>
              </button>
              <button
                type="button"
                className="lcMiniCardDel"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteCard?.(c);
                }}
                title="删除"
              >
                删除
              </button>
            </div>
          ))}
          {cards.length === 0 && (
            <div className="lcEmpty">
              暂无卡片。去 <a href="#/library">卡片库</a> 加载，或在 <a href="#/file-processing">文件处理</a> 生成。
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

