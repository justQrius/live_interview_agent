import SessionControls from './components/SessionControls';
import AnswerDisplay from './components/AnswerDisplay';
import ContextLoader from './components/ContextLoader';
import CalibrationModal from './components/CalibrationModal';
import SettingsPanel from './components/SettingsPanel';
import { DebugPanel } from './components/DebugPanel';

function App() {
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <header className="mb-4">
        <h1 className="text-3xl font-bold text-gray-800">Live Interview Agent</h1>
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
    </div>
  );
}

export default App;
