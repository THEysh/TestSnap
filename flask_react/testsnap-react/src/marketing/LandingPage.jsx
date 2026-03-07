import React, { useMemo } from 'react';
import './landing.css';

const FEATURES = [
  {
    title: 'AI 智能题解',
    desc: '拍照上传，自动识别题目并给出分步解析与易错点提示。'
  },
  {
    title: 'AI 学习报告',
    desc: '自动生成学习过程报告，掌握度、薄弱点与提升建议一目了然。'
  },
  {
    title: 'AI 学习分析',
    desc: '聚合错题、知识点与练习轨迹，给出个性化学习路径。'
  },
  {
    title: '多格式文档解析',
    desc: '支持 PDF 与图片，结构化输出 Markdown，方便二次编辑与归档。'
  },
  {
    title: '实时渲染与可视化',
    desc: '支持图片与 LaTeX 公式实时渲染，解析过程更直观。'
  }
];

const TESTIMONIALS = [
  {
    name: '小李 · 高三',
    quote: '拍一张就能得到步骤解析，还会提示我哪里容易丢分。'
  },
  {
    name: '小张 · 大一',
    quote: '把 PDF 直接转成 Markdown，复习资料整理效率提高很多。'
  },
  {
    name: '王老师 · 教研',
    quote: '报告和分析很清晰，适合做课堂练习后的快速复盘。'
  }
];

export default function LandingPage() {
  const demoUrl = useMemo(() => {
    try {
      const base = window.location.origin + window.location.pathname;
      return `${base}#/demo?embed=1`;
    } catch {
      return '#/demo?embed=1';
    }
  }, []);

  return (
    <div className="landing">
      <section className="landing-hero">
        <div className="landing-heroInner">
          <div className="landing-kicker">AI 学伴</div>
          <h1 className="landing-title">你的专属 AI 学习伙伴</h1>
          <p className="landing-subtitle">
            从试卷扫描到结构化笔记：更快读懂、更准提取、更好复盘。
          </p>

          <div className="landing-cta">
            <a className="landing-btn landing-btnPrimary" href="#/login">立即体验</a>
            <a className="landing-btn landing-btnGhost" href="#/demo">查看 Demo</a>
          </div>

          <div className="landing-metrics">
            <div className="landing-metric">
              <div className="landing-metricValue">PDF / 图片</div>
              <div className="landing-metricLabel">多格式输入</div>
            </div>
            <div className="landing-metric">
              <div className="landing-metricValue">Markdown</div>
              <div className="landing-metricLabel">结构化输出</div>
            </div>
            <div className="landing-metric">
              <div className="landing-metricValue">实时流式</div>
              <div className="landing-metricLabel">过程可视化</div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-sectionInner">
          <h2 className="landing-h2">核心能力</h2>
          <p className="landing-p">围绕学习场景的输入、理解、输出与复盘，打造可落地的 AI 学伴体验。</p>

          <div className="landing-grid">
            {FEATURES.map((f) => (
              <div key={f.title} className="landing-card">
                <div className="landing-cardTitle">{f.title}</div>
                <div className="landing-cardDesc">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-sectionAlt">
        <div className="landing-sectionInner">
          <div className="landing-split">
            <div className="landing-splitText">
              <h2 className="landing-h2">真实 Demo 嵌入</h2>
              <p className="landing-p">
                直接在官网中体验当前 Demo。后续可无缝升级为用户体系与个人学习空间。
              </p>
              <div className="landing-cta">
                <a className="landing-btn landing-btnPrimary" href="#/demo">打开完整 Demo</a>
                <a className="landing-btn landing-btnGhost" href="#/login">前往登录</a>
              </div>
            </div>
            <div className="landing-embed">
              <iframe
                title="TextSnap Demo"
                src={demoUrl}
                className="landing-iframe"
                loading="lazy"
              />
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-sectionInner">
          <h2 className="landing-h2">截图与用户评价</h2>
          <p className="landing-p">展示占位，后续可替换为真实截图与真实用户数据。</p>

          <div className="landing-gallery">
            <div className="landing-shot" />
            <div className="landing-shot" />
            <div className="landing-shot" />
          </div>

          <div className="landing-quotes">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="landing-quote">
                <div className="landing-quoteText">“{t.quote}”</div>
                <div className="landing-quoteName">{t.name}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-footerInner">
          <div className="landing-footerLeft">
            <div className="landing-footerBrand">AI 学伴</div>
            <div className="landing-footerMeta">技术栈：React · Vite · Flask · PyTorch · SiliconFlow</div>
          </div>
          <div className="landing-footerRight">
            <a className="landing-footerLink" href="#/privacy">隐私协议</a>
            <a className="landing-footerLink" href="#/login">登录</a>
            <a className="landing-footerLink" href="#/demo">Demo</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

