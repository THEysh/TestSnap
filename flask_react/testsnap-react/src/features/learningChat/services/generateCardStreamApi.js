import { API_BASE_URL, API_ROOT_URL } from '../../../constants/apiConfig';

function readSep(buffer) {
  const nn = buffer.indexOf('\n\n');
  const rr = buffer.indexOf('\r\n\r\n');
  if (nn === -1 && rr === -1) return { idx: -1, len: 0 };
  if (nn === -1) return { idx: rr, len: 4 };
  if (rr === -1) return { idx: nn, len: 2 };
  return nn < rr ? { idx: nn, len: 2 } : { idx: rr, len: 4 };
}

function extractDataLines(evt) {
  const lines = String(evt || '').split(/\r?\n/);
  const dataLines = lines
    .filter((l) => l.trimStart().startsWith('data:'))
    .map((l) => {
      const p = l.indexOf('data:');
      const rest = l.slice(p + 5);
      return rest.startsWith(' ') ? rest.slice(1) : rest;
    });
  return dataLines;
}

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

export async function streamGenerateLearningCard({ userId, messages, modelName, onChunk, signal }) {
  const normalizedMessages = (messages || [])
    .filter((m) => m && (m.role === 'user' || m.role === 'assistant'))
    .map((m) => ({ role: m.role, content: String(m.content || '') }))
    .filter((m) => m.content.trim());

  const chatText = normalizedMessages
    .map((m) => `${m.role === 'user' ? '用户' : 'AI'}：${m.content}`)
    .join('\n\n');

  const body = JSON.stringify({
    user_id: userId || null,
    messages: normalizedMessages,
    chat: chatText,
    model_name: modelName || null
  });

  const endpoints = Array.from(new Set([
    `${API_ROOT_URL}/generate_card/stream`,
    `${API_BASE_URL}/generate_card/stream`,
    '/generate_card/stream',
    '/api/generate_card/stream'
  ]));

  for (let i = 0; i < endpoints.length; i++) {
    const url = endpoints[i];
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache'
        },
        body,
        signal
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error('无可读流');
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      const handleEvent = (evt) => {
        const dataLines = extractDataLines(evt);
        if (dataLines.length === 0) return { done: false };
        const payloadStr = dataLines.join('\n');
        if (payloadStr === '[DONE]') return { done: true };
        const obj = safeJsonParse(payloadStr, null);
        if (obj && typeof obj === 'object') {
          if (obj.type === 'delta') {
            onChunk?.({ type: 'delta', content: String(obj.content || '') });
            return { done: false };
          }
          if (obj.type === 'error') {
            onChunk?.({ type: 'error', content: String(obj.content || obj.error || '') });
            return { done: false };
          }
        }
        onChunk?.({ type: 'delta', content: String(payloadStr || '') });
        return { done: false };
      };

      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          while (true) {
            const { idx, len } = readSep(buffer);
            if (idx === -1) break;
            const event = buffer.slice(0, idx);
            buffer = buffer.slice(idx + len);
            const ret = handleEvent(event);
            if (ret.done) return { ok: true };
          }
        }
      } finally {
        try {
          reader.releaseLock();
        } catch {
          void 0;
        }
      }
      return { ok: true };
    } catch (e) {
      if (i === endpoints.length - 1) return { ok: false, error: String(e || '生成学习卡片失败') };
    }
  }
  return { ok: false, error: '生成学习卡片失败' };
}
