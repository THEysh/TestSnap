import './App.css';
import React, { Suspense, useEffect, useMemo, useState } from 'react';
import LandingPage from './marketing/LandingPage';
import DemoPage from './pages/DemoPage';
import AuthPage from './pages/AuthPage';
import PrivacyPage from './pages/PrivacyPage';
import DashboardPage from './pages/DashboardPage';
import { AuthProvider } from './app/auth/AuthContext.jsx';
import LearningChatPage from './pages/LearningChatPage';
import FileProcessing from './pages/FileProcessing';
import LibraryPage from './pages/LibraryPage';

const ChatPage = React.lazy(() => import('./pages/ChatPage'));

function parseHashRoute(hash) {
  const raw = (hash || '#/').replace(/^#/, '');
  const qIndex = raw.indexOf('?');
  const path = (qIndex >= 0 ? raw.slice(0, qIndex) : raw) || '/';
  const queryString = qIndex >= 0 ? raw.slice(qIndex + 1) : '';
  const params = new URLSearchParams(queryString);
  return { path, params };
}

function App() {
  const [route, setRoute] = useState(
    typeof window !== 'undefined' ? (window.location.hash || '#/') : '#/'
  );
  useEffect(() => {
    const handler = () => setRoute(window.location.hash || '#/');
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);
  const parsed = useMemo(() => parseHashRoute(route), [route]);
  const path = parsed.path || '/';

  useEffect(() => {
    if (typeof document === 'undefined') return;
    const embed = path.startsWith('/demo') && String(parsed.params?.get('embed') || '') === '1';
    const isMarketing = path === '/' || path === '/login' || path === '/privacy' || embed;
    document.body.classList.toggle('marketing-mode', isMarketing);
    const launcher = document.getElementById('textsnap_chat_launcher');
    if (launcher) {
      const showLauncher = path.startsWith('/demo') && !path.startsWith('/demo/chat');
      launcher.style.display = showLauncher ? 'flex' : 'none';
    }
  }, [path, parsed.params]);

  return (
    <AuthProvider>
      {path.startsWith('/demo/chat') ? (
        <Suspense fallback={<div style={{ padding: 20 }}>加载聊天页面...</div>}>
          <ChatPage />
        </Suspense>
      ) : path.startsWith('/chat') ? (
        <LearningChatPage />
      ) : path.startsWith('/file-processing') ? (
        <FileProcessing />
      ) : path.startsWith('/library') ? (
        <LibraryPage />
      ) : path.startsWith('/demo') ? (
        <DemoPage routeParams={parsed.params} />
      ) : path.startsWith('/login') ? (
        <AuthPage />
      ) : path.startsWith('/app') ? (
        <DashboardPage />
      ) : path.startsWith('/privacy') ? (
        <PrivacyPage />
      ) : (
        <LandingPage />
      )}
    </AuthProvider>
  );
}

export default App;
