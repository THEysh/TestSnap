import React, { useEffect, useMemo, useRef, useState } from 'react';
import useAuth from '../app/auth/useAuth';
import AppShell from '../app/shell/AppShell';
import useFileUpload from '../hooks/useFileUpload';
import useFileProcess from '../hooks/useFileProcess';
import { apiRequest } from '../services/apiService';
import { ENDPOINTS } from '../constants/apiConfig';
import { updateImagePaths } from '../utils/markdownUtils';
import useBlockMarkdownRenderer from '../hooks/useBlockMarkdownRenderer';
import ChatMarkdown from './ChatMarkdown';
import { appendToCardLibrary } from '../features/learningChat/services/cardStorage';
import ImageCropper from './ImageCropper';
import './fileProcessing.css';

function createId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`.replaceAll('.', '');
}

function splitByHeadings(markdown) {
  const md = String(markdown || '').trim();
  if (!md) return [];
  const lines = md.split(/\r?\n/);
  const sections = [];
  let current = { title: '未命名卡片', body: [] };
  const flush = () => {
    const body = current.body.join('\n').trim();
    if (!body) return;
    sections.push({
      id: createId(),
      title: current.title,
      meta: '从 Markdown 拆分',
      content: body
    });
  };
  for (const line of lines) {
    const m = /^(#{1,3})\s+(.+)$/.exec(line.trim());
    if (m) {
      flush();
      current = { title: m[2].trim(), body: [] };
      continue;
    }
    current.body.push(line);
  }
  flush();
  return sections;
}

export default function FileProcessing() {
  const { user, loading } = useAuth();
  const upload = useFileUpload();
  const proc = useFileProcess({ persistKey: user?.id ? `ts_file_processing_task_${user.id}` : '' });

  const fileInputRef = useRef(null);
  const editorRef = useRef(null);
  const toastTimerRef = useRef(null);
  const uiPersistTimerRef = useRef(null);
  const uiLoadedRef = useRef(false);
  const fileUrlRef = useRef('');

  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileMeta, setSelectedFileMeta] = useState(null);
  const [fileObjectUrl, setFileObjectUrl] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [dirty, setDirty] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftContent, setDraftContent] = useState('');
  const [cards, setCards] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [error, setError] = useState('');
  const [previewSelection, setPreviewSelection] = useState({ open: false, text: '', x: 0, y: 0 });
  const [toast, setToast] = useState('');
  const [openCard, setOpenCard] = useState(null);
  const [filePreviewHeight, setFilePreviewHeight] = useState(360);
  const resizeRef = useRef({ dragging: false, startY: 0, startH: 360 });
  const [cropOpen, setCropOpen] = useState(false);
  const [cropFile, setCropFile] = useState(null);

  useEffect(() => {
    if (!loading && !user) window.location.hash = '#/login';
  }, [loading, user]);

  useEffect(() => {
    if (!user?.id) return;
    if (uiLoadedRef.current) return;
    uiLoadedRef.current = true;
    try {
      const raw = window.localStorage.getItem(`ts_file_processing_ui_${user.id}`);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object') return;
      if (typeof data.markdown === 'string') setMarkdown(data.markdown);
      if (typeof data.dirty === 'boolean') setDirty(data.dirty);
      if (typeof data.draftTitle === 'string') setDraftTitle(data.draftTitle);
      if (typeof data.draftContent === 'string') setDraftContent(data.draftContent);
      if (Array.isArray(data.cards)) setCards(data.cards);
      if (Array.isArray(data.selectedIds)) setSelectedIds(new Set(data.selectedIds));
      if (data.selectedFileMeta && typeof data.selectedFileMeta === 'object') setSelectedFileMeta(data.selectedFileMeta);
      if (typeof data.filePreviewHeight === 'number' && Number.isFinite(data.filePreviewHeight)) setFilePreviewHeight(data.filePreviewHeight);
    } catch {
      return;
    }
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    if (!uiLoadedRef.current) return;
    if (uiPersistTimerRef.current) clearTimeout(uiPersistTimerRef.current);
    uiPersistTimerRef.current = setTimeout(() => {
      try {
        const payload = {
          markdown,
          dirty,
          draftTitle,
          draftContent,
          cards,
          selectedIds: Array.from(selectedIds),
          selectedFileMeta,
          filePreviewHeight,
          ts: Date.now()
        };
        window.localStorage.setItem(`ts_file_processing_ui_${user.id}`, JSON.stringify(payload));
      } catch {
        void 0;
      } finally {
        uiPersistTimerRef.current = null;
      }
    }, 200);
  }, [user?.id, markdown, dirty, draftTitle, draftContent, cards, selectedIds, selectedFileMeta, filePreviewHeight]);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      if (uiPersistTimerRef.current) clearTimeout(uiPersistTimerRef.current);
      if (fileUrlRef.current) URL.revokeObjectURL(fileUrlRef.current);
    };
  }, []);

  useEffect(() => {
    const onMove = (e) => {
      if (!resizeRef.current.dragging) return;
      const dy = (e?.clientY ?? 0) - resizeRef.current.startY;
      const next = Math.max(220, Math.min(900, resizeRef.current.startH + dy));
      setFilePreviewHeight(next);
    };
    const onUp = () => {
      if (!resizeRef.current.dragging) return;
      resizeRef.current.dragging = false;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  useEffect(() => {
    if (!selectedFile) {
      if (fileUrlRef.current) URL.revokeObjectURL(fileUrlRef.current);
      fileUrlRef.current = '';
      setFileObjectUrl('');
      return;
    }
    if (fileUrlRef.current) URL.revokeObjectURL(fileUrlRef.current);
    fileUrlRef.current = URL.createObjectURL(selectedFile);
    setFileObjectUrl(fileUrlRef.current);
  }, [selectedFile]);

  useEffect(() => {
    const info = upload.uploadedFileInfo;
    if (!info || !selectedFileMeta) return;
    const filePath = String(info.file_path || '').trim();
    const unique = String(info.unique_filename || '').trim();
    const name = String(selectedFileMeta?.name || '').trim();
    const typeStr = String(selectedFileMeta?.type || '').trim();
    const isPdf = typeStr.includes('pdf') || /\.pdf$/i.test(name);
    let rel = '';
    if (filePath) {
      const normalized = filePath.replaceAll('\\', '/');
      const i = normalized.toLowerCase().indexOf('srcproject/');
      if (i >= 0) rel = normalized.slice(i);
    }
    if (!rel && unique) {
      rel = `srcProject/output/visualizations/uploads/${isPdf ? 'pdfs' : 'images'}/${unique}`;
    }
    if (!rel) return;
    const serverUrl = `${ENDPOINTS.FILES}${rel}`;
    setSelectedFileMeta((prev) => ({ ...(prev || {}), serverUrl, unique_filename: unique, file_path: filePath }));
  }, [upload.uploadedFileInfo, selectedFileMeta]);

  const showToast = (msg) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast(String(msg || ''));
    toastTimerRef.current = setTimeout(() => {
      setToast('');
      toastTimerRef.current = null;
    }, 1200);
  };

  const appendToDraft = (mdFragment, preferredTitle) => {
    const frag = String(mdFragment || '').trim();
    if (!frag) return false;
    setError('');
    setDraftContent((prev) => (prev ? `${prev}\n\n---\n\n${frag}` : frag));
    setDraftTitle((prev) => {
      if (String(prev || '').trim()) return prev;
      const t = String(preferredTitle || '').trim();
      if (t) return t.slice(0, 24);
      const first = frag.split(/\r?\n/).find((l) => l.trim()) || '知识卡片';
      return first.trim().slice(0, 24);
    });
    return true;
  };

  const { previewRef, renderMarkdown } = useBlockMarkdownRenderer({
    onBlockClick: (payload) => {
      const raw = String(payload?.rawMd || '').trim();
      const txt = String(payload?.text || '').trim();
      const chosen = raw || txt;
      if (!chosen) return;
      const first = chosen.split(/\r?\n/).find((l) => l.trim()) || '';
      const ok = appendToDraft(chosen, first);
      if (ok) showToast('已追加到卡片草稿');
    }
  });

  useEffect(() => {
    renderMarkdown(markdown || '');
  }, [markdown, renderMarkdown]);

  useEffect(() => {
    const onDown = (e) => {
      if (!previewSelection.open) return;
      const t = e?.target;
      const inBar = t?.closest?.('.fpSelBar');
      if (inBar) return;
      setPreviewSelection({ open: false, text: '', x: 0, y: 0 });
    };
    document.addEventListener('mousedown', onDown);
    return () => document.removeEventListener('mousedown', onDown);
  }, [previewSelection.open]);

  const uploadHint = useMemo(() => {
    const f = selectedFile || selectedFileMeta;
    if (!f) return '支持 PDF / 图片，解析结果将以 Markdown 展示，可编辑并生成知识卡片。';
    const name = f.name || '';
    const typeStr = f.type || '';
    const type = typeStr.includes('pdf') || /\.pdf$/i.test(name) ? 'PDF' : '图片';
    return `已选择：${name}（${type}）`;
  }, [selectedFile, selectedFileMeta]);

  const previewInfo = useMemo(() => {
    const f = selectedFile || selectedFileMeta;
    if (!f) return null;
    const name = String(f.name || '').trim();
    const typeStr = String(f.type || '').trim();
    const isPdf = typeStr.includes('pdf') || /\.pdf$/i.test(name);
    const url = fileObjectUrl || String(selectedFileMeta?.serverUrl || '').trim();
    if (!url) return null;
    return { isPdf, url, name };
  }, [selectedFile, selectedFileMeta, fileObjectUrl]);

  const onPick = () => fileInputRef.current?.click();

  const resetWorkspace = () => {
    setMarkdown('');
    setDirty(false);
    setDraftTitle('');
    setDraftContent('');
    setCards([]);
    setSelectedIds(new Set());
    proc.reset();
    upload.reset();
    try {
      if (user?.id) window.localStorage.removeItem(`ts_file_processing_ui_${user.id}`);
    } catch {
      void 0;
    }
  };

  const onFileChange = async (e) => {
    const f = e.target.files?.[0];
    try {
      if (e.target) e.target.value = '';
    } catch {
      void 0;
    }
    if (!f) return;
    setError('');
    resetWorkspace();
    setSelectedFile(f);
    setSelectedFileMeta({ name: f.name, type: f.type });
    const isPdf = f.type.includes('pdf') || /\.pdf$/i.test(f.name || '');
    if (!isPdf) {
      setCropFile(f);
      setCropOpen(true);
      return;
    }
    const res = await upload.handleUpload(f);
    if (!res.success) setError(res.error || '上传失败');
  };

  const onProcess = async () => {
    if (!upload.uploadedFileInfo || !selectedFile) return;
    setError('');
    const isPdf = selectedFile.type.includes('pdf') || /\.pdf$/i.test(selectedFile.name || '');
    const ok = await proc.process(upload.uploadedFileInfo.unique_filename, isPdf);
    if (!ok?.success && proc.error) setError(proc.error);
  };

  useEffect(() => {
    if (proc.status !== 'completed') return;
    if (!proc.autoLoadMarkdownPath) return;
    const run = async () => {
      const ret = await apiRequest(ENDPOINTS.MARKDOWN, {
        method: 'POST',
        body: JSON.stringify({ path: proc.autoLoadMarkdownPath })
      });
      if (!ret?.success) {
        setError(ret?.error || '加载解析结果失败');
        return;
      }
      const updated = updateImagePaths(ret.content || '', ret.file_dir || '');
      setMarkdown(updated);
      setDirty(false);
    };
    run();
  }, [proc.status, proc.autoLoadMarkdownPath]);

  useEffect(() => {
    if (proc.status !== 'processing') return;
    if (!proc.streamContent) return;
    if (dirty) return;
    setMarkdown(proc.streamContent);
  }, [proc.status, proc.streamContent, dirty]);

  const getPreviewSelectionText = () => {
    try {
      const root = previewRef.current;
      if (!root) return '';
      const sel = window.getSelection?.();
      if (!sel || sel.rangeCount === 0) return '';
      const range = sel.getRangeAt(0);
      const container = range.commonAncestorContainer;
      const node = container?.nodeType === 1 ? container : container?.parentElement;
      if (!node || !root.contains(node)) return '';
      const txt = String(sel.toString() || '').trim();
      return txt;
    } catch {
      return '';
    }
  };

  const getPreviewSelectionRect = () => {
    try {
      const root = previewRef.current;
      if (!root) return null;
      const sel = window.getSelection?.();
      if (!sel || sel.rangeCount === 0) return null;
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect?.();
      if (!rect) return null;
      const container = range.commonAncestorContainer;
      const node = container?.nodeType === 1 ? container : container?.parentElement;
      if (!node || !root.contains(node)) return null;
      return rect;
    } catch {
      return null;
    }
  };

  const createCardFromDraft = () => {
    const content = String(draftContent || '').trim();
    if (!content) {
      setError('请先从预览或编辑框选中内容，加入到卡片草稿');
      return;
    }
    const title = String(draftTitle || '').trim() || '知识卡片';
    const card = { id: createId(), title, meta: '从预览/草稿生成', content };
    setCards((prev) => [card].concat(prev));
    setSelectedIds((prev) => new Set(prev).add(card.id));
    setDraftTitle('');
    setDraftContent('');
  };

  const createCardFromPreviewSelection = () => {
    const txt = getPreviewSelectionText();
    if (!txt) {
      setError('请先在预览区选中文本，或点击预览中的图片');
      return;
    }
    setError('');
    const title = txt.split(/\r?\n/).find((l) => l.trim())?.trim().slice(0, 24) || '知识卡片';
    const card = { id: createId(), title, meta: '从预览选中生成', content: txt };
    setCards((prev) => [card].concat(prev));
    setSelectedIds((prev) => new Set(prev).add(card.id));
  };

  const showPreviewSelectionBar = () => {
    const txt = getPreviewSelectionText();
    const rect = getPreviewSelectionRect();
    if (!txt || !rect) {
      setPreviewSelection({ open: false, text: '', x: 0, y: 0 });
      return;
    }
    const x = Math.max(12, rect.left + rect.width / 2);
    const y = Math.max(12, rect.top - 10);
    setPreviewSelection({ open: true, text: txt, x, y });
  };

  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const buildCardFromSelection = () => {
    const el = editorRef.current;
    if (!el) return;
    const start = el.selectionStart ?? 0;
    const end = el.selectionEnd ?? 0;
    const selected = String(markdown || '').slice(start, end).trim();
    if (!selected) {
      setError('请先在 Markdown 编辑框中选中内容');
      return;
    }
    setError('');
    const title = selected.split(/\r?\n/).find((l) => l.trim())?.slice(0, 22) || '知识卡片';
    const card = { id: createId(), title, meta: '从选中内容生成', content: selected };
    setCards((prev) => [card].concat(prev));
    setSelectedIds((prev) => new Set(prev).add(card.id));
  };

  const buildCardsBySplit = () => {
    const list = splitByHeadings(markdown);
    if (list.length === 0) {
      setError('未检测到可拆分的标题（建议使用 # / ## / ###）');
      return;
    }
    setError('');
    setCards((prev) => list.concat(prev));
    setSelectedIds((prev) => {
      const next = new Set(prev);
      list.forEach((c) => next.add(c.id));
      return next;
    });
  };

  const mergeSelected = () => {
    const ids = Array.from(selectedIds);
    if (ids.length < 2) {
      setError('请至少选择 2 张卡片合并');
      return;
    }
    setError('');
    setCards((prev) => {
      const selected = prev.filter((c) => selectedIds.has(c.id));
      const rest = prev.filter((c) => !selectedIds.has(c.id));
      const merged = {
        id: createId(),
        title: selected[0]?.title || '合并卡片',
        meta: `合并自 ${selected.length} 张卡片`,
        content: selected.map((c) => `## ${c.title}\n\n${c.content}`).join('\n\n---\n\n')
      };
      setSelectedIds(new Set([merged.id]));
      return [merged].concat(rest);
    });
  };

  const saveSelected = () => {
    if (!user?.id) return;
    const selected = cards.filter((c) => selectedIds.has(c.id));
    if (selected.length === 0) {
      setError('请先选择要保存的卡片');
      return;
    }
    setError('');
    const ret = appendToCardLibrary(user.id, selected);
    if (ret?.ok) showToast(`已保存 ${ret.count || selected.length} 张到卡片库`);
    setSelectedIds(new Set());
  };

  if (loading || !user) return null;

  return (
    <AppShell title="文件处理">
      <div className="fpLayout">
        {cropOpen && cropFile && (
          <ImageCropper
            file={cropFile}
            onCancel={() => {
              setCropOpen(false);
              setCropFile(null);
              setSelectedFile(null);
              setSelectedFileMeta(null);
              setFileObjectUrl('');
            }}
            onConfirm={async (outFile) => {
              setCropOpen(false);
              setCropFile(null);
              resetWorkspace();
              setError('');
              setSelectedFile(outFile);
              setSelectedFileMeta({ name: outFile.name, type: outFile.type });
              const res = await upload.handleUpload(outFile);
              if (!res.success) setError(res.error || '上传失败');
            }}
          />
        )}
        <div className="fpCard">
          <div className="fpCardTitle">上传与解析</div>
          <div className="fpHint">{uploadHint}</div>
          <div className="fpActions">
            <input
              ref={fileInputRef}
              type="file"
              className="fpFile"
              onChange={onFileChange}
              accept=".pdf,image/*"
            />
            <button type="button" className="fpBtn fpBtnGhost" onClick={onPick}>
              选择文件
            </button>
            <button
              type="button"
              className="fpBtn fpBtnPrimary"
              onClick={onProcess}
              disabled={upload.status !== 'uploaded' || proc.status === 'processing'}
            >
              {proc.status === 'processing' ? '处理中…' : '处理文件'}
            </button>
            <a className="fpBtn fpBtnGhost" href="#/chat">返回聊天</a>
          </div>

          {proc.status === 'processing' && (
            <div className="fpProgress">
              <div className="fpProgressBar">
                <div className="fpProgressFill" style={{ width: `${proc.progress || 0}%` }} />
              </div>
              <div className="fpProgressText">{proc.progressMessage || '处理中…'}</div>
            </div>
          )}
          {proc.status === 'processing' && !dirty && (
            <div className="fpStreamingHint">正在流式写入 Markdown，等待解析完成…</div>
          )}
          {proc.status === 'processing' && dirty && (
            <div className="fpStreamingHint">你正在编辑 Markdown，流式写入已暂停。</div>
          )}

          {!!error && <div className="fpError">{error}</div>}

          {previewInfo && (
            <div className="fpFilePreview">
              <div className="fpFilePreviewTitle">文件预览</div>
              <div className="fpFilePreviewBody" style={{ height: `${filePreviewHeight}px` }}>
                {previewInfo.isPdf ? (
                  <iframe title={previewInfo.name || 'PDF预览'} src={previewInfo.url} />
                ) : (
                  <img alt={previewInfo.name || '图片预览'} src={previewInfo.url} />
                )}
              </div>
              <div
                className="fpResizeHandle"
                role="separator"
                aria-label="调整预览高度"
                onMouseDown={(e) => {
                  resizeRef.current.dragging = true;
                  resizeRef.current.startY = e.clientY;
                  resizeRef.current.startH = filePreviewHeight;
                }}
              />
            </div>
          )}
        </div>

        <div className="fpSplit">
          <div className="fpCard fpEditor">
            <div className="fpCardTitle">Markdown（可编辑）</div>
            <textarea
              ref={editorRef}
              className="fpTextarea"
              value={markdown}
              onChange={(e) => {
                setDirty(true);
                setMarkdown(e.target.value);
              }}
              placeholder="解析后的 Markdown 将显示在这里…"
              rows={16}
            />
            <div className="fpEditorActions">
              <button type="button" className="fpBtn fpBtnGhost" onClick={buildCardFromSelection} disabled={!markdown}>
                从选中内容生成卡片
              </button>
              <button type="button" className="fpBtn fpBtnGhost" onClick={buildCardsBySplit} disabled={!markdown}>
                按标题拆分生成卡片
              </button>
            </div>
          </div>

          <div className="fpCard fpPreview">
            <div className="fpCardTitle">预览</div>
            <div
              className="fpPreviewBody"
              ref={previewRef}
              onMouseUp={() => {
                showPreviewSelectionBar();
              }}
              onClick={(e) => {
                const t = e?.target;
                if (!t || t.tagName !== 'IMG') return;
                const src = String(t.getAttribute('src') || '').trim();
                if (!src) return;
                const ok = appendToDraft(`![](${src})`, draftTitle || '图片卡片');
                if (ok) showToast('已追加到卡片草稿');
              }}
            />
            <div className="fpPreviewHint">点击任意 Markdown 块可加入草稿；拖选文本可在浮条中选择加入/生成。</div>
            <div className="fpPreviewActions">
              <button type="button" className="fpBtn fpBtnGhost" onClick={createCardFromPreviewSelection}>
                预览选中 → 生成卡片
              </button>
            </div>
          </div>
        </div>

        <div className="fpCard">
          <div className="fpCardTitle">知识卡片</div>
          <div className="fpDraft">
            <div className="fpDraftTop">
              <div className="fpDraftLabel">卡片草稿</div>
              <div className="fpDraftActions">
                <button type="button" className="fpBtn fpBtnPrimary" onClick={createCardFromDraft} disabled={!draftContent.trim()}>
                  生成卡片
                </button>
                <button
                  type="button"
                  className="fpBtn fpBtnGhost"
                  onClick={() => {
                    setDraftTitle('');
                    setDraftContent('');
                  }}
                  disabled={!draftContent.trim() && !draftTitle.trim()}
                >
                  清空草稿
                </button>
              </div>
            </div>
            <div className="fpDraftRow">
              <input
                className="fpDraftTitle"
                value={draftTitle}
                onChange={(e) => setDraftTitle(e.target.value)}
                placeholder="卡片标题（可选）"
              />
            </div>
            <textarea
              className="fpDraftTextarea"
              value={draftContent}
              onChange={(e) => setDraftContent(e.target.value)}
              placeholder="从预览区选中内容追加到这里，或点击预览中的图片…"
              rows={6}
            />
          </div>
          <div className="fpCardActions">
            <button type="button" className="fpBtn fpBtnGhost" onClick={mergeSelected} disabled={selectedIds.size < 2}>
              合并选中
            </button>
            <button type="button" className="fpBtn fpBtnPrimary" onClick={saveSelected} disabled={selectedIds.size === 0}>
              保存到卡片库
            </button>
          </div>

          <div className="fpCardList">
            {cards.map((c) => (
              <div
                key={c.id}
                className="fpCardItem"
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  const tag = e?.target?.tagName;
                  if (tag === 'INPUT' || tag === 'LABEL') return;
                  setOpenCard(c);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') setOpenCard(c);
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(c.id)}
                  onChange={() => toggleSelect(c.id)}
                  onClick={(e) => e.stopPropagation()}
                />
                <div className="fpCardItemBody">
                  <div className="fpCardItemTitle">{c.title}</div>
                  <div className="fpCardItemMeta">{c.meta}</div>
                </div>
                <button type="button" className="fpCardOpen" onClick={() => setOpenCard(c)}>
                  查看
                </button>
              </div>
            ))}
            {cards.length === 0 && <div className="fpEmpty">暂无卡片。可从 Markdown 选中内容或按标题拆分生成。</div>}
          </div>
        </div>
      </div>
      {previewSelection.open && (
        <div className="fpSelBar" style={{ left: previewSelection.x, top: previewSelection.y }}>
          <button
            type="button"
            className="fpSelBtn"
            onClick={() => {
              const ok = appendToDraft(previewSelection.text, previewSelection.text.split(/\r?\n/).find((l) => l.trim()) || '');
              if (ok) showToast('已追加到卡片草稿');
              setPreviewSelection({ open: false, text: '', x: 0, y: 0 });
            }}
          >
            加入草稿
          </button>
          <button
            type="button"
            className="fpSelBtn fpSelBtnPrimary"
            onClick={() => {
              const title = previewSelection.text.split(/\r?\n/).find((l) => l.trim())?.trim().slice(0, 24) || '知识卡片';
              const card = { id: createId(), title, meta: '从预览选中生成', content: previewSelection.text };
              setCards((prev) => [card].concat(prev));
              setSelectedIds((prev) => new Set(prev).add(card.id));
              setPreviewSelection({ open: false, text: '', x: 0, y: 0 });
            }}
          >
            生成卡片
          </button>
        </div>
      )}
      {!!toast && (
        <div className="fpToast" role="status" aria-live="polite">
          {toast}
        </div>
      )}
      {!!openCard && (
        <div className="fpModalMask" role="dialog" aria-modal="true">
          <div className="fpModal">
            <div className="fpModalHeader">
              <div className="fpModalTitle">{openCard.title || '知识卡片'}</div>
              <button type="button" className="fpModalX" onClick={() => setOpenCard(null)}>×</button>
            </div>
            <div className="fpModalBody">
              <ChatMarkdown content={openCard.content || ''} />
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}
