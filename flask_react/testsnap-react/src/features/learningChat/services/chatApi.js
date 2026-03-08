import { API_BASE_URL } from '../../../constants/apiConfig';

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

export async function streamChatAPI(payload, onChunk, signal) {
  const endpoints = Array.from(new Set([
    `${API_BASE_URL}/chat/stream`,
    '/api/chat/stream'
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
        body: JSON.stringify(payload),
        signal
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      if (!res.body) throw new Error('无可读流');
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      const handleEvent = (evt) => {
        const dataLines = extractDataLines(evt);
        if (dataLines.length === 0) return false;
        const payloadStr = dataLines.join('\n');
        if (payloadStr === '[DONE]') return true;
        let piece = '';
        try {
          const obj = JSON.parse(payloadStr);
          if (obj && typeof obj === 'object') {
            if (obj.type && obj.content) {
              if (onChunk) onChunk({ type: obj.type, content: obj.content });
              return false;
            }
            piece = obj.delta || obj.content || obj.text || obj.message || '';
            if (!piece && Array.isArray(obj.choices) && obj.choices[0]?.delta?.content) {
              piece = obj.choices[0].delta.content;
            }
          }
        } catch {
          piece = '';
        }
        if (!piece) piece = payloadStr;
        if (onChunk) onChunk(piece);
        return false;
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
            const isDone = handleEvent(event);
            if (isDone) return { success: true };
          }
        }
      } finally {
        try {
          reader.releaseLock();
        } catch {
          void 0;
        }
      }
      return { success: true };
    } catch (e) {
      if (i === endpoints.length - 1) return { success: false, error: String(e) };
    }
  }
  return { success: false, error: '未知错误' };
}
