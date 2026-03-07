import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import useAuth from '../app/auth/useAuth';
import AppShell from '../app/shell/AppShell';
import './dashboard.css';

function getGreeting() {
  const h = new Date().getHours();
  if (h < 6) return '凌晨好';
  if (h < 12) return '早安';
  if (h < 18) return '下午好';
  return '晚上好';
}

function pickRandom(list) {
  const arr = Array.isArray(list) ? list : [];
  if (arr.length === 0) return '';
  return arr[Math.floor(Math.random() * arr.length)];
}

function createId() {
  return `${Date.now()}_${Math.random().toString(16).slice(2)}`.replaceAll('.', '');
}

function safeJsonParse(value, fallback) {
  try {
    const parsed = JSON.parse(value);
    return parsed ?? fallback;
  } catch {
    return fallback;
  }
}

function getGoalTodosKey(userId) {
  return `ts_dash_goal_todos_${userId}`;
}

function getSuggestTodosKey(userId) {
  return `ts_dash_suggest_todos_${userId}`;
}

function getDashStateKey(userId) {
  return `ts_dash_state_${userId}`;
}

function loadDashState(userId) {
  try {
    const raw = window.localStorage.getItem(getDashStateKey(userId));
    const data = safeJsonParse(raw, null);
    if (!data || typeof data !== 'object') return null;
    return {
      mood: typeof data.mood === 'string' ? data.mood : '',
      goal: typeof data.goal === 'string' ? data.goal : '',
      encourage: typeof data.encourage === 'string' ? data.encourage : ''
    };
  } catch {
    return null;
  }
}

function saveDashState(userId, state) {
  try {
    window.localStorage.setItem(getDashStateKey(userId), JSON.stringify({ ts: Date.now(), ...state }));
  } catch {
    return;
  }
}

function loadGoalTodos(userId) {
  try {
    const raw = window.localStorage.getItem(getGoalTodosKey(userId));
    const data = safeJsonParse(raw, []);
    if (!Array.isArray(data)) return [];
    return data
      .filter((x) => x && typeof x === 'object')
      .map((x) => ({ id: String(x.id || ''), text: String(x.text || '') }))
      .filter((x) => x.id && x.text);
  } catch {
    return [];
  }
}

function saveGoalTodos(userId, todos) {
  try {
    window.localStorage.setItem(getGoalTodosKey(userId), JSON.stringify(todos));
  } catch {
    return;
  }
}

function loadSuggestTodos(userId, fallback) {
  try {
    const raw = window.localStorage.getItem(getSuggestTodosKey(userId));
    const data = safeJsonParse(raw, null);
    if (!data) return fallback;
    if (!Array.isArray(data)) return fallback;
    const normalized = data
      .filter((x) => x && typeof x === 'object')
      .map((x) => ({ id: String(x.id || ''), text: String(x.text || '') }))
      .filter((x) => x.id && x.text);
    return normalized.length > 0 ? normalized : fallback;
  } catch {
    return fallback;
  }
}

function saveSuggestTodos(userId, todos) {
  try {
    window.localStorage.setItem(getSuggestTodosKey(userId), JSON.stringify(todos));
  } catch {
    return;
  }
}

function getChatTaskQueueKey(userId) {
  return `ts_chat_task_queue_${userId}`;
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [mood, setMood] = useState('');
  const [goal, setGoal] = useState('');
  const [goalTodos, setGoalTodos] = useState([]);
  const [suggestTodos, setSuggestTodos] = useState([]);
  const loadedRef = useRef(false);
  const suggestLoadedRef = useRef(false);
  const dashLoadedRef = useRef(false);
  const persistTimerRef = useRef(null);

  const greeting = useMemo(() => getGreeting(), []);
  const nickname = user?.name || '同学';

  const encourageOptions = useMemo(() => ([
    'AI 学伴给你加油打气中 (ง •_•)ง',
    '今天也要闪闪发光 (✧∀✧)',
    '你已经很棒了，再坚持一下就超神 (๑•̀ㅂ•́)و✧',
    '慢慢来，稳稳赢 (´▽｀)',
    '这题不怕，我陪你拆开做 (•̀ω•́)✧',
    '把今天学到的每一步都算进成长值里 (｡•̀ᴗ-)✧',
    '你不是一个人在战斗 (ง •̀_•́)ง',
    '专注 10 分钟，也是一种胜利 (•̀ᴗ•́)و ̑̑',
    '再试一次，说不定这次就通关了 (ง •̀_•́)ง',
    '小小一步，也是向前的一大步 (•̀ᴗ•́)و',
    '别急，思路正在加载中 (￣▽￣)ノ',
    '思考一下，你已经离答案更近了 (•̀ω•́)✧',
    '保持好奇心，学习会更有趣 (✿◡‿◡)',
    '今天的努力，会变成明天的底气 (๑•̀ㅂ•́)و✧',
    '一步一步来，难题也会变简单 (｡•̀ᴗ-)✧',
    '你认真思考的样子真的很厉害 (✧ω✧)',
    '学习模式已启动，冲鸭 (ง •̀_•́)ง',
    '再看一遍题目，说不定灵感就来了 (•̀ᴗ•́)و',
    '慢一点没关系，只要在前进 (´▽｀)',
    '每一次尝试都在升级你的大脑 (✧∀✧)',
    '思考 + 耐心 = 解题超能力 (๑•̀ㅂ•́)و✧',
    '困难只是经验值比较多的怪物 (ง •̀_•́)ง',
    '别担心，我会陪你一起想 (•̀ω•́)✧',
    '学习是一场长期升级任务 (✿◠‿◠)',
    '答案可能就在下一次尝试里 (•̀ᴗ•́)و',
    '保持节奏，你做得很好 (´▽｀)ノ',
    '这一步理解了，就离成功更近了 (✧ω✧)',
    '认真思考的每一秒都不浪费 (๑•̀ㅂ•́)و✧',
    '学习进度 +1 (ง •̀_•́)ง',
    '再坚持一下，马上就突破了 (•̀ω•́)✧',
    '别怕难题，它只是想和你做朋友 (´▽｀)',
    '你正在变得越来越强 (✧∀✧)',
    '思路已经在路上了，等等它 (•̀ᴗ•́)و',
    '今天也在认真升级自己 (ง •̀_•́)ง',
    '保持专注，奇迹会发生 (✧ω✧)',
    '慢慢理解，比记住更厉害 (•̀ω•́)✧',
    '每一题都是经验值 (๑•̀ㅂ•́)و✧',
    '你正在悄悄变强 (✿◡‿◡)'
  ]), []);
  const [encourage, setEncourage] = useState(() => pickRandom(encourageOptions));

  const refreshEncourage = () => {
    setEncourage((prev) => {
      if (encourageOptions.length <= 1) return prev;
      let next = prev;
      for (let i = 0; i < 6 && next === prev; i++) next = pickRandom(encourageOptions);
      return next;
    });
  };

  const statusText = '随时待命';
  const face = '(ﾉ◕ヮ◕)ﾉ';

  useEffect(() => {
    if (!user?.id) return;
    const restored = loadDashState(user.id);
    dashLoadedRef.current = true;
    if (!restored) return;
    if (restored.mood) setMood(restored.mood);
    if (typeof restored.goal === 'string') setGoal(restored.goal);
    if (restored.encourage) setEncourage(restored.encourage);
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    if (!dashLoadedRef.current) return;
    if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    persistTimerRef.current = setTimeout(() => {
      saveDashState(user.id, { mood, goal, encourage });
      persistTimerRef.current = null;
    }, 180);
  }, [user?.id, mood, goal, encourage]);

  useEffect(() => {
    return () => {
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    loadedRef.current = true;
    setGoalTodos(loadGoalTodos(user.id));
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    if (!loadedRef.current) return;
    saveGoalTodos(user.id, goalTodos);
  }, [user?.id, goalTodos]);

  const defaultSuggestTodos = useMemo(() => ([
    { id: 's1', text: '先来 1 道中等难度数学题巩固' },

  ]), []);

  useEffect(() => {
    if (!user?.id) return;
    suggestLoadedRef.current = true;
    setSuggestTodos(loadSuggestTodos(user.id, defaultSuggestTodos));
  }, [user?.id, defaultSuggestTodos]);

  useEffect(() => {
    if (!user?.id) return;
    if (!suggestLoadedRef.current) return;
    saveSuggestTodos(user.id, suggestTodos);
  }, [user?.id, suggestTodos]);

  const addGoalTodo = () => {
    const t = goal.trim();
    if (!t) return;
    const id = createId();
    setGoalTodos((prev) => prev.concat([{ id, text: t }]));
    setGoal('');
  };

  const queueChatTasksAndGo = useCallback((activeId) => {
    if (!user?.id) return;
    const tasks = [
      ...goalTodos.map((g) => ({ id: g.id, title: '今日目标', desc: g.text })),
      ...suggestTodos.map((s) => ({ id: s.id, title: '学习建议', desc: s.text }))
    ];
    const payload = { tasks, activeTaskId: String(activeId || '') };
    try {
      window.localStorage.setItem(getChatTaskQueueKey(user.id), JSON.stringify(payload));
    } catch {
      void 0;
    }
    window.location.hash = '#/chat';
  }, [user?.id, goalTodos, suggestTodos]);

  const startGoalTodo = useCallback((goalId) => {
    queueChatTasksAndGo(goalId);
  }, [queueChatTasksAndGo]);

  const removeGoalTodo = useCallback((goalId) => {
    setGoalTodos((prev) => prev.filter((x) => x.id !== goalId));
  }, []);

  const startSuggestTodo = useCallback((suggestId) => {
    queueChatTasksAndGo(suggestId);
  }, [queueChatTasksAndGo]);

  const removeSuggestTodo = useCallback((suggestId) => {
    setSuggestTodos((prev) => prev.filter((x) => x.id !== suggestId));
  }, []);

  const todos = useMemo(() => {
    const goalItems = goalTodos.map((g) => ({
      id: g.id,
      text: `今日目标：${g.text}`,
      primary: '开始',
      secondary: '稍后',
      onPrimary: () => startGoalTodo(g.id),
      onSecondary: () => removeGoalTodo(g.id)
    }));
    const suggestItems = suggestTodos.map((s) => ({
      id: s.id,
      text: s.text,
      primary: '开始',
      secondary: '稍后',
      onPrimary: () => startSuggestTodo(s.id),
      onSecondary: () => removeSuggestTodo(s.id)
    }));
    return goalItems.concat(suggestItems);
  }, [goalTodos, suggestTodos, startGoalTodo, removeGoalTodo, startSuggestTodo, removeSuggestTodo]);

  if (!loading && !user) {
    window.location.hash = '#/login';
    return null;
  }
  if (loading || !user) return null;

  return (
    <AppShell title="学习中枢">
      <div className="dashGrid">
        <div className="dashCard dashHero">
          <div className="dashHeroTop">
            <div>
              <div className="dashHello">{greeting}，{nickname}</div>
              <div className="dashStatus">AI 学伴：{statusText}</div>
            </div>
            <div className="dashFace" aria-hidden="true">{face}</div>
          </div>

          <div className="dashRow">
            <div className="dashField">
              <div className="dashLabel">今日心情</div>
              <div className="dashMoodBtns">
                {['开心', '一般', '疲惫', '困惑', '焦虑', '专注', '无聊', '有动力'].map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={mood === v ? 'dashPill is-active' : 'dashPill'}
                    onClick={() => setMood(v)}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
            <div className="dashField">
              <div className="dashLabel">每日AI鼓励</div>
              <div className="dashEncourage">
                <div className="dashEncourageText">{encourage}</div>
                <button type="button" className="dashBtnSmall dashBtnSmallGhost dashEncourageBtn" onClick={refreshEncourage}>
                  换一句
                </button>
              </div>
            </div>
          </div>

          <div className="dashGoal">
            <div className="dashLabel">今日目标（1 秒打卡）</div>
            <div className="dashGoalRow">
              <input
                className="dashInput"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="例如：做完 3 道几何题 + 背 20 个单词"
              />
              <button
                type="button"
                className="dashBtnPrimary"
                onClick={addGoalTodo}
              >
                增加目标
              </button>
            </div>
            <a className="dashEntryCard" href="#/chat">
              <div className="dashEntryTitle">AI 学习聊天</div>
              <div className="dashEntryDesc">与 AI 学伴聊天，学习知识</div>
            </a>
          </div>
        </div>

        <div className="dashCard">
          <div className="dashCardTitle">当前学习建议 / 智能待办</div>
          <div className="dashTodo">
            {todos.map((t) => (
              <div key={t.id} className="dashTodoItem">
                <div className="dashTodoMain">{t.text}</div>
                <div className="dashTodoActions">
                  <button type="button" className="dashBtnSmall" onClick={t.onPrimary}>
                    {t.primary}
                  </button>
                  <button type="button" className="dashBtnSmall dashBtnSmallGhost" onClick={t.onSecondary}>
                    {t.secondary}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="dashCard">
          <div className="dashCardTitle">进度 / 成就</div>
          <div className="dashStats">
            <div className="dashStat">
              <div className="dashStatValue">3</div>
              <div className="dashStatLabel">连续学习天数</div>
            </div>
            <div className="dashStat">
              <div className="dashStatValue">2h 10m</div>
              <div className="dashStatLabel">本周学习时长</div>
            </div>
            <div className="dashStat">
              <div className="dashStatValue">68%</div>
              <div className="dashStatLabel">本周完成率</div>
            </div>
            <div className="dashStat">
              <div className="dashStatValue">Lv. 4</div>
              <div className="dashStatLabel">成长值</div>
            </div>
          </div>
          <div className="dashBadges">
            {['坚持不懈', '错题克星', '早起学习', '今日已打卡'].map((b) => (
              <div key={b} className="dashBadge">{b}</div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
