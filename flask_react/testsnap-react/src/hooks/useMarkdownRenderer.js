// src/hooks/useMarkdownRenderer.js
import { useEffect, useRef } from 'react';
import { debounce } from '../utils/debounce';

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
  };

  // 创建防抖版本的渲染函数
  const debouncedRender = debounce(renderMarkdown, 300);

  return {
    previewRef,
    renderMarkdown,
    debouncedRender
  };
};

export default useMarkdownRenderer;