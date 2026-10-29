import React from 'react';

const TABS = [
  { id: 'summarise', label: 'Summarise', icon: '📝' },
  { id: 'ask', label: 'Ask', icon: '💬' },
  { id: 'search', label: 'Search', icon: '🔍' },
  { id: 'analytics', label: 'Analytics', icon: '📊' },
];

/**
 * Top navigation bar with tab switcher and logout.
 */
export default function Nav({ activeTab, onTabChange, onLogout }) {
  return (
    <header className="sticky top-0 z-50 border-b border-white/[0.06]" style={{ background: 'rgba(10,10,26,0.85)', backdropFilter: 'blur(16px)' }}>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center text-lg"
               style={{ background: 'linear-gradient(135deg, #6366f1, #7c3aed)' }}>
            🚀
          </div>
          <h1 className="text-lg font-bold tracking-tight">
            <span className="bg-clip-text text-transparent" style={{ backgroundImage: 'linear-gradient(135deg, #e2e8f0, #94a3b8)' }}>
              Study
            </span>
            <span className="bg-clip-text text-transparent" style={{ backgroundImage: 'linear-gradient(135deg, #818cf8, #6366f1)' }}>
              Pilot
            </span>
          </h1>
        </div>

        {/* Tabs */}
        <nav className="hidden sm:flex items-center gap-1 rounded-xl p-1" style={{ background: 'rgba(255,255,255,0.04)' }}>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              id={`nav-tab-${tab.id}`}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-brand-600/30 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/[0.04]'
              }`}
            >
              <span className="text-base">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Mobile tabs */}
        <select
          className="sm:hidden glass-input !w-auto !py-2 !px-3 text-sm"
          value={activeTab}
          onChange={(e) => onTabChange(e.target.value)}
        >
          {TABS.map((tab) => (
            <option key={tab.id} value={tab.id}>{tab.icon} {tab.label}</option>
          ))}
        </select>

        {/* Logout */}
        <button
          id="btn-logout"
          onClick={onLogout}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors px-3 py-2 rounded-lg hover:bg-white/[0.04]"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
