import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { 
  useSessionStore, 
  StorySuggestion, 
  StructureHint, 
  Contradiction 
} from '../store/sessionStore';

// WebSocket message types (as per architecture)
export type MessageType =
  | 'START_SESSION'
  | 'STOP_SESSION'
  | 'UPLOAD_CONTEXT'
  | 'CALIBRATE_VOICE'
  | 'MANUAL_QUESTION'
  | 'AUDIO_CHUNK'
  | 'TRANSCRIPTION'
  | 'ANSWER_START'
  | 'ANSWER_CHUNK'
  | 'ERROR'
  | 'STATUS'
  // Preparation (STORY-047/048)
  | 'PREPARE_INTERVIEW'
  | 'PREPARATION_READY'
  // Session History (Phase 3: STORY-039)
  | 'LIST_SESSIONS'
  | 'LOAD_SESSION'
  | 'EXPORT_SESSION'
  | 'DELETE_SESSION'
  | 'SESSION_LIST'
  | 'SESSION_DATA'
  | 'SESSION_EXPORT'
  | 'SESSION_DELETED'
  // Coaching (Phase 4E: STORY-070)
  | 'STORY_SUGGESTION'
  | 'STRUCTURE_SUGGESTION'
  | 'CONSISTENCY_WARNING'
  | 'INTERIM_TRANSCRIPTION'
  // Answer Enhancement (Phase 5)
  | 'ENHANCE_ANSWER'
  | 'ENHANCED_ANSWER_START'
  | 'ENHANCED_ANSWER_CHUNK'
  | 'ENHANCED_ANSWER_COMPLETE'
  // Document Type Inference (Phase 5)
  | 'INFER_DOCUMENT_TYPES'
  | 'DOCUMENT_TYPE_SUGGESTIONS';

export interface WebSocketMessage {
  type: MessageType;
  data?: unknown;
}

const WS_URL = 'ws://localhost:8765';

type ConnectionListener = (connected: boolean) => void;

let sharedWs: WebSocket | null = null;
let sharedIsConnected = false;
let subscriberCount = 0;
let reconnectTimeoutId: number | undefined;

const connectionListeners = new Set<ConnectionListener>();

// Custom message handlers for components that need raw message access
type MessageHandler = (message: WebSocketMessage) => void;
const customMessageHandlers = new Set<MessageHandler>();

const notifyConnectionListeners = () => {
  for (const listener of connectionListeners) {
    listener(sharedIsConnected);
  }
};

const clearReconnectTimeout = () => {
  if (reconnectTimeoutId !== undefined) {
    clearTimeout(reconnectTimeoutId);
    reconnectTimeoutId = undefined;
  }
};

const scheduleReconnect = () => {
  if (reconnectTimeoutId !== undefined) return;
  reconnectTimeoutId = window.setTimeout(() => {
    reconnectTimeoutId = undefined;
    connectSharedWebSocket();
  }, 5000);
};

const handleIncomingMessage = (message: WebSocketMessage) => {
  const store = useSessionStore.getState();

  // Notify custom handlers first (for component-level handling)
  for (const handler of customMessageHandlers) {
    try {
      handler(message);
    } catch (e) {
      console.error('Custom message handler error:', e);
    }
  }

  switch (message.type) {
    case 'TRANSCRIPTION': {
      const data = message.data as {
        speaker: 'User' | 'Interviewer';
        text: string;
        timestamp: number;
        confidence: number;
      };

      // When interviewer asks a new question, start a fresh answer buffer
      // This clears the previous answer and associates the new question text
      if (data.speaker === 'Interviewer') {
        store.startAnswer(data.text, data.timestamp);
        store.setInterimTranscript(null); // Clear interim on final
      }

      store.addTranscription(data);
      break;
    }

    case 'ANSWER_START': {
      store.startAnswer('', Date.now());
      break;
    }

    case 'ANSWER_CHUNK': {
      const data = message.data as {
        chunk: string;
        complete: boolean;
        confidence?: 'high' | 'medium' | 'low';
      };
      store.appendAnswerText(data.chunk);
      if (data.complete && data.confidence) {
        store.completeAnswer(data.confidence);
      }
      break;
    }

    case 'STATUS': {
      const data = message.data as {
        state: 'listening' | 'processing' | 'idle' | 'calibrating';
      };
      store.setStatus(data.state);
      break;
    }

    case 'PREPARATION_READY': {
      const data = message.data as { summary: string };
      store.setPreparationStatus('ready');
      store.setPreparationSummary(data.summary);
      store.setPreparationExpanded(true);
      break;
    }

    case 'ERROR': {
      const data = message.data as { message: string };
      console.error('Python sidecar error:', data.message);
      store.setLastError(data.message);
      break;
    }

    // Session History responses (Phase 3: STORY-040)
    case 'SESSION_LIST': {
      const data = message.data as {
        sessions: Array<{
          id: string;
          startedAt: number;
          endedAt: number | null;
          contextFiles: string[];
          transcriptionCount: number;
          answerCount: number;
        }>;
        total: number;
        hasMore: boolean;
      };
      store.setSavedSessions(data.sessions);
      store.setHistoryLoading(false);
      break;
    }

    case 'SESSION_DATA': {
      const data = message.data as {
        id: string;
        startedAt: number;
        endedAt: number | null;
        contextFiles: string[];
        transcriptions: Array<{
          speaker: 'User' | 'Interviewer';
          text: string;
          timestamp: number;
          confidence: number;
        }>;
        answers: Array<{
          question: string;
          answer: string;
          confidence: string;
          timestamp?: number;
          latency_ms?: number;
        }>;
      };
      store.setSelectedSession(data);
      store.setHistoryLoading(false);
      break;
    }

    case 'SESSION_DELETED': {
      const data = message.data as { sessionId: string; success: boolean };
      if (data.success) {
        store.removeSession(data.sessionId);
      }
      store.setHistoryLoading(false);
      break;
    }

    // Coaching messages (Phase 4E)
    case 'STORY_SUGGESTION': {
      const data = message.data as StorySuggestion;
      store.setStorySuggestion(data);
      break;
    }

    case 'STRUCTURE_SUGGESTION': {
      const data = message.data as StructureHint;
      store.setStructureHint(data);
      break;
    }

    case 'CONSISTENCY_WARNING': {
      const data = message.data as { contradictions: Contradiction[] };
      store.setConsistencyWarnings(data.contradictions);
      break;
    }

    case 'INTERIM_TRANSCRIPTION': {
      const data = message.data as { text: string; speaker: string };
      if (data.speaker === 'Interviewer') {
        store.setInterimTranscript(data.text);
      }
      break;
    }

    // Enhancement messages (Phase 5)
    case 'ENHANCED_ANSWER_START': {
      // Enhancement already started via UI, this confirms server received
      break;
    }

    case 'ENHANCED_ANSWER_CHUNK': {
      const data = message.data as { chunk: string; complete: boolean };
      store.appendEnhancedText(data.chunk);
      break;
    }

    case 'ENHANCED_ANSWER_COMPLETE': {
      store.completeEnhancement();
      break;
    }

    default:
      console.warn('Unknown message type:', message.type);
  }
};

const connectSharedWebSocket = () => {
  // If nothing is using the socket, don't maintain a connection.
  if (subscriberCount <= 0) return;

  if (sharedWs && (sharedWs.readyState === WebSocket.OPEN || sharedWs.readyState === WebSocket.CONNECTING)) {
    return;
  }

  clearReconnectTimeout();

  try {
    const ws = new WebSocket(WS_URL);
    sharedWs = ws;

    ws.onopen = () => {
      sharedIsConnected = true;
      notifyConnectionListeners();
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        handleIncomingMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      sharedIsConnected = false;
      sharedWs = null;
      notifyConnectionListeners();

      if (subscriberCount > 0) {
        scheduleReconnect();
      }
    };
  } catch (error) {
    console.error('Failed to create WebSocket connection:', error);
    if (subscriberCount > 0) {
      scheduleReconnect();
    }
  }
};

const closeSharedWebSocket = () => {
  clearReconnectTimeout();

  if (sharedWs) {
    try {
      sharedWs.close();
    } catch {
      // Ignore
    }
    sharedWs = null;
  }

  sharedIsConnected = false;
  notifyConnectionListeners();
};

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(sharedIsConnected);

  useEffect(() => {
    subscriberCount += 1;

    const onConnectionChange: ConnectionListener = (connected) => {
      setIsConnected(connected);
    };

    connectionListeners.add(onConnectionChange);

    // Sync immediately (in case connection state changed before subscription).
    setIsConnected(sharedIsConnected);

    connectSharedWebSocket();

    return () => {
      connectionListeners.delete(onConnectionChange);
      subscriberCount -= 1;

      if (subscriberCount <= 0) {
        closeSharedWebSocket();
      }
    };
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    if (sharedWs && sharedWs.readyState === WebSocket.OPEN) {
      sharedWs.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  };

  const sendAudio = (audioData: string) => {
    sendMessage({
      type: 'AUDIO_CHUNK',
      data: {
        audioData,
        timestamp: Date.now(),
      },
    });
  };

  // Session History operations (Phase 3: STORY-040)
  const listSessions = (limit = 20, offset = 0) => {
    const store = useSessionStore.getState();
    store.setHistoryLoading(true);
    sendMessage({
      type: 'LIST_SESSIONS',
      data: { limit, offset },
    });
  };

  const loadSession = (sessionId: string) => {
    const store = useSessionStore.getState();
    store.setHistoryLoading(true);
    sendMessage({
      type: 'LOAD_SESSION',
      data: { sessionId },
    });
  };

  const exportSession = (sessionId: string, format: 'md' | 'json' = 'md'): Promise<string> => {
    return new Promise((resolve, reject) => {
      // Set up one-time listener for export response
      const handleExport = (event: MessageEvent) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'SESSION_EXPORT') {
            resolve(message.data.content);
            sharedWs?.removeEventListener('message', handleExport);
          }
        } catch {
          // Ignore parse errors for other messages
        }
      };

      if (sharedWs) {
        sharedWs.addEventListener('message', handleExport);
        sendMessage({
          type: 'EXPORT_SESSION',
          data: { sessionId, format },
        });

        // Timeout after 10 seconds
        setTimeout(() => {
          sharedWs?.removeEventListener('message', handleExport);
          reject(new Error('Export timed out'));
        }, 10000);
      } else {
        reject(new Error('WebSocket not connected'));
      }
    });
  };

  const deleteSession = (sessionId: string) => {
    const store = useSessionStore.getState();
    store.setHistoryLoading(true);
    sendMessage({
      type: 'DELETE_SESSION',
      data: { sessionId },
    });
  };

  const requestPreparation = async () => {
    const store = useSessionStore.getState();
    store.setPreparationStatus('preparing');

    const apiKeys: Record<string, string> = {};
    const providers = ['gemini', 'groq', 'openai', 'anthropic', 'deepgram'];

    for (const provider of providers) {
      try {
        const key = await invoke<string>('get_api_key', { provider });
        if (key) {
          apiKeys[provider] = key;
        }
      } catch {
        // Ignore missing keys
      }
    }

    const prefs = {
      sttProvider: store.preferredSttProvider,
      llmProvider: store.preferredLlmProvider,
    };

    sendMessage({
      type: 'PREPARE_INTERVIEW',
      data: { apiKeys, preferences: prefs },
    });
  };

  // Custom message handler registration (for component-level handling)
  const addMessageHandler = (handler: MessageHandler) => {
    customMessageHandlers.add(handler);
  };

  const removeMessageHandler = (handler: MessageHandler) => {
    customMessageHandlers.delete(handler);
  };

  return {
    sendMessage,
    sendAudio,
    isConnected,
    // Session History (Phase 3: STORY-040)
    listSessions,
    loadSession,
    exportSession,
    deleteSession,
    // Preparation
    requestPreparation,
    // Custom message handlers (Phase 5: Document Type Inference)
    addMessageHandler,
    removeMessageHandler,
  };
};
