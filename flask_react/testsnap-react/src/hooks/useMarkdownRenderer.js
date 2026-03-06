// src/hooks/useMarkdownRenderer.js
import { useEffect, useRef } from 'react';
import { debounce } from '../utils/debounce';
import { enqueueBlock } from '../utils/chatStorage';

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
      } catch (e) {
        frag = window.marked.parse(normalizedRaw || '');
      }
      parts.push(`<div class="md-block" data-raw-md="${encodeURIComponent(raw)}">${frag}</div>`);
    }
    previewRef.current.innerHTML = parts.join('\n');
    // 触发MathJax重新渲染
    if (window.MathJax) {
      MathJax.typesetPromise([previewRef.current]).catch(function(err) {
        console.log('MathJax渲染错误: ', err);
      });
    }
    enhanceBlocks(previewRef.current);
  };

  // 创建防抖版本的渲染函数
  const debouncedRender = debounce(renderMarkdown, 300);

  return {
    previewRef,
    renderMarkdown,
    debouncedRender
  };
};

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
      try { rawMd = decodeURIComponent(node.getAttribute('data-raw-md') || ''); } catch (e) {}
      const payload = {
        tag,
        type,
        rawMd,
        text: (node.textContent || '').trim().slice(0, 2000),
        html: node.innerHTML
      };
      enqueueBlock(payload);
      const hash = typeof window !== 'undefined' ? (window.location.hash || '') : '';
      if (!hash.startsWith('#/chat')) {
        const url = (typeof window !== 'undefined')
          ? (window.location.origin + window.location.pathname + '#/chat?new=1')
          : '#/chat?new=1';
        window.open(url, 'TextSnapChat');
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
  let fenceMarker = '';
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^(```+|~~~+)/);
    if (fenceMatch) {
      if (!inFence) {
        inFence = true;
        fenceMarker = fenceMatch[1][0];
      } else {
        inFence = false;
        fenceMarker = '';
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
