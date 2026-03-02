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

  // 渲染Markdown内容
  const renderMarkdown = (input) => {
    if (!previewRef.current || !window.marked) {
      return;
    }

    // 保护数学公式不被解析器处理
    let tempStorage = [];
    let tempIndex = 0;

    // 保护块级公式
    let protectedInput = input.replace(/\$\$[\s\S]*?\$\$/g, function(match) {
      const placeholder = `MATH_BLOCK_${tempIndex}`;
      tempStorage[tempIndex] = match;
      tempIndex++;
      return placeholder;
    });

    // 保护行内公式
    protectedInput = protectedInput.replace(/\$(?!\$)([^\$\n]+?)\$/g, function(match) {
      const placeholder = `MATH_INLINE_${tempIndex}`;
      tempStorage[tempIndex] = match;
      tempIndex++;
      return placeholder;
    });

    // 使用marked解析Markdown
    let html = window.marked.parse(protectedInput);

    // 恢复数学公式
    html = html.replace(/MATH_BLOCK_(\d+)/g, function(match, index) {
      return tempStorage[parseInt(index)];
    });

    html = html.replace(/MATH_INLINE_(\d+)/g, function(match, index) {
      return tempStorage[parseInt(index)];
    });

    // 更新预览
    previewRef.current.innerHTML = html;

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
  const selector = [
    'h1','h2','h3','h4','h5','h6',
    'p','table','pre','blockquote','img'
  ].join(',');
  const nodes = root.querySelectorAll(selector);
  nodes.forEach((node) => {
    if (node.dataset && node.dataset.chatEnhanced === '1') return;
    const wrapper = document.createElement('div');
    wrapper.className = 'chat-enhanced-wrap';
    wrapper.title = '加入聊天框';
    node.parentNode.insertBefore(wrapper, node);
    wrapper.appendChild(node);
    wrapper.addEventListener('click', (e) => {
      // 避免在选中文本时误触
      const selection = window.getSelection ? window.getSelection().toString() : '';
      if (selection && selection.length > 0) return;
      const tag = node.tagName.toLowerCase();
      const type = tag === 'img' ? 'image' : tag === 'table' ? 'table' : 'text';
      const payload = {
        tag,
        type,
        text: type === 'text' ? (node.innerText || '').trim().slice(0, 2000) : undefined,
        html: type !== 'text' ? node.outerHTML : undefined,
      };
      enqueueBlock(payload);
      const url = (typeof window !== 'undefined')
        ? (window.location.origin + window.location.pathname + '#/chat?new=1')
        : '#/chat?new=1';
      // 使用具名窗口，复用已开启的聊天页
      window.open(url, 'TextSnapChat');
      e.stopPropagation();
    });
    node.dataset.chatEnhanced = '1';
  });
}

export default useMarkdownRenderer;
