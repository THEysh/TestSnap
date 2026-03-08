import { API_BASE_URL, API_ROOT_URL } from '../../../constants/apiConfig';

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function normalizeCardFromJson(obj) {
  if (!obj || typeof obj !== 'object') return null;
  const title = String(obj.title || '').trim();
  const kp = Array.isArray(obj.knowledge_points) ? obj.knowledge_points.map((x) => String(x || '').trim()).filter(Boolean) : [];
  const exQ = String(obj.example?.question || '').trim();
  const exA = String(obj.example?.analysis || '').trim();
  const summary = String(obj.summary || '').trim();
  if (!title && kp.length === 0 && !exQ && !summary) return null;
  const md = [
    `# ${title || '学习卡片'}`,
    '',
    '## 知识点',
    ...(kp.length ? kp.map((x) => `- ${x}`) : ['- （暂无）']),
    '',
    '## 例题',
    '',
    '题目：',
    '',
    exQ || '（暂无）',
    '',
    '解析：',
    '',
    exA || '（暂无）',
    '',
    '## 总结',
    '',
    summary || '（暂无）'
  ].join('\n');
  return { title: title || '学习卡片', markdown: md };
}

function normalizeMarkdownResult(markdown) {
  const md = String(markdown || '').trim();
  if (!md) return null;
  const m = md.match(/^#\s+(.+)\s*$/m);
  const title = m ? String(m[1] || '').trim() : '学习卡片';
  return { title, markdown: md };
}

export async function generateLearningCard({ userId, messages, modelName }) {
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
    `${API_ROOT_URL}/generate_card`,
    `${API_BASE_URL}/generate_card`,
    '/generate_card',
    '/api/generate_card'
  ]));

  for (let i = 0; i < endpoints.length; i++) {
    const url = endpoints[i];
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body
      });
      const contentType = String(res.headers.get('content-type') || '').toLowerCase();
      const text = await res.text();
      if (!res.ok) throw new Error(text || `HTTP ${res.status}`);

      if (contentType.includes('application/json')) {
        const data = safeJsonParse(text, null);
        const maybe = data?.data && typeof data.data === 'object' ? data.data : data;
        if (data?.success === false) throw new Error(String(data?.error || '生成学习卡片失败'));
        const fromJson = normalizeCardFromJson(maybe);
        if (fromJson) return { ok: true, ...fromJson };
        const md = String(maybe?.markdown || maybe?.content || maybe?.card || maybe?.card_md || '').trim();
        const fromMd = normalizeMarkdownResult(md);
        if (fromMd) return { ok: true, ...fromMd };
        throw new Error('返回数据格式不正确');
      }

      const fromMd = normalizeMarkdownResult(text);
      if (fromMd) return { ok: true, ...fromMd };
      throw new Error('返回内容为空');
    } catch (e) {
      if (i === endpoints.length - 1) return { ok: false, error: String(e || '生成学习卡片失败') };
    }
  }
  return { ok: false, error: '生成学习卡片失败' };
}

