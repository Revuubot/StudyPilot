import React, { useState } from 'react';
import Nav from './components/Nav';
import SummariseTab from './components/SummariseTab';
import AskTab from './components/AskTab';
import SearchTab from './components/SearchTab';
import AnalyticsTab from './components/AnalyticsTab';
import AuthScreen from './components/AuthScreen';
import api from './api';

/**
 * Root application component.
 *
 * Manages global auth state and tab-based navigation between the
 * four main sections: Summarise, Ask, Search, Analytics.
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('summarise');
  const [isLoggedIn, setIsLoggedIn] = useState(api.isAuthenticated());

  const handleAuthSuccess = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    api.logout();
    setIsLoggedIn(false);
  };

  if (!isLoggedIn) {
    return <AuthScreen onSuccess={handleAuthSuccess} />;
  }

  const renderTab = () => {
    switch (activeTab) {
      case 'summarise':
        return <SummariseTab />;
      case 'ask':
        return <AskTab />;
      case 'search':
        return <SearchTab />;
      case 'analytics':
        return <AnalyticsTab />;
      default:
        return <SummariseTab />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Nav activeTab={activeTab} onTabChange={setActiveTab} onLogout={handleLogout} />
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 animate-fade-in">
        {renderTab()}
      </main>
      <footer className="text-center text-xs text-gray-600 py-4 border-t border-white/5">
        StudyPilot v1.0 — AI-powered study companion
      </footer>
    </div>
  );
}
