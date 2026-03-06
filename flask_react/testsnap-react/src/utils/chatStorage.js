// 简单的本地持久化存储，管理会话与临时加入队列
const QUEUE_KEY = 'textsnap_chat_queue';
const CONV_KEY = 'textsnap_chat_conversations';
const TARGET_KEY = 'textsnap_chat_target';
const HEARTBEAT_KEY = 'textsnap_chat_heartbeat';
const AUTO_OPEN_KEY = 'textsnap_chat_auto_open';
const PENDING_COUNT_KEY = 'textsnap_chat_pending_count';

export function getQueueLength() {
  try {
    const list = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
    return Array.isArray(list) ? list.length : 0;
  } catch {
    return 0;
  }
}

export function getChatHeartbeat() {
  const raw = localStorage.getItem(HEARTBEAT_KEY);
  const n = raw ? Number(raw) : 0;
  return Number.isFinite(n) ? n : 0;
}

export function setChatHeartbeat(ts) {
  const n = typeof ts === 'number' ? ts : Date.now();
  localStorage.setItem(HEARTBEAT_KEY, String(n));
}

export function getChatAutoOpen() {
  const raw = localStorage.getItem(AUTO_OPEN_KEY);
  if (raw === null) return true;
  return raw === '1';
}

export function setChatAutoOpen(value) {
  localStorage.setItem(AUTO_OPEN_KEY, value ? '1' : '0');
}

export function getChatPendingCount() {
  const raw = localStorage.getItem(PENDING_COUNT_KEY);
  const n = raw ? Number(raw) : 0;
  return Number.isFinite(n) ? n : 0;
}

export function setChatPendingCount(count) {
  const n = typeof count === 'number' ? count : Number(count);
  localStorage.setItem(PENDING_COUNT_KEY, String(Number.isFinite(n) ? n : 0));
}

export function enqueueBlock(payload) {
  const list = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  const targetConvId = localStorage.getItem(TARGET_KEY) || null;
  list.push({
    id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    convId: targetConvId,
    ...payload,
    createdAt: Date.now(),
  });
  localStorage.setItem(QUEUE_KEY, JSON.stringify(list));
  try {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('textsnap_chat_queue_updated'));
    }
  } catch {
    void 0;
  }
}

export function consumeQueue() {
  const list = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  localStorage.removeItem(QUEUE_KEY);
  return list;
}

export function getConversations() {
  return JSON.parse(localStorage.getItem(CONV_KEY) || '[]');
}

export function saveConversations(convs) {
  localStorage.setItem(CONV_KEY, JSON.stringify(convs));
}

export function createConversation({ title = '新对话', initialMessages = [] } = {}) {
  const convs = getConversations();
  const conv = {
    id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    title,
    createdAt: Date.now(),
    messages: Array.isArray(initialMessages) ? initialMessages : []
  };
  convs.unshift(conv);
  saveConversations(convs);
  return conv;
}

export function addMessage(convId, message) {
  const convs = getConversations();
  const idx = convs.findIndex(c => c.id === convId);
  if (idx === -1) return null;
  convs[idx].messages.push({
    id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    role: message.role,
    content: message.content,
    meta: message.meta || {},
    createdAt: Date.now()
  });
  saveConversations(convs);
  return convs[idx];
}

export function deleteConversation(convId) {
  const convs = getConversations().filter(c => c.id !== convId);
  saveConversations(convs);
  return convs;
}

export function setTargetConversation(convId) {
  if (convId) {
    localStorage.setItem(TARGET_KEY, convId);
  } else {
    localStorage.removeItem(TARGET_KEY);
  }
}

export function updateLastAssistantMessage(convId, appendText) {
  const convs = getConversations();
  const idx = convs.findIndex(c => c.id === convId);
  if (idx === -1) return null;
  const msgs = convs[idx].messages || [];
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') {
      msgs[i].content = (msgs[i].content || '') + appendText;
      break;
    }
  }
  saveConversations(convs);
  return convs[idx];
}

export function updateLastAssistantReasoning(convId, appendText) {
  const convs = getConversations();
  const idx = convs.findIndex(c => c.id === convId);
  if (idx === -1) return null;
  const msgs = convs[idx].messages || [];
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'assistant') {
      const meta = msgs[i].meta || {};
      meta.reasoning = (meta.reasoning || '') + appendText;
      msgs[i].meta = meta;
      break;
    }
  }
  saveConversations(convs);
  return convs[idx];
}

