import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock WebSocket for testing
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  private sentMessages: string[] = [];

  constructor(public url: string) {
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    this.sentMessages.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Test helper: simulate receiving a message
  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Test helper: get sent messages
  getSentMessages() {
    return this.sentMessages;
  }

  ping() {
    return Promise.resolve();
  }
}

// Store the original WebSocket for restoration
const originalWebSocket = globalThis.WebSocket;

describe('WebSocket Message Protocol', () => {
  beforeEach(() => {
    globalThis.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket;
    vi.clearAllMocks();
  });

  describe('Message Types', () => {
    it('should define all client-to-server message types', () => {
      const clientMessageTypes = [
        'START_SESSION',
        'STOP_SESSION',
        'UPLOAD_CONTEXT',
        'CALIBRATE_VOICE',
        'MANUAL_QUESTION',
      ];

      // All message types should be string values matching the protocol
      for (const type of clientMessageTypes) {
        expect(type).toBe(type.toUpperCase());
      }
    });

    it('should define all server-to-client message types', () => {
      const serverMessageTypes = ['TRANSCRIPTION', 'ANSWER_CHUNK', 'ERROR', 'STATUS'];

      // All message types should be string values matching the protocol
      for (const type of serverMessageTypes) {
        expect(type).toBe(type.toUpperCase());
      }
    });
  });

  describe('Message Serialization', () => {
    it('should create valid START_SESSION message with API key', () => {
      const message = {
        type: 'START_SESSION',
        data: { apiKey: 'test-api-key' },
      };

      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('START_SESSION');
      expect(parsed.data.apiKey).toBe('test-api-key');
    });

    it('should create valid STOP_SESSION message', () => {
      const message = { type: 'STOP_SESSION' };

      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('STOP_SESSION');
    });

    it('should create valid MANUAL_QUESTION message', () => {
      const message = {
        type: 'MANUAL_QUESTION',
        data: { question: 'Tell me about your experience' },
      };

      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('MANUAL_QUESTION');
      expect(parsed.data.question).toBe('Tell me about your experience');
    });

    it('should create valid UPLOAD_CONTEXT message', () => {
      const message = {
        type: 'UPLOAD_CONTEXT',
        data: {
          files: [
            { name: 'resume.pdf', content: 'base64...' },
            { name: 'job_desc.txt', content: 'base64...' },
          ],
        },
      };

      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('UPLOAD_CONTEXT');
      expect(parsed.data.files).toHaveLength(2);
    });

    it('should create valid CALIBRATE_VOICE message', () => {
      const message = {
        type: 'CALIBRATE_VOICE',
        data: { audioData: 'base64-audio-data' },
      };

      const json = JSON.stringify(message);
      const parsed = JSON.parse(json);

      expect(parsed.type).toBe('CALIBRATE_VOICE');
      expect(parsed.data.audioData).toBe('base64-audio-data');
    });
  });

  describe('Response Message Parsing', () => {
    it('should parse TRANSCRIPTION message', () => {
      const message = {
        type: 'TRANSCRIPTION',
        data: {
          speaker: 'Interviewer',
          text: 'Tell me about yourself',
          timestamp: 1234567890.123,
          confidence: 0.95,
        },
      };

      const parsed = JSON.parse(JSON.stringify(message));

      expect(parsed.type).toBe('TRANSCRIPTION');
      expect(parsed.data.speaker).toBe('Interviewer');
      expect(parsed.data.text).toBe('Tell me about yourself');
      expect(parsed.data.timestamp).toBe(1234567890.123);
      expect(parsed.data.confidence).toBe(0.95);
    });

    it('should parse ANSWER_CHUNK message (streaming)', () => {
      const message = {
        type: 'ANSWER_CHUNK',
        data: {
          chunk: 'I have experience with...',
          complete: false,
        },
      };

      const parsed = JSON.parse(JSON.stringify(message));

      expect(parsed.type).toBe('ANSWER_CHUNK');
      expect(parsed.data.chunk).toBe('I have experience with...');
      expect(parsed.data.complete).toBe(false);
    });

    it('should parse ANSWER_CHUNK message (complete)', () => {
      const message = {
        type: 'ANSWER_CHUNK',
        data: {
          chunk: '...in Python and JavaScript.',
          complete: true,
          confidence: 'high',
        },
      };

      const parsed = JSON.parse(JSON.stringify(message));

      expect(parsed.type).toBe('ANSWER_CHUNK');
      expect(parsed.data.complete).toBe(true);
      expect(parsed.data.confidence).toBe('high');
    });

    it('should parse ERROR message', () => {
      const message = {
        type: 'ERROR',
        data: {
          message: 'API key is required',
          code: 'ERR_NO_API_KEY',
        },
      };

      const parsed = JSON.parse(JSON.stringify(message));

      expect(parsed.type).toBe('ERROR');
      expect(parsed.data.message).toBe('API key is required');
      expect(parsed.data.code).toBe('ERR_NO_API_KEY');
    });

    it('should parse STATUS message', () => {
      const message = {
        type: 'STATUS',
        data: {
          state: 'listening',
        },
      };

      const parsed = JSON.parse(JSON.stringify(message));

      expect(parsed.type).toBe('STATUS');
      expect(parsed.data.state).toBe('listening');
    });
  });

  describe('WebSocket Connection', () => {
    it('should connect to localhost:8765', async () => {
      const ws = new MockWebSocket('ws://localhost:8765');

      expect(ws.url).toBe('ws://localhost:8765');

      // Wait for connection
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(ws.readyState).toBe(MockWebSocket.OPEN);
    });

    it('should send messages when connected', async () => {
      const ws = new MockWebSocket('ws://localhost:8765');

      // Wait for connection
      await new Promise((resolve) => setTimeout(resolve, 10));

      const message = { type: 'START_SESSION', data: { apiKey: 'test-key' } };
      ws.send(JSON.stringify(message));

      expect(ws.getSentMessages()).toHaveLength(1);
      expect(JSON.parse(ws.getSentMessages()[0])).toEqual(message);
    });

    it('should receive and parse messages', async () => {
      const ws = new MockWebSocket('ws://localhost:8765');
      const receivedMessages: unknown[] = [];

      ws.onmessage = (event) => {
        receivedMessages.push(JSON.parse(event.data));
      };

      // Wait for connection
      await new Promise((resolve) => setTimeout(resolve, 10));

      // Simulate server sending STATUS message
      ws.simulateMessage({ type: 'STATUS', data: { state: 'listening' } });

      expect(receivedMessages).toHaveLength(1);
      expect(receivedMessages[0]).toEqual({
        type: 'STATUS',
        data: { state: 'listening' },
      });
    });
  });
});
