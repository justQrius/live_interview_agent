import { useState } from 'react';
import { useSessionStore } from './store/sessionStore';
import SessionControls from './components/SessionControls';
import AnswerDisplay from './components/AnswerDisplay';
import ContextLoader from './components/ContextLoader';
import CalibrationModal from './components/CalibrationModal';
import SettingsModal from './components/SettingsModal';
import { DebugPanel } from './components/DebugPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { PreparationButton } from './components/PreparationButton';
import { PreparationSummary } from './components/PreparationSummary';
import { CoachingPanel } from './components/CoachingPanel';
import { ThemeToggle } from './components/ThemeToggle';

function App() {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  
  const preparationSummary = useSessionStore((state) => state.preparationSummary);
  const isPreparationExpanded = useSessionStore((state) => state.isPreparationExpanded);
  const setPreparationExpanded = useSessionStore((state) => state.setPreparationExpanded);
  const loadedContextFiles = useSessionStore((state) => state.loadedContextFiles);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-background dark:to-background text-text-primary transition-colors duration-300">
      <div className="mx-auto max-w-[1800px] p-4 lg:p-6 h-screen flex flex-col">
        <header className="mb-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/20 text-white font-bold text-xl">
              IA
            </div>
            <div>
              <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-900 to-slate-700 dark:from-white dark:to-slate-300">
                Live Interview Agent
              </h1>
              <p className="text-xs text-text-muted">AI-Powered Assistant</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface-elevated rounded-lg transition-colors"
              title="Settings"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <div className="w-px h-6 bg-border mx-1" />
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-surface border border-border rounded-lg hover:bg-slate-50 dark:hover:bg-surface-elevated text-text-secondary transition-all shadow-sm hover:shadow active:scale-95"
              title="View session history"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              History
            </button>
          </div>
        </header>

        <main className="grid grid-cols-1 gap-6 lg:grid-cols-[400px_1fr] flex-1 min-h-0">
          <div className="space-y-6 overflow-y-auto pr-2 scrollbar-thin">
            <SessionControls />
            <ContextLoader />
            
            <div className="bg-surface rounded-xl shadow-sm border border-border p-5 dark:shadow-none">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg text-purple-600 dark:text-purple-400">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div>
                  <h2 className="text-base font-semibold text-text-primary">Preparation Guide</h2>
                  <p className="text-xs text-text-muted">Based on your documents</p>
                </div>
              </div>
              <PreparationButton disabled={loadedContextFiles.length === 0} />
            </div>
          </div>

          <div className="space-y-6 flex flex-col min-h-0">
            <PreparationSummary 
              summary={preparationSummary} 
              isExpanded={isPreparationExpanded} 
              onToggle={() => setPreparationExpanded(!isPreparationExpanded)} 
            />
            <div className="flex-1 flex flex-col min-h-0 gap-6">
              <div className="shrink-0">
                <CoachingPanel />
              </div>
              <div className="flex-1 min-h-0">
                <AnswerDisplay />
              </div>
            </div>
          </div>
        </main>

        <CalibrationModal />
        <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        <DebugPanel />
        <HistoryPanel isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />
      </div>
    </div>
  );
}

export default App;
