import { useEffect, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';

// WebSocket message types (as per architecture)
export type MessageType =
  | 'START_SESSION'
  | 'STOP_SESSION'
  | 'UPLOAD_CONTEXT'
  | 'CALIBRATE_VOICE'
  | 'MANUAL_QUESTION'
  | 'TRANSCRIPTION'
  | 'ANSWER_CHUNK'
  | 'ERROR'
  | 'STATUS';

export interface WebSocketMessage {
  type: MessageType;
  data?: unknown;
}

const WS_URL = 'ws://localhost:8765';

export const useWebSocket = () => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const mountedRef = useRef(true);
  const [isConnected, setIsConnected] = useState(false);
  const addTranscription = useSessionStore((state) => state.addTranscription);
  const appendAnswerText = useSessionStore((state) => state.appendAnswerText);
  const completeAnswer = useSessionStore((state) => state.completeAnswer);
  const setStatus = useSessionStore((state) => state.setStatus);
  const setLastError = useSessionStore((state) => state.setLastError);

  useEffect(() => {
    mountedRef.current = true;

    const handleMessage = (message: WebSocketMessage) => {
      switch (message.type) {
        case 'TRANSCRIPTION': {
          const data = message.data as {
            speaker: 'User' | 'Interviewer';
            text: string;
            timestamp: number;
            confidence: number;
          };
          addTranscription(data);
          break;
        }

        case 'ANSWER_CHUNK': {
          const data = message.data as {
            chunk: string;
            complete: boolean;
            confidence?: 'high' | 'medium' | 'low';
          };
          appendAnswerText(data.chunk);
          if (data.complete && data.confidence) {
            completeAnswer(data.confidence);
          }
          break;
        }

        case 'STATUS': {
          const data = message.data as {
            state: 'listening' | 'processing' | 'idle' | 'calibrating';
          };
          setStatus(data.state);
          break;
        }

        case 'ERROR': {
          const data = message.data as { message: string };
          console.error('Python sidecar error:', data.message);
          setLastError(data.message);
          break;
        }

        default:
          console.warn('Unknown message type:', message.type);
      }
    };

    const connect = () => {
      // Clear any existing reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }

      // Don't connect if unmounted
      if (!mountedRef.current) {
        return;
      }

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected to Python sidecar');
          setIsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected.');
          setIsConnected(false);
          wsRef.current = null;

          // Only reconnect if still mounted
          if (mountedRef.current) {
            console.log('Attempting to reconnect in 5 seconds...');
            reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        // Only retry if still mounted
        if (mountedRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
        }
      }
    };

    // Initial connection
    connect();

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
    // Zustand store functions are stable references, no need to include in deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
    }
  };

  return {
    sendMessage,
    isConnected,
  };
};
