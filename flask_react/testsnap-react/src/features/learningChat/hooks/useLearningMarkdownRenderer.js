import { useEffect, useRef } from 'react';
import { debounce } from '../../../utils/debounce';

export default function useLearningMarkdownRenderer() {
  const previewRef = useRef(null);

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

  const renderMarkdown = (input) => {
    if (!previewRef.current || !window.marked) return;
    let html = '';
    try {
      html = window.marked.parse(input || '');
    } catch {
      html = window.marked.parse(String(input || ''));
    }
    previewRef.current.innerHTML = html;
    if (typeof window !== 'undefined' && window.MathJax) {
      try {
        window.MathJax.typesetPromise([previewRef.current]);
      } catch {
        return;
      }
    }
  };

  const debouncedRender = debounce(renderMarkdown, 150);

  return { previewRef, renderMarkdown, debouncedRender };
}

