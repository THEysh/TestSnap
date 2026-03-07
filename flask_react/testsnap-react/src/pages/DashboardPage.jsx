import React, { useMemo, useState } from 'react';
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

function getPersonaKey(userId) {
  return `ts_persona_${userId}`;
}

function loadPersona(userId) {
  try {
    const v = window.localStorage.getItem(getPersonaKey(userId));
    return v || 'gentle';
  } catch {
    return 'gentle';
  }
}

function savePersona(userId, persona) {
  try {
    window.localStorage.setItem(getPersonaKey(userId), persona);
  } catch {
    return;
  }
}

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const [mood, setMood] = useState('');
  const [goal, setGoal] = useState('');

  const [persona, setPersona] = useState(() => {
    if (!user?.id) return 'gentle';
    return loadPersona(user.id);
  });

  const greeting = useMemo(() => getGreeting(), []);
  const nickname = user?.name || '同学';

  if (!loading && !user) {
    window.location.hash = '#/login';
    return null;
  }

  const statusText = persona === 'gentle'
    ? '温柔陪伴中'
    : persona === 'sharp'
      ? '毒舌监督中'
      : '沙雕打气中';

  const face = persona === 'gentle' ? '(*´▽｀*)' : persona === 'sharp' ? '(¬_¬ )' : '(ﾉ◕ヮ◕)ﾉ';

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
                {['开心', '一般', '疲惫', '冲刺'].map((v) => (
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
              <div className="dashLabel">学伴性格</div>
              <div className="dashMoodBtns">
                <button
                  type="button"
                  className={persona === 'gentle' ? 'dashPill is-active' : 'dashPill'}
                  onClick={() => {
                    setPersona('gentle');
                    if (user?.id) savePersona(user.id, 'gentle');
                  }}
                >
                  温柔
                </button>
                <button
                  type="button"
                  className={persona === 'sharp' ? 'dashPill is-active' : 'dashPill'}
                  onClick={() => {
                    setPersona('sharp');
                    if (user?.id) savePersona(user.id, 'sharp');
                  }}
                >
                  毒舌
                </button>
                <button
                  type="button"
                  className={persona === 'funny' ? 'dashPill is-active' : 'dashPill'}
                  onClick={() => {
                    setPersona('funny');
                    if (user?.id) savePersona(user.id, 'funny');
                  }}
                >
                  沙雕
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
                onClick={() => {
                  if (!goal.trim()) return;
                  setGoal('');
                }}
              >
                打卡
              </button>
              <a className="dashBtnGhost" href="#/demo">去 Demo</a>
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
            <div className="dashTodoItem">
              <div className="dashTodoMain">你昨天数学错了 3 道，今天来 3 道中等难度巩固？</div>
              <div className="dashTodoActions">
                <button type="button" className="dashBtnSmall">开始</button>
                <button type="button" className="dashBtnSmall dashBtnSmallGhost">稍后</button>
              </div>
            </div>
            <div className="dashTodoItem">
              <div className="dashTodoMain">英语基础不牢固，背10个单词？</div>
              <div className="dashTodoActions">
                <button type="button" className="dashBtnSmall">开始</button>
                <button type="button" className="dashBtnSmall dashBtnSmallGhost">稍后</button>
              </div>
            </div>
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
