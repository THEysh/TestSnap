import React, { useEffect } from 'react';
import useMarkdownRenderer from '../hooks/useMarkdownRenderer';

export default function ChatMarkdown({ content }) {
  const { previewRef, renderMarkdown } = useMarkdownRenderer();
  useEffect(() => {
    renderMarkdown(content || '');
  }, [content]);
  return <div className="chat-md" ref={previewRef} />;
}
