import React, { useEffect, useMemo, useRef, useState } from 'react';
import useAuth from '../../app/auth/useAuth';
import AppShell from '../../app/shell/AppShell';
import ContextSidebar from './components/ContextSidebar';
import MessageList from './components/MessageList';
import MessageComposer from './components/MessageComposer';
import CardModal from './components/CardModal';
import { streamChatAPI } from './services/chatApi';
import { generateLearningCard } from './services/generateCardApi';
import { streamGenerateLearningCard } from './services/generateCardStreamApi';
import { buildMessages } from '../../utils/buildChatMessages';
import { appendToCardLibrary } from './services/cardStorage';
import { API_BASE_URL } from '../../constants/apiConfig';
import '../../components/MarkdownViewer.css';
import './learningChat.css';
import GenerateCardModal from './components/GenerateCardModal';

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

function buildSystemPrompt({ personalityTitle, personalityDesc, task }) {
  const lines = [
    '你是“AI 学伴”，面向学习陪伴场景。',
    '目标：帮助学生理解知识点、拆解步骤、指出易错点、给出可执行练习计划。',
    '回答风格：分析题目仔细认真，确保分析的准确性, 必要时给出例题或练习建议。',
  ];
  if (personalityTitle) lines.push(`学伴性格：${personalityTitle}`);
  if (personalityDesc) lines.push(`性格特点：${personalityDesc}`);
  if (task) lines.push(`当前学习任务：${task}`);
  return lines.join('\n');
}

function markdownToHtml(md) {
  try {
    const marked = typeof window !== 'undefined' ? window.marked : null;
    if (marked?.parse) return marked.parse(md || '');
  } catch {
    return '';
  }
  return '';
}

function buildAttachmentsFromContextBlocks(blocks) {
  const attachments = [];
  (blocks || []).forEach((b, idx) => {
    const title = String(b?.title || `卡片${idx + 1}`).trim();
    const content = String(b?.content || '');
    const rawMd = `### ${title}\n\n${content}`.slice(0, 18000);
    attachments.push({ type: 'text', rawMd });
    const html = markdownToHtml(content);
    if (html) attachments.push({ type: 'image', html });
  });
  return attachments;
}

async function cancelChat({ convId, requestId }) {
  const payload = { conv_id: convId || null, request_id: requestId || null };
  const endpoints = Array.from(new Set([
    `${API_BASE_URL}/chat/cancel`,
    '/api/chat/cancel'
  ]));
  for (let i = 0; i < endpoints.length; i++) {
    const url = endpoints[i];
    try {
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      return;
    } catch {
      if (i === endpoints.length - 1) return;
    }
  }
}

export default function LearningChatPage() {
  const { user, loading } = useAuth();
  const abortRef = useRef(null);
  const streamingConvIdRef = useRef(null);
  const streamingRequestIdRef = useRef(null);
  const streamingAssistantIdRef = useRef(null);
  const stateLoadedRef = useRef(false);
  const persistTimerRef = useRef(null);
  const [sending, setSending] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const modelOptions = useMemo(() => ([
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "Qwen/Qwen3-VL-235B-A22B-Thinking",
    "Qwen/Qwen3-Next-80B-A3B-Instruct",
    "Qwen/Qwen3-Next-80B-A3B-Thinking",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-32B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct-128K",
    "Qwen/Qwen2.5-7B-Instruct",
    "zai-org/GLM-4.6V",
    "zai-org/GLM-4.6",
    "deepseek-ai/DeepSeek-V3",
    "deepseek-ai/DeepSeek-V3.1-Terminus",
    "deepseek-ai/DeepSeek-V3.2",
    "deepseek-ai/DeepSeek-R1"
  ]), []);
  const [selectedModel, setSelectedModel] = useState(modelOptions[0]);
  const canThinkModels = useMemo(() => ([
    "Pro/zai-org/GLM-5",
    "Pro/zai-org/GLM-4.7",
    "deepseek-ai/DeepSeek-V3.2",
    "Pro/deepseek-ai/DeepSeek-V3.2",
    "zai-org/GLM-4.6",
    "Qwen/Qwen3-8B",
    "Qwen/Qwen3-14B",
    "Qwen/Qwen3-32B",
    "Qwen/Qwen3-30B-A3B",
    "tencent/Hunyuan-A13B-Instruct",
    "zai-org/GLM-4.5V",
    "deepseek-ai/DeepSeek-V3.1-Terminus",
    "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"
  ]), []);
  const canThink = useMemo(() => canThinkModels.includes(selectedModel), [canThinkModels, selectedModel]);
  const [enableReasoning, setEnableReasoning] = useState(false);

  const [tasks, setTasks] = useState([
    { id: 't1', title: '今日任务', desc: '做 1 道数学题' },
    
  ]);
  const [activeTaskId, setActiveTaskId] = useState('t1');
  const activeTask = useMemo(() => tasks.find((t) => t.id === activeTaskId) || null, [tasks, activeTaskId]);

  const personalities = useMemo(() => ([
    { id: 'gentle_sis', title: '温柔耐心的姐姐型', desc: '像邻家大姐姐一样永远不急不躁，无论多蠢的问题都会耐心解答。' },
    { id: 'top_student', title: '超会讲题的学霸型', desc: '年级第一的学神同桌，擅长总结套路和公式，不讲废话只给干货，能把复杂问题拆解成清晰步骤。' },
    { id: 'funny', title: '活泼沙雕的搞怪型', desc: '班上的气氛担当，用梗、段子教学，时不时跑题但总能绕回来。' },
    { id: 'teacher', title: '严肃负责的老师型', desc: '严格但负责的班主任，不留情面指出错误但给出改进方案。' },
    { id: 'healing', title: '温柔治愈的陪伴型', desc: '像深夜电台主播般先接住情绪，话不多但每句都暖。' },
    { id: 'breakdown', title: '底层逻辑的拆解型', desc: '不满足于给答案，喜欢把复杂问题拆成最小单元，帮你建立知识框架。' },
    { id: 'analogy', title: '举一反三的类比型', desc: '擅长用生活例子解释抽象概念，把“黑话”翻译成“人话”。' },
    { id: 'socrates', title: '追根究底的苏格拉底型', desc: '从不直接给答案，用一连串反问逼你自己想明白。' },
    { id: 'story', title: '故事化叙事型', desc: '把知识点包装进故事、段子里，让你听完就忘不掉。' },
    { id: 'debate', title: '杠精上身的辩论型', desc: '专门挑难以察觉的逻辑漏洞，逼你把论点打磨更扎实。' },
    { id: 'association', title: '脑洞大开的联想型', desc: '把风马牛不相及的事情串在一起，头脑风暴打开思路。' },
    { id: 'toxic', title: '毒舌直给的简短型', desc: '不灌鸡汤，一针见血戳破问题本质。' },
    { id: 'hype', title: '元气满满的打鸡血型', desc: '像小太阳一样疯狂打气，用夸张赞美推着你走。' },
    { id: 'ai', title: 'AI式分析型（不装人，坦诚是AI）', desc: '不模仿人类，发挥AI优势：海量数据、绝对理性、超强算力。' },
  ]), []);
  const [activePersonalityId, setActivePersonalityId] = useState('top_student');
  const activePersonality = useMemo(
    () => personalities.find((p) => p.id === activePersonalityId) || personalities[0] || null,
    [personalities, activePersonalityId]
  );

  const [cards, setCards] = useState([]);

  const [contextBlocks, setContextBlocks] = useState([]);
  const [openCard, setOpenCard] = useState(null);

  const [messages, setMessages] = useState(() => ([
    {
      id: createId(),
      role: 'assistant',
      content: '你好，我是你的 **AI 学伴**。\n\n把题目、知识点或你的学习目标发给我，我会用“步骤 + 易错点 + 练习建议”的方式陪你学。'
    }
  ]));
  const [input, setInput] = useState('');
  const [toast, setToast] = useState('');
  const toastTimerRef = useRef(null);
  const [confirmClear, setConfirmClear] = useState(false);
  const [genOpen, setGenOpen] = useState(false);
  const [genLoading, setGenLoading] = useState(false);
  const [genError, setGenError] = useState('');
  const [genTitle, setGenTitle] = useState('');
  const [genMarkdown, setGenMarkdown] = useState('');
  const [genSourceId, setGenSourceId] = useState('');
  const [genMinimized, setGenMinimized] = useState(false);
  const genMinimizedRef = useRef(false);
  const genAbortRef = useRef(null);
  const genMarkdownRef = useRef('');
  const genFlushTimerRef = useRef(null);

  const showToast = (msg) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToast(String(msg || ''));
    toastTimerRef.current = setTimeout(() => {
      setToast('');
      toastTimerRef.current = null;
    }, 1300);
  };

  const buildInitialMessages = () => ([
    {
      id: createId(),
      role: 'assistant',
      content: '你好，我是你的 **AI 学伴**。\n\n知识点或不理解的地方发给我，我会用“步骤 + 易错点 + 练习建议”的方式陪你学。'
    }
  ]);

  useEffect(() => {
    genMinimizedRef.current = genMinimized;
  }, [genMinimized]);

  const flushGenMarkdown = () => {
    if (genFlushTimerRef.current) return;
    genFlushTimerRef.current = setTimeout(() => {
      genFlushTimerRef.current = null;
      if (genMinimizedRef.current) return;
      setGenMarkdown(genMarkdownRef.current);
      const m = genMarkdownRef.current.match(/^#\s+(.+)\s*$/m);
      if (m) setGenTitle((t) => (String(t || '').trim() && t !== '学习卡片' ? t : String(m[1] || '').trim()));
    }, 80);
  };

  const runGenerateCard = async (assistantMsgId) => {
    const id = String(assistantMsgId || '');
    const idx = messages.findIndex((m) => String(m?.id || '') === id);
    const slice = idx >= 0 ? messages.slice(0, idx + 1) : messages;
    const payloadMessages = slice
      .filter((m) => m && (m.role === 'user' || m.role === 'assistant'))
      .map((m) => ({ role: m.role, content: String(m.content || '') }))
      .filter((m) => m.content.trim());

    setGenOpen(true);
    setGenMinimized(false);
    setGenLoading(true);
    setGenError('');
    setGenTitle('学习卡片');
    setGenMarkdown('');
    genMarkdownRef.current = '';
    setGenSourceId(id);

    try {
      if (genAbortRef.current) genAbortRef.current.abort();
    } catch {
      void 0;
    }
    const controller = new AbortController();
    genAbortRef.current = controller;

    const streamRet = await streamGenerateLearningCard({
      userId: user?.id,
      messages: payloadMessages,
      modelName: selectedModel,
      onChunk: (piece) => {
        if (piece?.type === 'delta') {
          genMarkdownRef.current += String(piece.content || '');
          if (!genMinimizedRef.current) flushGenMarkdown();
        } else if (piece?.type === 'error') {
          setGenError(String(piece.content || '生成学习卡片出错，请重试'));
        }
      },
      signal: controller.signal
    });
    if (!streamRet?.ok) {
      const ret = await generateLearningCard({ userId: user?.id, messages: payloadMessages, modelName: selectedModel });
      if (!ret?.ok) {
        setGenError(ret?.error || '生成学习卡片出错，请重试');
        setGenLoading(false);
        return;
      }
      genMarkdownRef.current = String(ret.markdown || '');
      setGenTitle(ret.title || '学习卡片');
      if (!genMinimizedRef.current) setGenMarkdown(genMarkdownRef.current);
      setGenLoading(false);
      return;
    }
    if (!genMinimizedRef.current) {
      setGenMarkdown(genMarkdownRef.current);
      const m = genMarkdownRef.current.match(/^#\s+(.+)\s*$/m);
      if (m) setGenTitle(String(m[1] || '').trim() || '学习卡片');
    }
    setGenLoading(false);
  };

  const saveGeneratedCard = () => {
    const content = String(genMarkdownRef.current || genMarkdown || '').trim();
    if (!content) return;
    const title = String(genTitle || '').trim() || '学习卡片';
    const card = { id: createId(), title, meta: 'AI 生成', content };
    const ret = appendToCardLibrary(user.id, [card]);
    if (ret?.ok) showToast('已保存到卡片库');
    try {
      genAbortRef.current?.abort?.();
    } catch {
      void 0;
    }
    setGenOpen(false);
    setGenMinimized(false);
  };

  useEffect(() => {
    return () => {
      if (genFlushTimerRef.current) clearTimeout(genFlushTimerRef.current);
      try {
        genAbortRef.current?.abort?.();
      } catch {
        void 0;
      }
    };
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    if (stateLoadedRef.current) return;
    stateLoadedRef.current = true;
    const key = `ts_learning_chat_state_${user.id}`;
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return;
      const data = safeJsonParse(raw, null);
      if (!data || typeof data !== 'object') return;
      const ts = Number(data.ts || 0);
      if (ts && Date.now() - ts > 7 * 24 * 60 * 60 * 1000) return;
      if (Array.isArray(data.messages) && data.messages.length > 0) setMessages(data.messages);
      if (Array.isArray(data.contextBlocks)) setContextBlocks(data.contextBlocks);
      if (Array.isArray(data.tasks) && data.tasks.length > 0) setTasks(data.tasks);
      if (typeof data.activeTaskId === 'string') setActiveTaskId(data.activeTaskId);
      if (Array.isArray(data.cards)) setCards(data.cards);
      if (typeof data.input === 'string') setInput(data.input);
      if (typeof data.selectedModel === 'string' && data.selectedModel) setSelectedModel(data.selectedModel);
      if (typeof data.enableReasoning === 'boolean') setEnableReasoning(data.enableReasoning);
      if (typeof data.activePersonalityId === 'string' && data.activePersonalityId) setActivePersonalityId(data.activePersonalityId);
      if (typeof data.convId === 'string' && data.convId) streamingConvIdRef.current = data.convId;
      setSending(false);
    } catch {
      return;
    }
  }, [user?.id]);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mql = window.matchMedia('(max-width: 980px)');
    const apply = () => setIsMobile(!!mql.matches);
    apply();
    const onChange = () => apply();
    if (typeof mql.addEventListener === 'function') mql.addEventListener('change', onChange);
    else mql.addListener(onChange);
    return () => {
      if (typeof mql.removeEventListener === 'function') mql.removeEventListener('change', onChange);
      else mql.removeListener(onChange);
    };
  }, []);

  useEffect(() => {
    if (!isMobile) setSidebarOpen(false);
  }, [isMobile]);

  useEffect(() => {
    if (!user?.id) return;
    if (!stateLoadedRef.current) return;
    const key = `ts_learning_chat_state_${user.id}`;
    if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
    persistTimerRef.current = setTimeout(() => {
      try {
        const convId = streamingConvIdRef.current || createId();
        streamingConvIdRef.current = convId;
        const payload = {
          ts: Date.now(),
          convId,
          selectedModel,
          enableReasoning,
          messages: (messages || []).slice(-80),
          contextBlocks,
          tasks,
          activeTaskId,
          activePersonalityId,
          cards,
          input
        };
        window.localStorage.setItem(key, JSON.stringify(payload));
      } catch {
        void 0;
      } finally {
        persistTimerRef.current = null;
      }
    }, 180);
  }, [user?.id, messages, contextBlocks, tasks, activeTaskId, activePersonalityId, cards, input, selectedModel, enableReasoning]);

  useEffect(() => {
    return () => {
      if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
      try {
        abortRef.current?.abort();
      } catch {
        void 0;
      }
      const convId = streamingConvIdRef.current;
      const requestId = streamingRequestIdRef.current;
      if (convId || requestId) cancelChat({ convId, requestId });
    };
  }, []);

  useEffect(() => {
    if (!user?.id) return;
    const key = `ts_chat_context_queue_${user.id}`;
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return;
      const queued = JSON.parse(raw);
      window.localStorage.removeItem(key);
      if (!Array.isArray(queued) || queued.length === 0) return;
      setCards((prev) => queued.concat(prev));
      setMessages((prev) => prev.concat([{
        id: createId(),
        role: 'assistant',
        content: `左侧有 **${queued.length}** 张知识卡片。打开并插入到聊天开始学习。`
      }]));
    } catch {
      return;
    }
  }, [user?.id]);

  useEffect(() => {
    if (!user?.id) return;
    const key = `ts_chat_task_queue_${user.id}`;
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return;
      const data = JSON.parse(raw);
      window.localStorage.removeItem(key);
      const queuedTasks = Array.isArray(data?.tasks) ? data.tasks : [];
      if (queuedTasks.length === 0) return;
      const normalized = queuedTasks
        .filter((t) => t && typeof t === 'object')
        .map((t) => ({
          id: String(t.id || ''),
          title: String(t.title || '今日目标'),
          desc: String(t.desc || '')
        }))
        .filter((t) => t.id && t.desc);
      if (normalized.length === 0) return;
      const nextActive = String(data?.activeTaskId || '');
      setTasks(normalized);
      setActiveTaskId(normalized.some((t) => t.id === nextActive) ? nextActive : normalized[0].id);
    } catch {
      return;
    }
  }, [user?.id]);

  useEffect(() => {
    if (!loading && !user) {
      window.location.hash = '#/login';
    }
  }, [loading, user]);

  const insertCardToContext = (card) => {
    const id = createId();
    setContextBlocks((prev) => prev.concat([{
      id,
      title: card.title,
      content: card.content
    }]));
  };

  const removeContext = (id) => {
    setContextBlocks((prev) => prev.filter((x) => x.id !== id));
  };

  const completeTask = (id) => {
    setTasks((prev) => {
      const next = prev.filter((t) => t.id !== id);
      setActiveTaskId((cur) => (cur === id ? (next[0]?.id || '') : cur));
      return next;
    });
  };

  const openCardModal = (card) => {
    setOpenCard(card);
  };

  const stopGenerating = () => {
    const convId = streamingConvIdRef.current;
    const requestId = streamingRequestIdRef.current;
    const assistantId = streamingAssistantIdRef.current;
    try {
      abortRef.current?.abort();
    } catch {
      void 0;
    }
    abortRef.current = null;
    streamingRequestIdRef.current = null;
    streamingAssistantIdRef.current = null;
    setSending(false);
    if (convId || requestId) cancelChat({ convId, requestId });
    if (assistantId) {
      setMessages((prev) => prev.map((m) => {
        if (m.id !== assistantId) return m;
        const cur = String(m.content || '').trim();
        const r = String(m.reasoning || '').trim();
        if (cur || r) return m;
        return { ...m, content: '已停止生成。' };
      }));
    }
  };

  const copyToClipboard = async (text) => {
    const value = String(text || '');
    if (!value) return false;
    if (navigator?.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(value);
        return true;
      } catch {
        return false;
      }
    }
    try {
      const ta = document.createElement('textarea');
      ta.value = value;
      ta.setAttribute('readonly', 'true');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      ta.style.top = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return !!ok;
    } catch {
      return false;
    }
  };

  const copyAllChat = async () => {
    const blocks = (messages || []).map((m) => {
      const role = m.role === 'user' ? '你' : 'AI';
      const content = String(m.content || '');
      const reasoning = String(m.reasoning || '').trim();
      const parts = [`### ${role}\n\n${content}`];
      if (reasoning) parts.push(`\n\n<details>\n<summary>思考</summary>\n\n${reasoning}\n\n</details>`);
      return parts.join('');
    });
    const ok = await copyToClipboard(blocks.join('\n\n---\n\n'));
    if (ok) showToast('已复制对话');
  };

  const requestClearChat = () => {
    setConfirmClear(true);
  };

  const clearChat = () => {
    stopGenerating();
    setMessages(buildInitialMessages());
    setContextBlocks([]);
    setInput('');
    streamingConvIdRef.current = createId();
    streamingRequestIdRef.current = null;
    streamingAssistantIdRef.current = null;
    try {
      if (user?.id) window.localStorage.removeItem(`ts_learning_chat_state_${user.id}`);
    } catch {
      void 0;
    }
    setConfirmClear(false);
    showToast('已清空聊天记录');
  };

  const send = async () => {
    const question = input.trim();
    if (!question) return;
    if (sending) return;

    setSending(true);
    setInput('');

    const contextSnapshot = contextBlocks;
    setContextBlocks([]);

    const userMsg = { id: createId(), role: 'user', content: question };
    const assistantMsgId = createId();
    setMessages((prev) => prev.concat([userMsg, { id: assistantMsgId, role: 'assistant', content: '' }]));

    const controller = new AbortController();
    abortRef.current = controller;
    const convId = streamingConvIdRef.current || createId();
    const requestId = createId();
    streamingConvIdRef.current = convId;
    streamingRequestIdRef.current = requestId;
    streamingAssistantIdRef.current = assistantMsgId;

    const systemPrompt = buildSystemPrompt({
      personalityTitle: activePersonality?.title || '',
      personalityDesc: activePersonality?.desc || '',
      task: activeTask?.desc || activeTask?.title || ''
    });

    const history = messages
      .slice(-10)
      .filter((m) => m && (m.role === 'user' || m.role === 'assistant'))
      .map((m) => ({ role: m.role, content: String(m.content || '') }));

    const attachments = buildAttachmentsFromContextBlocks(contextSnapshot);
    const built = buildMessages(history, question, attachments);
    const payload = {
      messages: [{ role: 'system', content: systemPrompt }, ...built],
      conv_id: convId,
      request_id: requestId,
      model_name: selectedModel,
      enable_reasoning: !!enableReasoning && !!canThink
    };

    const updateAssistant = (delta) => {
      setMessages((prev) => prev.map((m) => {
        if (m.id !== assistantMsgId) return m;
        return { ...m, content: String(m.content || '') + String(delta || '') };
      }));
    };

    const updateAssistantReasoning = (delta) => {
      setMessages((prev) => prev.map((m) => {
        if (m.id !== assistantMsgId) return m;
        return { ...m, reasoning: String(m.reasoning || '') + String(delta || '') };
      }));
    };

    try {
      const ret = await streamChatAPI(payload, (piece) => {
        if (typeof piece === 'string') {
          updateAssistant(piece);
          return;
        }
        if (piece && typeof piece === 'object') {
          if (piece.type === 'content') updateAssistant(piece.content || '');
          if (piece.type === 'reasoning' || piece.type === 'thinking' || piece.type === 'thought') updateAssistantReasoning(piece.content || '');
          if (piece.type === 'error') updateAssistant(`\n\n[错误] ${piece.content || ''}`);
        }
      }, controller.signal);
      if (!ret?.success) {
        if (controller.signal.aborted) return;
        updateAssistant(`\n\n[流式失败] ${ret?.error || '未知错误'}`);
      }
    } catch (e) {
      const name = e?.name || '';
      const msg = String(e || '');
      if (name !== 'AbortError' && !msg.includes('AbortError')) {
        updateAssistant(`\n\n[异常] ${msg}`);
      }
    } finally {
      abortRef.current = null;
      streamingRequestIdRef.current = null;
      streamingAssistantIdRef.current = null;
      setSending(false);
    }
  };

  if (loading || !user) return null;

  return (
    <AppShell title="AI 学习聊天">
      <div className="lcLayout">
        {!isMobile && (
          <ContextSidebar
            tasks={tasks}
            activeTaskId={activeTaskId}
            onCompleteTask={completeTask}
            onSelectTask={setActiveTaskId}
            personalities={personalities}
            activePersonalityId={activePersonalityId}
            onSelectPersonality={setActivePersonalityId}
            cards={cards}
            onOpenCard={openCardModal}
          />
        )}

        <div className="lcMain">
          <MessageList
            messages={messages}
            streaming={sending}
            onGenerateCard={(msgId) => runGenerateCard(msgId)}
          />

          <MessageComposer
            input={input}
            onChangeInput={setInput}
            onSend={send}
            onStop={stopGenerating}
            onClear={requestClearChat}
            onCopyAll={copyAllChat}
            onOpenSidebar={() => setSidebarOpen(true)}
            showSidebarButton={isMobile}
            sending={sending}
            modelOptions={modelOptions}
            selectedModel={selectedModel}
            onChangeModel={setSelectedModel}
            enableReasoning={enableReasoning}
            canThink={canThink}
            onToggleReasoning={setEnableReasoning}
            contextBlocks={contextBlocks}
            onRemoveContext={removeContext}
          />
        </div>
      </div>
      {isMobile && sidebarOpen && (
        <div className="lcDrawerMask" role="dialog" aria-modal="true">
          <div className="lcDrawer">
            <div className="lcDrawerHeader">
              <div className="lcDrawerTitle">学习面板</div>
              <button type="button" className="lcDrawerX" onClick={() => setSidebarOpen(false)}>×</button>
            </div>
            <div className="lcDrawerBody">
              <ContextSidebar
                tasks={tasks}
                activeTaskId={activeTaskId}
                onCompleteTask={(id) => {
                  completeTask(id);
                }}
                onSelectTask={setActiveTaskId}
                personalities={personalities}
                activePersonalityId={activePersonalityId}
                onSelectPersonality={setActivePersonalityId}
                cards={cards}
                onOpenCard={(card) => {
                  openCardModal(card);
                  setSidebarOpen(false);
                }}
              />
            </div>
          </div>
        </div>
      )}
      <CardModal
        open={!!openCard}
        card={openCard}
        onClose={() => setOpenCard(null)}
        onInsert={(card) => {
          insertCardToContext(card);
          setOpenCard(null);
        }}
      />
      <GenerateCardModal
        open={genOpen}
        loading={genLoading}
        error={genError}
        title={genTitle}
        markdown={genMarkdown}
        onClose={() => {
          try {
            genAbortRef.current?.abort?.();
          } catch {
            void 0;
          }
          setGenOpen(false);
          setGenMinimized(false);
          setGenLoading(false);
          setGenError('');
          setGenTitle('');
          setGenMarkdown('');
          genMarkdownRef.current = '';
          setGenSourceId('');
        }}
        onMinimize={() => {
          setGenOpen(false);
          setGenMinimized(true);
          showToast('已在后台生成学习卡片');
        }}
        onRetry={() => runGenerateCard(genSourceId)}
        onSave={saveGeneratedCard}
      />
      {genMinimized && (
        <div className="lcGenFloat">
          <div>{genLoading ? '学习卡片生成中…' : '学习卡片已生成'}</div>
          <button
            type="button"
            className="lcGenFloatBtn"
            onClick={() => {
              setGenMinimized(false);
              setGenOpen(true);
              setGenMarkdown(genMarkdownRef.current);
            }}
          >
            打开
          </button>
        </div>
      )}
      {confirmClear && (
        <div className="lcConfirmMask" role="dialog" aria-modal="true">
          <div className="lcConfirm">
            <div className="lcConfirmTitle">清空聊天记录</div>
            <div className="lcConfirmDesc">将清空当前聊天内容（不影响卡片库）。</div>
            <div className="lcConfirmActions">
              <button type="button" className="lcBtn lcBtnPrimary" onClick={clearChat}>
                确认清空
              </button>
              <button type="button" className="lcBtn lcBtnGhost" onClick={() => setConfirmClear(false)}>
                取消
              </button>
            </div>
          </div>
        </div>
      )}
      {!!toast && (
        <div className="lcToast" role="status" aria-live="polite">
          {toast}
        </div>
      )}
    </AppShell>
  );
}

