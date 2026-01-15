import React, { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

const SessionControls: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const setStatus = useSessionStore((state) => state.setStatus);
  const clearSession = useSessionStore((state) => state.clearSession);
  const cancelEnhancement = useSessionStore((state) => state.cancelEnhancement);
  const preferredSttProvider = useSessionStore((state) => state.preferredSttProvider);
  const setCurrentAnswer = useSessionStore((state) => state.setCurrentAnswer);
  const { sendMessage, isConnected } = useWebSocket();

  const [manualQuestion, setManualQuestion] = useState('');
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [hasPrimaryKey, setHasPrimaryKey] = useState<boolean | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    const checkKey = () => {
      const provider = preferredSttProvider === 'auto' ? 'gemini' : preferredSttProvider;
      invoke<{ exists: boolean }>('has_api_key', { provider })
        .then((status) => {
          if (isMounted) {
            setHasPrimaryKey(status.exists);
          }
        })
        .catch(() => {
          if (isMounted) {
            setHasPrimaryKey(false);
          }
        });
    };

    checkKey();

    const handleApiKeyChange = () => {
      checkKey();
    };

    window.addEventListener('apiKeyChanged', handleApiKeyChange as EventListener);

    return () => {
      isMounted = false;
      window.removeEventListener('apiKeyChanged', handleApiKeyChange as EventListener);
    };
  }, [preferredSttProvider]);

  const handleStartSession = async () => {
    if (!isConnected) {
      console.error('Cannot start session: WebSocket not connected');
      return;
    }

    if (hasPrimaryKey !== true) {
      console.error('Cannot start session: API key missing for selected STT provider');
      return;
    }

    setStatus('listening');

    const providers = ['gemini', 'groq', 'deepgram', 'openai', 'anthropic'];
    const apiKeys: Record<string, string> = {};

    for (const provider of providers) {
      try {
        const key = await invoke<string>('get_api_key', { provider });
        if (key) {
          apiKeys[provider] = key;
        }
      } catch (err) {
        // Ignore missing keys
      }
    }

    const prefs = {
      sttProvider: useSessionStore.getState().preferredSttProvider,
      llmProvider: useSessionStore.getState().preferredLlmProvider,
    };

    sendMessage({ 
      type: 'START_SESSION', 
      data: { 
        apiKeys, 
        preferences: prefs 
      } 
    });
  };

  const handleStopSession = () => {
    setShowStopConfirm(true);
  };

  const confirmStopSession = () => {
    // Cancel any ongoing enhancement first
    sendMessage({ type: 'CANCEL_ENHANCEMENT' });
    cancelEnhancement();
    
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

      <div className="mb-4">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Connected to sidecar' : 'Disconnected'}
          </span>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          API Key Status: {hasPrimaryKey === null ? 'Checking...' : hasPrimaryKey ? '✅ Found' : '❌ Not configured'}
          {' '}(Provider: {preferredSttProvider === 'auto' ? 'gemini (auto)' : preferredSttProvider})
        </div>
      </div>

      <div className="space-y-3">
        <button
          onClick={handleStartSession}
          disabled={status !== 'idle' || !isConnected || hasPrimaryKey !== true}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition duration-200"
        >
          {hasPrimaryKey !== true ? 'Configure API Key First' : 'Start Session'}
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
