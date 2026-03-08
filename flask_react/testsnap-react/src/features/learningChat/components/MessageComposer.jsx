import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import '../learningChat.css';

export default function MessageComposer({
  input,
  onChangeInput,
  onSend,
  onStop,
  onClear,
  onCopyAll,
  onOpenSidebar,
  showSidebarButton,
  sending,
  modelOptions,
  selectedModel,
  onChangeModel,
  enableReasoning,
  canThink,
  onToggleReasoning,
  contextBlocks,
  onRemoveContext
}) {
  const goFileProcessing = () => {
    window.location.hash = '#/file-processing';
  };

  const [modelOpen, setModelOpen] = useState(false);
  const [modelQuery, setModelQuery] = useState('');
  const [modelOpenUp, setModelOpenUp] = useState(false);
  const [modelMenuStyle, setModelMenuStyle] = useState(null);
  const modelWrapRef = useRef(null);
  const modelSearchRef = useRef(null);
  const modelMenuRef = useRef(null);

  useEffect(() => {
    if (!modelOpen) return;
    const update = () => {
      const root = modelWrapRef.current;
      const btn = root?.querySelector?.('button');
      if (!btn || typeof window === 'undefined') return;
      const viewportHeight = window.innerHeight;

      const rect = btn.getBoundingClientRect();
      const spaceBelow = viewportHeight - rect.bottom;
      const spaceAbove = rect.top;
      const openUp = spaceBelow < 320 && spaceAbove > spaceBelow;
      setModelOpenUp(openUp);
      const maxHeight = Math.max(220, Math.min(520, (openUp ? spaceAbove : spaceBelow) - 16));

      const width = Math.max(1, Math.round(rect.width));
      const left = Math.round(rect.left);

      const next = { left, width, maxHeight };
      if (openUp) {
        next.bottom = Math.max(8, viewportHeight - rect.top + 8);
        next.top = 'auto';
      } else {
        next.top = Math.max(8, rect.bottom + 8);
        next.bottom = 'auto';
      }
      setModelMenuStyle(next);
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [modelOpen]);

  useEffect(() => {
    if (!modelOpen) return;
    const onDown = (e) => {
      const root = modelWrapRef.current;
      const menu = modelMenuRef.current;
      if (root && root.contains(e.target)) return;
      if (menu && menu.contains(e.target)) return;
      setModelOpen(false);
    };
    const onKey = (e) => {
      if (e.key === 'Escape') setModelOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    window.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      window.removeEventListener('keydown', onKey);
    };
  }, [modelOpen]);

  useEffect(() => {
    if (!modelOpen) return;
    const t = setTimeout(() => modelSearchRef.current?.focus?.(), 0);
    return () => clearTimeout(t);
  }, [modelOpen]);

  const filteredModels = useMemo(() => {
    const all = Array.isArray(modelOptions) ? modelOptions : [];
    const q = String(modelQuery || '').trim().toLowerCase();
    if (!q) return all;
    return all.filter((m) => String(m || '').toLowerCase().includes(q));
  }, [modelOptions, modelQuery]);

  return (
    <div className="lcComposer">
      <div className="lcContextRow">
        {contextBlocks.map((c) => (
          <div key={c.id} className="lcChip">
            <span className="lcChipText">{c.title}</span>
            <button type="button" className="lcChipX" onClick={() => onRemoveContext(c.id)}>×</button>
          </div>
        ))}
        {contextBlocks.length === 0 && <div className="lcHint">可从左侧插入知识卡片作为上下文</div>}
      </div>

      <div className="lcModelRow">
        <div className="lcModelLabel">模型</div>
        <div ref={modelWrapRef} className="lcModelPicker">
          <button
            type="button"
            className="lcModelBtn"
            onClick={() => setModelOpen((v) => !v)}
            disabled={sending}
            title={selectedModel || ''}
          >
            <span className="lcModelBtnText">{selectedModel || '选择模型'}</span>
            <span className={modelOpen ? 'lcModelCaret is-open' : 'lcModelCaret'} aria-hidden="true" />
          </button>
          {modelOpen && typeof document !== 'undefined' && createPortal(
            <div
              ref={modelMenuRef}
              className={modelOpenUp ? 'lcModelMenu is-up' : 'lcModelMenu'}
              role="listbox"
              aria-label="模型列表"
              style={modelMenuStyle || undefined}
            >
              <div className="lcModelMenuTop">
                <input
                  ref={modelSearchRef}
                  className="lcModelSearch"
                  value={modelQuery}
                  onChange={(e) => setModelQuery(e.target.value)}
                  placeholder="搜索模型…"
                />
              </div>
              <div className="lcModelList">
                {filteredModels.map((m) => (
                  <button
                    key={m}
                    type="button"
                    className={m === selectedModel ? 'lcModelItem is-active' : 'lcModelItem'}
                    onClick={() => {
                      onChangeModel?.(m);
                      setModelOpen(false);
                      setModelQuery('');
                    }}
                  >
                    {m}
                  </button>
                ))}
                {filteredModels.length === 0 && <div className="lcModelEmpty">无匹配模型</div>}
              </div>
            </div>,
            document.body
          )}
        </div>

        <label className={canThink ? 'lcThinkToggle' : 'lcThinkToggle is-disabled'} title={canThink ? '开启思考会返回更详细的推理过程（更慢）' : '当前模型不支持思考'}>
          <input
            type="checkbox"
            checked={!!enableReasoning}
            disabled={sending || !canThink}
            onChange={(e) => onToggleReasoning?.(e.target.checked)}
          />
          <span className="lcSwitch" aria-hidden="true" />
          <span className="lcThinkText">思考</span>
        </label>
      </div>

      <div className="lcInputRow">
        <textarea
          className="lcTextarea"
          value={input}
          onChange={(e) => onChangeInput(e.target.value)}
          placeholder="输入你的问题…（支持复制粘贴题目/知识点）"
          rows={3}
        />
      </div>

      <div className="lcActions">
        {showSidebarButton && (
          <button type="button" className="lcBtn lcBtnGhost lcSidebarBtn" onClick={() => onOpenSidebar?.()} disabled={sending}>
            学习面板
          </button>
        )}
        <button type="button" className="lcBtn lcBtnGhost" onClick={goFileProcessing} disabled={sending}>
          上传与解析文件
        </button>
        <button type="button" className="lcBtn lcBtnGhost" onClick={() => onCopyAll?.()} disabled={sending}>
          复制对话
        </button>
        <button type="button" className="lcBtn lcBtnGhost" onClick={() => onClear?.()} disabled={sending}>
          清空
        </button>
        {!sending ? (
          <button type="button" className="lcBtn lcBtnPrimary" onClick={onSend} disabled={!input.trim()}>
            发送
          </button>
        ) : (
          <button
            type="button"
            className="lcBtn lcBtnStop"
            onClick={() => onStop?.()}
            title="停止生成"
          >
            <span className="lcStopIcon" aria-hidden="true" />
            停止
          </button>
        )}
      </div>
    </div>
  );
}
