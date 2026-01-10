import { useEffect, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';

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
  | 'STATUS';

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

    case 'ERROR': {
      const data = message.data as { message: string };
      console.error('Python sidecar error:', data.message);
      store.setLastError(data.message);
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

  return {
    sendMessage,
    sendAudio,
    isConnected,
  };
};
