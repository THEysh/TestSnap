const USERS_KEY = 'ts_users_v1';
const SESSION_KEY = 'ts_session_v1';

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function loadUsers() {
  if (typeof window === 'undefined') return [];
  const raw = window.localStorage.getItem(USERS_KEY);
  const users = safeJsonParse(raw, []);
  return Array.isArray(users) ? users : [];
}

function saveUsers(users) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(USERS_KEY, JSON.stringify(users));
}

function loadSession() {
  if (typeof window === 'undefined') return null;
  const raw = window.localStorage.getItem(SESSION_KEY);
  return safeJsonParse(raw, null);
}

function saveSession(session) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function clearSession() {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(SESSION_KEY);
}

function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

async function sha256(text) {
  const input = String(text || '');
  if (typeof window === 'undefined') return input;
  const cryptoObj = window.crypto;
  if (!cryptoObj?.subtle) return input;
  const encoder = new TextEncoder();
  const data = encoder.encode(input);
  const digest = await cryptoObj.subtle.digest('SHA-256', data);
  const bytes = Array.from(new Uint8Array(digest));
  return bytes.map((b) => b.toString(16).padStart(2, '0')).join('');
}

function createId() {
  const base = `${Date.now()}_${Math.random().toString(16).slice(2)}`;
  return base.replaceAll('.', '');
}

export async function signUp({ name, email, password }) {
  const n = String(name || '').trim();
  const e = normalizeEmail(email);
  const p = String(password || '');
  if (!n) return { ok: false, error: '请输入昵称' };
  if (!e || !e.includes('@')) return { ok: false, error: '请输入有效邮箱' };
  if (p.length < 6) return { ok: false, error: '密码至少 6 位' };

  const users = loadUsers();
  if (users.some((u) => normalizeEmail(u.email) === e)) {
    return { ok: false, error: '该邮箱已注册' };
  }

  const passwordHash = await sha256(p);
  const user = {
    id: createId(),
    name: n,
    email: e,
    passwordHash,
    createdAt: Date.now()
  };
  users.push(user);
  saveUsers(users);
  const session = { userId: user.id, createdAt: Date.now() };
  saveSession(session);
  return { ok: true, user: { id: user.id, name: user.name, email: user.email } };
}

export async function signIn({ email, password }) {
  const e = normalizeEmail(email);
  const p = String(password || '');
  if (!e || !e.includes('@')) return { ok: false, error: '请输入有效邮箱' };
  if (!p) return { ok: false, error: '请输入密码' };

  const users = loadUsers();
  const user = users.find((u) => normalizeEmail(u.email) === e);
  if (!user) return { ok: false, error: '账号或密码错误' };
  const passwordHash = await sha256(p);
  if (String(user.passwordHash || '') !== passwordHash) {
    return { ok: false, error: '账号或密码错误' };
  }
  const session = { userId: user.id, createdAt: Date.now() };
  saveSession(session);
  return { ok: true, user: { id: user.id, name: user.name, email: user.email } };
}

export function signOut() {
  clearSession();
  return { ok: true };
}

export function getCurrentUser() {
  const session = loadSession();
  if (!session?.userId) return null;
  const users = loadUsers();
  const user = users.find((u) => String(u.id) === String(session.userId));
  if (!user) return null;
  return { id: user.id, name: user.name, email: user.email };
}

