import React, { useEffect, useState, useMemo } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

const SessionControls: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const setStatus = useSessionStore((state) => state.setStatus);
  const clearSession = useSessionStore((state) => state.clearSession);
  const cancelEnhancement = useSessionStore((state) => state.cancelEnhancement);
  const preferredSttProvider = useSessionStore((state) => state.preferredSttProvider);
  const addTranscription = useSessionStore((state) => state.addTranscription);
  const startAnswer = useSessionStore((state) => state.startAnswer);
  const setInterimTranscript = useSessionStore((state) => state.setInterimTranscript);
  const loadedContextFiles = useSessionStore((state) => state.loadedContextFiles);
  const { sendMessage, isConnected } = useWebSocket();

  const [manualQuestion, setManualQuestion] = useState('');
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [hasPrimaryKey, setHasPrimaryKey] = useState<boolean | null>(null);

  // Calculate document readiness status
  const documentStatus = useMemo(() => {
    const total = loadedContextFiles.length;
    if (total === 0) return { status: 'none', message: 'No documents uploaded', color: 'text-gray-500' };
    
    const ready = loadedContextFiles.filter(f => f.status === 'ready').length;
    const processing = loadedContextFiles.filter(f => f.status === 'processing').length;
    const pending = loadedContextFiles.filter(f => f.status === 'pending').length;
    const errors = loadedContextFiles.filter(f => f.status === 'error').length;
    
    if (processing > 0 || pending > 0) {
      return { 
        status: 'processing', 
        message: `Processing documents (${ready}/${total} ready)`, 
        color: 'text-blue-600'
      };
    }
    if (errors > 0 && ready === 0) {
      return { 
        status: 'error', 
        message: `Document processing failed`, 
        color: 'text-red-600'
      };
    }
    if (ready === total) {
      return { 
        status: 'ready', 
        message: `✓ ${total} document${total > 1 ? 's' : ''} ready`, 
        color: 'text-green-600'
      };
    }
    return { 
      status: 'partial', 
      message: `${ready}/${total} documents ready`, 
      color: 'text-yellow-600'
    };
  }, [loadedContextFiles]);

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
    if (!trimmedQuestion || !isConnected || status !== "listening") {
      return;
    }

    const timestamp = Date.now();
    
    // Update local state so UI reflects the manual question immediately
    addTranscription({
      speaker: "Interviewer",
      text: trimmedQuestion,
      timestamp,
      confidence: 1.0,
    });
    
    // Prepare answer buffer with the question
    startAnswer(trimmedQuestion, timestamp);
    setInterimTranscript(null);

    sendMessage({
      type: "MANUAL_QUESTION",
      data: { question: trimmedQuestion }
    });
    setManualQuestion("");
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
    <div className="bg-surface rounded-xl shadow-sm border border-border p-5 dark:shadow-none transition-colors">
      {/* Header with Status Badge */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 dark:text-blue-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-text-primary">Session Controls</h2>
            <p className="text-xs text-text-muted">Manage your interview session</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
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

      {/* Status Cards */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        {/* Connection Status */}
        <div className={`p-3 rounded-lg border ${
          isConnected 
            ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30' 
            : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/30'
        }`}>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className={`text-xs font-medium ${isConnected ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <p className="text-xs text-text-muted mt-1">Sidecar</p>
        </div>

        {/* API Key Status */}
        <div className={`p-3 rounded-lg border ${
          hasPrimaryKey === true 
            ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30' 
            : 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-900/30'
        }`}>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${hasPrimaryKey === true ? 'bg-green-500' : hasPrimaryKey === false ? 'bg-amber-500' : 'bg-slate-400 animate-pulse'}`} />
            <span className={`text-xs font-medium ${hasPrimaryKey === true ? 'text-green-700 dark:text-green-400' : 'text-amber-700 dark:text-amber-400'}`}>
              {hasPrimaryKey === null ? 'Checking...' : hasPrimaryKey ? 'API Ready' : 'Not Configured'}
            </span>
          </div>
          <p className="text-xs text-text-muted mt-1 capitalize">{preferredSttProvider === 'auto' ? 'Gemini' : preferredSttProvider}</p>
        </div>
      </div>

      {/* Document Status */}
      <div className={`mb-5 p-3 rounded-lg border ${
        documentStatus.status === 'ready' ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-900/30' :
        documentStatus.status === 'processing' ? 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-900/30' :
        documentStatus.status === 'error' ? 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-900/30' :
        'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'
      }`}>
        <div className="flex items-center gap-2">
          {documentStatus.status === 'processing' && (
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
          )}
          {documentStatus.status === 'ready' && (
            <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          )}
          {documentStatus.status === 'none' && (
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          )}
          <span className={`text-xs font-medium ${
            documentStatus.status === 'ready' ? 'text-green-700 dark:text-green-400' :
            documentStatus.status === 'processing' ? 'text-blue-700 dark:text-blue-400' :
            documentStatus.status === 'error' ? 'text-red-700 dark:text-red-400' :
            'text-text-secondary'
          }`}>{documentStatus.message}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="space-y-2">
        <button
          onClick={handleStartSession}
          disabled={status !== 'idle' || !isConnected || hasPrimaryKey !== true}
          className="w-full bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-700 dark:disabled:to-slate-800 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow active:scale-[0.98] flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {hasPrimaryKey !== true ? 'Configure API Key First' : 'Start Session'}
        </button>
        
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={handleStopSession}
            disabled={status === 'idle'}
            className="bg-surface border border-red-200 dark:border-red-900/30 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:border-slate-200 dark:disabled:border-slate-700 disabled:hover:bg-surface disabled:cursor-not-allowed font-medium py-2.5 px-4 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
            </svg>
            Stop
          </button>
          <button
            onClick={handleCalibrateVoice}
            disabled={status !== 'idle' || !isConnected}
            className="bg-surface border border-blue-200 dark:border-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:text-slate-400 dark:disabled:text-slate-600 disabled:border-slate-200 dark:disabled:border-slate-700 disabled:hover:bg-surface disabled:cursor-not-allowed font-medium py-2.5 px-4 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
            </svg>
            Calibrate
          </button>
        </div>
      </div>

      {/* Manual Question Input */}
      {status === 'listening' && (
        <div className="mt-5 pt-5 border-t border-border">
          <label htmlFor="manual-question" className="block text-sm font-medium text-text-primary mb-2">
            Ask a Question Manually
          </label>
          <textarea
            id="manual-question"
            value={manualQuestion}
            onChange={(e) => setManualQuestion(e.target.value)}
            onKeyDown={handleQuestionKeyDown}
            placeholder="Type a question and press Enter to send..."
            className="w-full p-3 bg-slate-50 dark:bg-slate-800 border border-border rounded-lg resize-none focus:ring-2 focus:ring-primary focus:border-transparent text-text-primary placeholder:text-text-muted transition-colors"
            rows={3}
            disabled={!isConnected || status !== 'listening'}
          />
          <button
            onClick={handleSendManualQuestion}
            disabled={!manualQuestion.trim() || !isConnected || status !== 'listening'}
            className="mt-2 w-full bg-gradient-to-r from-violet-500 to-violet-600 hover:from-violet-600 hover:to-violet-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-700 dark:disabled:to-slate-800 disabled:cursor-not-allowed text-white font-medium py-2.5 px-4 rounded-lg transition-all duration-200 shadow-sm hover:shadow active:scale-[0.98] flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            Send Question
          </button>
        </div>
      )}

      {/* Stop Session Confirmation Modal */}
      {showStopConfirm && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-surface rounded-xl shadow-2xl p-6 max-w-md w-full mx-4 border border-border">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-text-primary">Stop Session?</h3>
            </div>
            <p className="text-text-secondary mb-6">
              This will stop the current session and clear all transcriptions and answers.
              This action cannot be undone.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={cancelStopSession}
                className="px-4 py-2 text-text-secondary bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmStopSession}
                className="px-4 py-2 text-white bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 rounded-lg transition-all shadow-sm hover:shadow"
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
