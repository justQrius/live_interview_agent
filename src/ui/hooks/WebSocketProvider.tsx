import React, { createContext, useEffect, useMemo, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import type { WebSocketMessage } from './websocketTypes';

const WS_URL = 'ws://localhost:8765';

type WebSocketContextValue = {
  sendMessage: (message: WebSocketMessage) => void;
  sendAudio: (audioData: string) => void;
  isConnected: boolean;
};

export const WebSocketContext = createContext<WebSocketContextValue | null>(null);

export const WebSocketProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const mountedRef = useRef(true);

  // Track stream ordering/dedup
  const lastSeqByStreamRef = useRef<Map<string, number>>(new Map());

  const [isConnected, setIsConnected] = useState(false);

  const addTranscription = useSessionStore((state) => state.addTranscription);
  const appendAnswerText = useSessionStore((state) => state.appendAnswerText);
  const completeAnswer = useSessionStore((state) => state.completeAnswer);
  const setStatus = useSessionStore((state) => state.setStatus);
  const setLastError = useSessionStore((state) => state.setLastError);
  const setCurrentAnswer = useSessionStore((state) => state.setCurrentAnswer);

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

          // New interviewer question -> start fresh answer buffer
          if (data.speaker === 'Interviewer') {
            setCurrentAnswer(null);
            lastSeqByStreamRef.current.clear();
          }

          addTranscription(data);
          break;
        }

        case 'ANSWER_CHUNK': {
          const data = message.data as {
            chunk: string;
            complete: boolean;
            confidence?: 'high' | 'medium' | 'low';
            streamId?: string;
            sequence?: number;
          };

          if (data.streamId && typeof data.sequence === 'number') {
            const lastSeen = lastSeqByStreamRef.current.get(data.streamId) ?? -1;
            if (data.sequence <= lastSeen) {
              return;
            }
            lastSeqByStreamRef.current.set(data.streamId, data.sequence);
          }

          if (data.chunk) {
            appendAnswerText(data.chunk);
          }

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
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = undefined;
      }

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

          if (mountedRef.current) {
            console.log('Attempting to reconnect in 5 seconds...');
            reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
          }
        };
      } catch (error) {
        console.error('Failed to create WebSocket connection:', error);
        if (mountedRef.current) {
          reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
        }
      }
    };

    connect();

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
    // Zustand store functions are stable references
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendMessage = (message: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
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

  const value = useMemo<WebSocketContextValue>(
    () => ({
      sendMessage,
      sendAudio,
      isConnected,
    }),
    [isConnected]
  );

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
};
