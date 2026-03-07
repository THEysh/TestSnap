import { useEffect, useMemo, useRef } from 'react';
import { debounce } from '../utils/debounce';

function splitMdBlocks(src) {
  const lines = String(src || '').split(/\r?\n/);
  const blocks = [];
  let buf = [];
  let inFence = false;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const fenceMatch = line.match(/^(```+|~~~+)/);
    if (fenceMatch) {
      inFence = !inFence;
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
  const lines = String(src || '').split(/\r?\n/);
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
    out.push(line.replace(/\\\[/g, '$$').replace(/\\\]/g, '$$'));
  }
  return out.join('\n');
}

function isSelectionInsideNode(node) {
  try {
    const sel = window.getSelection?.();
    if (!sel || sel.rangeCount === 0) return false;
    const range = sel.getRangeAt(0);
    if (!range) return false;
    if (range.collapsed) return false;
    const container = range.commonAncestorContainer;
    const el = container?.nodeType === 1 ? container : container?.parentElement;
    if (!el || !node) return false;
    return node.contains(el);
  } catch {
    return false;
  }
}

function enhanceBlocks(root, getOnBlockClick) {
  if (!root) return;
  const nodes = root.querySelectorAll('.md-block');
  nodes.forEach((node) => {
    if (node.dataset && node.dataset.blockEnhanced === '1') return;
    node.classList.add('fp-md-block');
    node.addEventListener('click', (e) => {
      if (isSelectionInsideNode(node)) return;
      let rawMd = '';
      try {
        rawMd = decodeURIComponent(node.getAttribute('data-raw-md') || '');
      } catch {
        rawMd = '';
      }
      const payload = {
        rawMd,
        text: (node.textContent || '').trim().slice(0, 5000),
        html: node.innerHTML
      };
      const onBlockClick = getOnBlockClick ? getOnBlockClick() : null;
      if (onBlockClick) onBlockClick(payload);
      e.stopPropagation();
    });
    node.dataset.blockEnhanced = '1';
  });
}

export default function useBlockMarkdownRenderer({ onBlockClick } = {}) {
  const previewRef = useRef(null);
  const onBlockClickRef = useRef(null);

  useEffect(() => {
    onBlockClickRef.current = onBlockClick || null;
  }, [onBlockClick]);

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

  const renderMarkdown = useMemo(() => {
    return (input) => {
      if (!previewRef.current || !window.marked) return;
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
      if (window.MathJax) {
        try {
          window.MathJax.typesetPromise([previewRef.current]);
        } catch {
          void 0;
        }
      }
      enhanceBlocks(previewRef.current, () => onBlockClickRef.current);
    };
  }, []);

  const debouncedRender = useMemo(() => debounce(renderMarkdown, 150), [renderMarkdown]);

  return { previewRef, renderMarkdown, debouncedRender };
}
