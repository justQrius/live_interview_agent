import React, { useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

const SessionControls: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const setStatus = useSessionStore((state) => state.setStatus);
  const clearSession = useSessionStore((state) => state.clearSession);
  const apiKey = useSessionStore((state) => state.apiKey);
  const setCurrentAnswer = useSessionStore((state) => state.setCurrentAnswer);
  const { sendMessage, isConnected } = useWebSocket();

  const [manualQuestion, setManualQuestion] = useState('');
  const [showStopConfirm, setShowStopConfirm] = useState(false);

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
    setShowStopConfirm(true);
  };

  const confirmStopSession = () => {
    sendMessage({ type: 'STOP_SESSION' });
    clearSession();
    setManualQuestion('');
    setShowStopConfirm(false);
  };

  const cancelStopSession = () => {
    setShowStopConfirm(false);
  };

  const handleSendManualQuestion = () => {
    const trimmedQuestion = manualQuestion.trim();
    if (!trimmedQuestion || !isConnected || status !== 'listening') {
      return;
    }

    // Clear current answer before sending new question
    setCurrentAnswer(null);

    sendMessage({
      type: 'MANUAL_QUESTION',
      data: { question: trimmedQuestion }
    });
    setManualQuestion('');
  };

  const handleQuestionKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendManualQuestion();
    }
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

      {/* Manual Question Input */}
      {status === 'listening' && (
        <div className="mt-4 space-y-2">
          <label htmlFor="manual-question" className="block text-sm font-medium text-gray-700">
            Ask a Question Manually
          </label>
          <textarea
            id="manual-question"
            value={manualQuestion}
            onChange={(e) => setManualQuestion(e.target.value)}
            onKeyDown={handleQuestionKeyDown}
            placeholder="Type a question and press Enter to send..."
            className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            disabled={!isConnected || status !== 'listening'}
          />
          <button
            onClick={handleSendManualQuestion}
            disabled={!manualQuestion.trim() || !isConnected || status !== 'listening'}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200"
          >
            Send Question
          </button>
        </div>
      )}

      <div className="mt-4 p-3 bg-gray-100 rounded">
        <p className="text-sm text-gray-600">
          Status: <span className={`font-medium ${getStatusColor()}`}>{getStatusText()}</span>
        </p>
      </div>

      {/* Stop Session Confirmation Modal */}
      {showStopConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-2">Stop Session?</h3>
            <p className="text-gray-600 mb-4">
              This will stop the current session and clear all transcriptions and answers.
              This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={cancelStopSession}
                className="px-4 py-2 text-gray-700 bg-gray-200 hover:bg-gray-300 rounded-lg transition duration-200"
              >
                Cancel
              </button>
              <button
                onClick={confirmStopSession}
                className="px-4 py-2 text-white bg-red-600 hover:bg-red-700 rounded-lg transition duration-200"
              >
                Stop Session
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionControls;
