import { useState } from 'react';
import SessionControls from './components/SessionControls';
import AnswerDisplay from './components/AnswerDisplay';
import ContextLoader from './components/ContextLoader';
import CalibrationModal from './components/CalibrationModal';
import SettingsPanel from './components/SettingsPanel';
import { DebugPanel } from './components/DebugPanel';
import { HistoryPanel } from './components/HistoryPanel';

function App() {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-800">Live Interview Agent</h1>
        <button
          onClick={() => setIsHistoryOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors shadow-sm"
          title="View session history"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          History
        </button>
      </header>

      <main className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <SessionControls />
          <ContextLoader />
          <SettingsPanel />
        </div>

        <div>
          <AnswerDisplay />
        </div>
      </main>

      <CalibrationModal />
      <DebugPanel />
      <HistoryPanel isOpen={isHistoryOpen} onClose={() => setIsHistoryOpen(false)} />
    </div>
  );
}

export default App;
