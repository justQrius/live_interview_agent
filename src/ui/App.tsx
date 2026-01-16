import { useState, useEffect } from 'react';
import { useSessionStore } from './store/sessionStore';
import SessionControls from './components/SessionControls';
import AnswerDisplay from './components/AnswerDisplay';
import ContextLoader from './components/ContextLoader';
import CalibrationModal from './components/CalibrationModal';
import SettingsModal from './components/SettingsModal';
import { HistoryPanel } from './components/HistoryPanel';
import { PreparationButton } from './components/PreparationButton';
import { PreparationSummary } from './components/PreparationSummary';
import { CoachingPanel } from './components/CoachingPanel';
import { ThemeToggle } from './components/ThemeToggle';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  
  const status = useSessionStore((state) => state.status);
  const preparationSummary = useSessionStore((state) => state.preparationSummary);
  const isPreparationExpanded = useSessionStore((state) => state.isPreparationExpanded);
  const setPreparationExpanded = useSessionStore((state) => state.setPreparationExpanded);
  const loadedContextFiles = useSessionStore((state) => state.loadedContextFiles);
  
  const { isConnected } = useWebSocket();

  // Auto-collapse sidebar when session starts
  useEffect(() => {
    if (status === 'listening' || status === 'processing') {
      setIsSidebarOpen(false);
    }
  }, [status]);

  // Get status display info
  const getStatusInfo = () => {
    if (!isConnected) {
      return { color: 'bg-red-500', text: 'Offline', pulse: false };
    }
    switch (status) {
      case 'listening':
        return { color: 'bg-green-500', text: 'Listening', pulse: true };
      case 'processing':
        return { color: 'bg-blue-500', text: 'Processing', pulse: true };
      case 'calibrating':
        return { color: 'bg-amber-500', text: 'Calibrating', pulse: true };
      default:
        return { color: 'bg-emerald-500', text: 'Ready', pulse: false };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="min-h-screen bg-background text-text-primary">
      {/* Backdrop when sidebar open - closes sidebar on click */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sliding Sidebar Overlay */}
      <aside className={`
        fixed top-0 left-0 h-full w-[360px] bg-surface border-r border-border z-50
        transform transition-transform duration-300 ease-out
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        overflow-y-auto shadow-2xl
      `}>
        {/* Sidebar Header */}
        <div className="sticky top-0 bg-surface border-b border-border p-4 flex items-center justify-between z-10">
          <h2 className="font-semibold text-text-primary">Controls</h2>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="p-2 hover:bg-surface-elevated rounded-lg transition-colors text-text-secondary hover:text-text-primary"
            aria-label="Close sidebar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Sidebar Content */}
        <div className="p-4 space-y-4">
          {/* Session Controls */}
          <SessionControls />
          
          <div className="border-t border-border/50" />
          
          {/* Context Documents */}
          <ContextLoader />
          
          <div className="border-t border-border/50" />
          
          {/* Preparation Guide */}
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text-primary">Preparation</h3>
                <p className="text-xs text-text-muted">Based on your docs</p>
              </div>
            </div>
            <PreparationButton disabled={loadedContextFiles.length === 0} />
          </div>
        </div>
      </aside>

      {/* Main Content Area - Full Width */}
      <div className="min-h-screen flex flex-col transition-all duration-300">
        {/* Minimal Header */}
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-md border-b border-border/50">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
            {/* Left: Hamburger + Logo + Status */}
            <div className="flex items-center gap-3">
              {/* Hamburger Menu */}
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 hover:bg-surface-elevated rounded-lg transition-colors text-text-secondary hover:text-text-primary"
                title="Open controls"
                aria-label="Open controls"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              {/* Logo */}
              <div className="w-8 h-8 hidden sm:block">
                <svg viewBox="0 0 40 40" className="w-full h-full">
                  <defs>
                    <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#06b6d4" />
                      <stop offset="100%" stopColor="#3b82f6" />
                    </linearGradient>
                  </defs>
                  <rect x="4" y="14" width="4" height="12" rx="2" fill="url(#logoGradient)" opacity="0.6"/>
                  <rect x="12" y="8" width="4" height="24" rx="2" fill="url(#logoGradient)" opacity="0.8"/>
                  <rect x="20" y="4" width="4" height="32" rx="2" fill="url(#logoGradient)"/>
                  <rect x="28" y="10" width="4" height="20" rx="2" fill="url(#logoGradient)" opacity="0.8"/>
                  <rect x="36" y="16" width="4" height="8" rx="2" fill="url(#logoGradient)" opacity="0.6"/>
                </svg>
              </div>

              {/* Status Pill */}
              <div className={`
                flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors duration-300
                ${status === 'idle' ? 'bg-surface-elevated text-text-secondary' : 'bg-surface-elevated/80 border border-border'}
              `}>
                <span className={`w-1.5 h-1.5 rounded-full ${statusInfo.color} ${statusInfo.pulse ? 'animate-pulse' : ''}`} />
                <span className="text-text-secondary">{statusInfo.text}</span>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <button
                onClick={() => setIsSettingsOpen(true)}
                className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface-elevated rounded-lg transition-colors"
                title="Settings"
                aria-label="Settings"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </button>
              <button
                onClick={() => setIsHistoryOpen(true)}
                className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface-elevated rounded-lg transition-colors"
                title="History"
                aria-label="History"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        {/* Main Content - Centered Answer Display */}
        <main className="flex-1 flex flex-col p-4 lg:p-6">
          <div className="max-w-4xl w-full mx-auto flex-1 flex flex-col gap-4">
            {/* Preparation Summary (collapsible, only shows when ready) */}
            <PreparationSummary 
              summary={preparationSummary} 
              isExpanded={isPreparationExpanded} 
              onToggle={() => setPreparationExpanded(!isPreparationExpanded)} 
            />
            
            {/* Coaching Panel */}
            <CoachingPanel />
            
            {/* Answer Display - THE MAIN FOCUS */}
            <div className="flex-1 min-h-[500px]">
              <AnswerDisplay />
            </div>
          </div>
        </main>
      </div>

      {/* Modals */}
      <CalibrationModal />
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
      <HistoryPanel isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />
    </div>
  );
}

export default App;
