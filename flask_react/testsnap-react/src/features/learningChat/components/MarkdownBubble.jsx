import React, { useEffect } from 'react';
import useLearningMarkdownRenderer from '../hooks/useLearningMarkdownRenderer';
import '../learningChat.css';

export default function MarkdownBubble({ markdown }) {
  const { previewRef, renderMarkdown } = useLearningMarkdownRenderer();

  useEffect(() => {
    renderMarkdown(markdown || '');
  }, [markdown, renderMarkdown]);

  return (
    <div className="lcMarkdown" ref={previewRef} />
  );
}
