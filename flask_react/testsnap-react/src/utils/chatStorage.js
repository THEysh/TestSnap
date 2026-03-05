// 简单的本地持久化存储，管理会话与临时加入队列
const QUEUE_KEY = 'textsnap_chat_queue';
const CONV_KEY = 'textsnap_chat_conversations';
const TARGET_KEY = 'textsnap_chat_target';

export function enqueueBlock(payload) {
  const list = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  const targetConvId = localStorage.getItem(TARGET_KEY) || null;
  list.push({
    id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    convId: targetConvId,
    ...payload,
    createdAt: Date.now(),
  });
  const newValue = JSON.stringify(list);
  localStorage.setItem(QUEUE_KEY, newValue);
  
  // 必须手动触发 storage 事件，因为同窗口（同源同页）下 setItem 不会触发 window.onstorage
  window.dispatchEvent(new StorageEvent('storage', {
    key: QUEUE_KEY,
    newValue: newValue,
    url: window.location.href,
    storageArea: localStorage
  }));
}

let memQueue = null;
let memTimer = null;

export function consumeQueue() {
  const list = JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]');
  if (list && list.length > 0) {
    localStorage.removeItem(QUEUE_KEY);
    // 为了应对 React StrictMode 下 useEffect 执行两次的问题，
    // 我们将取出的数据暂存在内存中一小段时间
    memQueue = list;
    if (memTimer) clearTimeout(memTimer);
    memTimer = setTimeout(() => { memQueue = null; }, 500);
    return list;
  }
  // 如果 localStorage 为空，尝试返回内存中的暂存数据
  if (memQueue) {
    return memQueue;
  }
  return [];
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

