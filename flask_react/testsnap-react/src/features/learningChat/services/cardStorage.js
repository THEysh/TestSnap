function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function normalizeCard(card) {
  if (!card) return null;
  const id = String(card.id || '').trim();
  const title = String(card.title || '').trim() || '知识卡片';
  const content = String(card.content || '');
  const meta = String(card.meta || '').trim();
  if (!id) return null;
  return { id, title, content, meta };
}

function notifyCardLibraryUpdated(userId) {
  if (typeof window === 'undefined') return;
  try {
    window.dispatchEvent(new CustomEvent('ts_card_library_updated', { detail: { userId: String(userId || '') } }));
  } catch {
    return;
  }
}

export function loadCardLibrary(userId) {
  if (typeof window === 'undefined') return [];
  const key = `ts_card_library_${userId}`;
  const raw = window.localStorage.getItem(key);
  const list = safeJsonParse(raw, []);
  if (!Array.isArray(list)) return [];
  return list.map(normalizeCard).filter(Boolean);
}

export function appendToCardLibrary(userId, cards) {
  if (typeof window === 'undefined') return { ok: false };
  const key = `ts_card_library_${userId}`;
  const current = loadCardLibrary(userId);
  const existing = new Set(current.map((c) => String(c.id)));
  const incoming = (cards || []).map(normalizeCard).filter(Boolean).filter((c) => !existing.has(String(c.id)));
  const next = incoming.concat(current);
  window.localStorage.setItem(key, JSON.stringify(next));
  notifyCardLibraryUpdated(userId);
  return { ok: true, count: incoming.length };
}

export function saveCardLibrary(userId, cards) {
  if (typeof window === 'undefined') return { ok: false };
  const key = `ts_card_library_${userId}`;
  const list = (cards || []).map(normalizeCard).filter(Boolean);
  window.localStorage.setItem(key, JSON.stringify(list));
  notifyCardLibraryUpdated(userId);
  return { ok: true, count: list.length };
}

export function removeFromCardLibrary(userId, cardId) {
  if (typeof window === 'undefined') return { ok: false };
  const current = loadCardLibrary(userId);
  const next = current.filter((c) => String(c.id) !== String(cardId));
  return saveCardLibrary(userId, next);
}

export function enqueueCardsToChat(userId, cards) {
  if (typeof window === 'undefined') return { ok: false };
  const key = `ts_chat_context_queue_${userId}`;
  const raw = window.localStorage.getItem(key);
  const current = safeJsonParse(raw, []);
  const base = Array.isArray(current) ? current : [];
  const incoming = (cards || []).map(normalizeCard).filter(Boolean);
  const next = base.concat(incoming);
  window.localStorage.setItem(key, JSON.stringify(next));
  return { ok: true, count: incoming.length };
}
