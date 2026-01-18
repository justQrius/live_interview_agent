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
  const { sendMessage, isConnected } = useWebSocket();

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
      // Model selections (Phase 7)
      llmModel: useSessionStore.getState().preferredLlmModel,
      sttModel: useSessionStore.getState().preferredSttModel,
      streamingSttProvider: useSessionStore.getState().preferredStreamingSttProvider,
      streamingSttModel: useSessionStore.getState().preferredStreamingSttModel,
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
    setShowStopConfirm(false);
  };

  const cancelStopSession = () => {
    setShowStopConfirm(false);
  };

  const handleCalibrateVoice = () => {
    setStatus('calibrating');
    // Don't send message yet, let CalibrationModal handle the recording and sending
  };

  const getStatusText = () => {
    const statusMap = {
      idle: 'Idle',
      listening: 'Listening',
      processing: 'Processing',
      calibrating: 'Calibrating',
    };
    return statusMap[status];
  };

  return (
    <div className="space-y-4">
      {/* Compact Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">Session Controls</h2>
        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${
          status === 'listening' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
          status === 'processing' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
          status === 'calibrating' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
          'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            status === 'listening' ? 'bg-green-500 animate-pulse' :
            status === 'processing' ? 'bg-blue-500 animate-pulse' :
            status === 'calibrating' ? 'bg-amber-500 animate-pulse' :
            'bg-slate-400'
          }`} />
          {getStatusText()}
        </span>
      </div>

      {/* Status Grid - Compact */}
      <div className="grid grid-cols-2 gap-2">
        {/* Connection Status */}
        <div className={`p-2 rounded-md border text-xs ${
          isConnected 
            ? 'bg-green-50/50 dark:bg-green-900/10 border-green-100 dark:border-green-900/20' 
            : 'bg-red-50/50 dark:bg-red-900/10 border-red-100 dark:border-red-900/20'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-text-muted">Sidecar</span>
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          </div>
          <div className={`font-medium ${isConnected ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
            {isConnected ? 'Connected' : 'Offline'}
          </div>
        </div>

        {/* API Key Status */}
        <div className={`p-2 rounded-md border text-xs ${
          hasPrimaryKey === true 
            ? 'bg-green-50/50 dark:bg-green-900/10 border-green-100 dark:border-green-900/20' 
            : 'bg-amber-50/50 dark:bg-amber-900/10 border-amber-100 dark:border-amber-900/20'
        }`}>
          <div className="flex items-center justify-between mb-1">
            <span className="text-text-muted capitalize truncate pr-1">{preferredSttProvider === 'auto' ? 'Gemini' : preferredSttProvider}</span>
            <span className={`w-1.5 h-1.5 rounded-full ${hasPrimaryKey === true ? 'bg-green-500' : hasPrimaryKey === false ? 'bg-amber-500' : 'bg-slate-400'}`} />
          </div>
          <div className={`font-medium ${hasPrimaryKey === true ? 'text-green-700 dark:text-green-400' : 'text-amber-700 dark:text-amber-400'}`}>
            {hasPrimaryKey === null ? 'Checking...' : hasPrimaryKey ? 'Ready' : 'Config Needed'}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2">
        <button
          onClick={handleStartSession}
          disabled={status !== 'idle' || !isConnected || hasPrimaryKey !== true}
          className="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-700 dark:disabled:to-slate-800 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow active:scale-[0.98] flex items-center justify-center gap-2"
        >
          {status === 'idle' ? (
             <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          )}
          {hasPrimaryKey !== true ? 'Configure Key' : status === 'idle' ? 'Start Session' : 'Session Active'}
        </button>
        
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleStopSession}
            disabled={status === 'idle'}
            className="bg-white dark:bg-surface-elevated border border-red-200 dark:border-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:border-slate-200 dark:disabled:border-slate-800 disabled:hover:bg-white dark:disabled:hover:bg-surface-elevated disabled:cursor-not-allowed text-sm font-medium py-2 px-3 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            Stop
          </button>
          <button
            onClick={handleCalibrateVoice}
            disabled={status !== 'idle' || !isConnected}
            className="bg-white dark:bg-surface-elevated border border-blue-200 dark:border-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:border-slate-200 dark:disabled:border-slate-800 disabled:hover:bg-white dark:disabled:hover:bg-surface-elevated disabled:cursor-not-allowed text-sm font-medium py-2 px-3 rounded-lg transition-all duration-200 flex items-center justify-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
            Calibrate
          </button>
        </div>
      </div>

      {/* Stop Session Confirmation Modal */}
      {showStopConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-surface rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 border border-border">
            <h3 className="text-lg font-semibold text-text-primary mb-2">Stop Session?</h3>
            <p className="text-sm text-text-secondary mb-5">
              This will clear all transcriptions and answers.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={cancelStopSession}
                className="px-3 py-1.5 text-sm text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmStopSession}
                className="px-3 py-1.5 text-sm text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
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
