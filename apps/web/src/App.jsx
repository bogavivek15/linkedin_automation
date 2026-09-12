import React, { useState, useEffect } from 'react';
import { NetworkHeader } from './components/NetworkHeader';
import { FeedPage } from './pages/Feed';
import { NetworkPage } from './pages/Network';
import { JobsPage } from './pages/Jobs';
import { MessagesPage } from './pages/Messages';
import { CommandCenterPage } from './pages/CommandCenter';
import { ProfilePage } from './pages/Profile';
import { LoginPage } from './pages/Login';

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(true);
  const [currentTab, setCurrentTab] = useState('feed');

  // Sync with window URL hash or pathname for convenient navigation
  useEffect(() => {
    function handleLocation() {
      const path = window.location.pathname.replace(/^\//, '') || window.location.hash.replace(/^#\/?/, '');
      if (['feed', 'network', 'jobs', 'messages', 'command-center', 'profile'].includes(path)) {
        setCurrentTab(path);
      } else if (path.startsWith('in/')) {
        setCurrentTab('profile');
      }
    }

    handleLocation();
    window.addEventListener('popstate', handleLocation);
    window.addEventListener('hashchange', handleLocation);
    return () => {
      window.removeEventListener('popstate', handleLocation);
      window.removeEventListener('hashchange', handleLocation);
    };
  }, []);

  function handleSelectTab(tabId) {
    setCurrentTab(tabId);
    window.history.pushState(null, '', `/${tabId === 'feed' ? '' : tabId}`);
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen bg-[#f3f2ef] text-black/90 flex flex-col font-sans selection:bg-[#0a66c2]/30 selection:text-black">
      {/* Top Header Navigation */}
      <NetworkHeader currentTab={currentTab} onSelectTab={handleSelectTab} />

      {/* Main Execution Surface */}
      <main className="flex-1 w-full animate-fade-in">
        {currentTab === 'feed' && <FeedPage onNavigate={handleSelectTab} />}
        {currentTab === 'network' && <NetworkPage onNavigate={handleSelectTab} />}
        {currentTab === 'jobs' && <JobsPage onNavigate={handleSelectTab} />}
        {currentTab === 'messages' && <MessagesPage onNavigate={handleSelectTab} />}
        {currentTab === 'command-center' && <CommandCenterPage onNavigate={handleSelectTab} />}
        {currentTab === 'profile' && <ProfilePage onNavigate={handleSelectTab} />}
      </main>
    </div>
  );
}
