// src/hooks/useMarkdownRenderer.js
import { useEffect, useRef } from 'react';
import { debounce } from '../utils/debounce';
import { enqueueBlock, getChatAutoOpen, getChatHeartbeat, getChatPendingCount, getQueueLength, setChatAutoOpen } from '../utils/chatStorage';

const useMarkdownRenderer = () => {
  const previewRef = useRef(null);
  
  // 配置marked解析器
  useEffect(() => {
    if (typeof window !== 'undefined' && window.marked) {
      const renderer = new window.marked.Renderer();
      window.marked.setOptions({
        renderer,
        gfm: true,
        breaks: true,
        sanitize: true,
        smartLists: true,
        xhtml: false
      });
    }
  }, []);

  // 渲染Markdown内容（按块渲染并为每块绑定原始Markdown，便于后续携带rawMd）
  const renderMarkdown = (input) => {
    if (!previewRef.current || !window.marked) {
      return;
    }
    const blocks = splitMdBlocks(input || '');
    const parts = [];
    for (let i = 0; i < blocks.length; i++) {
      const raw = blocks[i];
      const normalizedRaw = normalizeMathDelimiters(raw);
      let frag = '';
      try {
        frag = window.marked.parse(normalizedRaw);
      } catch {
        frag = window.marked.parse(normalizedRaw || '');
      }
      parts.push(`<div class="md-block" data-raw-md="${encodeURIComponent(raw)}">${frag}</div>`);
    }
    previewRef.current.innerHTML = parts.join('\n');
    // 触发MathJax重新渲染
    if (window.MathJax) {
      window.MathJax.typesetPromise([previewRef.current]).catch(function(err) {
        console.log('MathJax渲染错误: ', err);
      });
    }
    enhanceBlocks(previewRef.current);
  };

  // 创建防抖版本的渲染函数
  const debouncedRender = debounce(renderMarkdown, 300);

  useEffect(() => {
    const refresh = () => updateChatLauncher();
    refresh();
    window.addEventListener('storage', refresh);
    window.addEventListener('textsnap_chat_queue_updated', refresh);
    return () => {
      window.removeEventListener('storage', refresh);
      window.removeEventListener('textsnap_chat_queue_updated', refresh);
    };
  }, []);

  return {
    previewRef,
    renderMarkdown,
    debouncedRender
  };
};

const LAUNCHER_ID = 'textsnap_chat_launcher';

function getChatUrl() {
  return (typeof window !== 'undefined')
    ? (window.location.origin + window.location.pathname + '#/chat?new=1')
    : '#/chat?new=1';
}

function openChatWindow() {
  const url = getChatUrl();
  window.open(url, 'TextSnapChat');
}

function isChatAlive() {
  try {
    const hb = getChatHeartbeat();
    return hb > 0 && (Date.now() - hb) < 15000;
  } catch {
    return false;
  }
}

function ensureChatLauncher() {
  if (typeof document === 'undefined') return null;
  const existing = document.getElementById(LAUNCHER_ID);
  if (existing) return existing;

  const el = document.createElement('div');
  el.id = LAUNCHER_ID;
  el.className = 'textsnap-chat-launcher';
  el.innerHTML = `
    <div class="textsnap-chat-launcher-row">
      <div class="textsnap-chat-launcher-title">卡片队列</div>
      <div class="textsnap-chat-launcher-count" data-role="count">0</div>
    </div>
    <div class="textsnap-chat-launcher-row">
      <button class="textsnap-chat-launcher-open" type="button" data-role="open">打开聊天</button>
      <label class="textsnap-chat-launcher-toggle">
        <input type="checkbox" data-role="autoOpen" />
        <span>自动打开</span>
      </label>
    </div>
  `.trim();
  document.body.appendChild(el);

  const openBtn = el.querySelector('[data-role="open"]');
  if (openBtn) {
    openBtn.addEventListener('click', () => openChatWindow());
  }
  const autoOpen = el.querySelector('[data-role="autoOpen"]');
  if (autoOpen) {
    autoOpen.addEventListener('change', (e) => {
      const checked = !!e.target?.checked;
      try {
        setChatAutoOpen(checked);
      } catch {
        return;
      }
      updateChatLauncher();
    });
  }

  return el;
}

function updateChatLauncher() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  const el = ensureChatLauncher();
  if (!el) return;

  let queuedCount = 0;
  try {
    queuedCount = getQueueLength();
  } catch {
    queuedCount = 0;
  }

  let pendingCount = 0;
  if (isChatAlive()) {
    try {
      pendingCount = getChatPendingCount();
    } catch {
      pendingCount = 0;
    }
  }
  const displayCount = pendingCount + queuedCount;

  const countEl = el.querySelector('[data-role="count"]');
  if (countEl) countEl.textContent = String(displayCount);

  const autoOpen = el.querySelector('[data-role="autoOpen"]');
  if (autoOpen) {
    try {
      autoOpen.checked = !!getChatAutoOpen();
    } catch {
      autoOpen.checked = true;
    }
  }

  const hash = window.location.hash || '';
  const show = !hash.startsWith('#/chat');
  el.style.display = show ? 'flex' : 'none';
  el.classList.toggle('is-idle', displayCount === 0);
}

function enhanceBlocks(root) {
  if (!root) return;
  const nodes = root.querySelectorAll('.md-block');
  nodes.forEach((node) => {
    if (node.dataset && node.dataset.chatEnhanced === '1') return;
    node.classList.add('chat-enhanced-wrap');
    node.title = '加入聊天框';
    node.addEventListener('click', (e) => {
      const selection = window.getSelection ? window.getSelection().toString() : '';
      if (selection && selection.length > 0) return;
      const hasImg = !!node.querySelector('img');
      const hasTable = !!node.querySelector('table');
      const type = hasImg ? 'image' : hasTable ? 'table' : 'text';
      const tag = hasImg ? 'img' : hasTable ? 'table' : 'p';
      let rawMd = '';
      try { rawMd = decodeURIComponent(node.getAttribute('data-raw-md') || ''); } catch { rawMd = ''; }
      const payload = {
        tag,
        type,
        rawMd,
        text: (node.textContent || '').trim().slice(0, 2000),
        html: node.innerHTML
      };
      enqueueBlock(payload);
      updateChatLauncher();
      const hash = typeof window !== 'undefined' ? (window.location.hash || '') : '';
      if (!hash.startsWith('#/chat')) {
        let autoOpen = true;
        try {
          autoOpen = !!getChatAutoOpen();
        } catch {
          autoOpen = true;
        }
        if (autoOpen && !isChatAlive()) {
          openChatWindow();
        }
      }
      e.stopPropagation();
    });
    node.dataset.chatEnhanced = '1';
  });
}

function splitMdBlocks(src) {
  const lines = src.split(/\r?\n/);
  const blocks = [];
  let buf = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^(```+|~~~+)/);
    if (fenceMatch) {
      if (!inFence) {
        inFence = true;
      } else {
        inFence = false;
      }
      buf.push(line);
      continue;
    }
    if (!inFence && line.trim() === '') {
      if (buf.length) {
        blocks.push(buf.join('\n'));
        buf = [];
      }
      continue;
    }
    buf.push(line);
  }
  if (buf.length) blocks.push(buf.join('\n'));
  return blocks;
}

function normalizeMathDelimiters(src) {
  const lines = src.split(/\r?\n/);
  const out = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^(```+|~~~+)/);
    if (fenceMatch) {
      inFence = !inFence;
      out.push(line);
      continue;
    }
    if (inFence) {
      out.push(line);
      continue;
    }
    const replaced = line
      .replace(/\\\[/g, '$$')
      .replace(/\\\]/g, '$$')
      .replace(/\\\(/g, '$')
      .replace(/\\\)/g, '$');
    out.push(replaced);
  }
  return out.join('\n');
}

export default useMarkdownRenderer;
