import React from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

const SessionControls: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const setStatus = useSessionStore((state) => state.setStatus);
  const clearSession = useSessionStore((state) => state.clearSession);
  const apiKey = useSessionStore((state) => state.apiKey);
  const { sendMessage, isConnected } = useWebSocket();

  const handleStartSession = () => {
    if (!isConnected) {
      console.error('Cannot start session: WebSocket not connected');
      return;
    }
    if (!apiKey) {
      console.error('Cannot start session: API key not configured');
      return;
    }

    // SECURITY: API key sent in plaintext - development only until STORY-004
    // In production, this should use secure keychain storage via Tauri commands
    if (import.meta.env.PROD) {
      console.warn(
        'SECURITY WARNING: API key transmission not using secure keychain. ' +
          'See STORY-004 for production-ready implementation.'
      );
    }

    sendMessage({ type: 'START_SESSION', data: { apiKey } });
    setStatus('listening');
  };

  const handleStopSession = () => {
    sendMessage({ type: 'STOP_SESSION' });
    clearSession();
  };

  const handleCalibrateVoice = () => {
    setStatus('calibrating');
    // Don't send message yet, let CalibrationModal handle the recording and sending
  };

  const getStatusColor = () => {
    switch (status) {
      case 'listening':
        return 'text-green-600';
      case 'processing':
        return 'text-blue-600';
      case 'calibrating':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusText = () => {
    const statusMap = {
      idle: 'Idle',
      listening: 'Listening...',
      processing: 'Processing...',
      calibrating: 'Calibrating...',
    };
    return statusMap[status];
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Session Controls</h2>

      <div className="mb-4 flex items-center gap-2">
        <span
          className={`inline-block w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}
        />
        <span className="text-sm text-gray-600">
          {isConnected ? 'Connected to sidecar' : 'Disconnected'}
        </span>
      </div>

      <div className="space-y-3">
        <button
          onClick={handleStartSession}
          disabled={status !== 'idle' || !isConnected || !apiKey}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition duration-200"
        >
          {!apiKey ? 'Configure API Key First' : 'Start Session'}
        </button>
        <button
          onClick={handleStopSession}
          disabled={status === 'idle'}
          className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition duration-200"
        >
          Stop Session
        </button>
        <button
          onClick={handleCalibrateVoice}
          disabled={status !== 'idle' || !isConnected}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition duration-200"
        >
          Calibrate Voice
        </button>
      </div>
      <div className="mt-4 p-3 bg-gray-100 rounded">
        <p className="text-sm text-gray-600">
          Status: <span className={`font-medium ${getStatusColor()}`}>{getStatusText()}</span>
        </p>
      </div>
    </div>
  );
};

export default SessionControls;
