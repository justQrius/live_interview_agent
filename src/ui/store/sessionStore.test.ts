import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from './sessionStore';

describe('sessionStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: null,
      currentTranscription: null,
      currentAnswer: null,
      answerHistory: [],
      loadedContextFiles: [],
    });
  });

  describe('status', () => {
    it('should start with idle status', () => {
      const { status } = useSessionStore.getState();
      expect(status).toBe('idle');
    });

    it('should update status', () => {
      const { setStatus } = useSessionStore.getState();
      setStatus('listening');
      expect(useSessionStore.getState().status).toBe('listening');
    });

    it('should support all status values', () => {
      const { setStatus } = useSessionStore.getState();
      const statuses: Array<'idle' | 'calibrating' | 'listening' | 'processing'> = [
        'idle',
        'calibrating',
        'listening',
        'processing',
      ];

      for (const status of statuses) {
        setStatus(status);
        expect(useSessionStore.getState().status).toBe(status);
      }
    });
  });

  describe('apiKey', () => {
    it('should start with null apiKey', () => {
      const { apiKey } = useSessionStore.getState();
      expect(apiKey).toBeNull();
    });

    it('should set and retrieve API key', () => {
      const { setApiKey } = useSessionStore.getState();
      setApiKey('test-api-key-123');
      expect(useSessionStore.getState().apiKey).toBe('test-api-key-123');
    });

    it('should allow clearing API key', () => {
      const { setApiKey } = useSessionStore.getState();
      setApiKey('test-api-key-123');
      setApiKey(null);
      expect(useSessionStore.getState().apiKey).toBeNull();
    });
  });

  describe('transcription', () => {
    it('should start with null transcription', () => {
      const { currentTranscription } = useSessionStore.getState();
      expect(currentTranscription).toBeNull();
    });

    it('should set transcription', () => {
      const { setCurrentTranscription } = useSessionStore.getState();
      const transcription = {
        speaker: 'Interviewer' as const,
        text: 'Tell me about yourself',
        timestamp: Date.now(),
        confidence: 0.95,
      };
      setCurrentTranscription(transcription);
      expect(useSessionStore.getState().currentTranscription).toEqual(transcription);
    });
  });

  describe('answer', () => {
    it('should start with null answer', () => {
      const { currentAnswer } = useSessionStore.getState();
      expect(currentAnswer).toBeNull();
    });

    it('should append answer text', () => {
      const { appendAnswerText } = useSessionStore.getState();
      appendAnswerText('Hello');
      appendAnswerText(' World');
      expect(useSessionStore.getState().currentAnswer?.answerText).toBe('Hello World');
    });

    it('should complete answer and add to history', () => {
      const { appendAnswerText, completeAnswer } = useSessionStore.getState();
      appendAnswerText('Test answer');
      completeAnswer('high');

      const state = useSessionStore.getState();
      expect(state.currentAnswer?.isComplete).toBe(true);
      expect(state.currentAnswer?.confidence).toBe('high');
      expect(state.answerHistory).toHaveLength(1);
      expect(state.answerHistory[0].answerText).toBe('Test answer');
    });
  });

  describe('context files', () => {
    it('should add context file', () => {
      const { addContextFile } = useSessionStore.getState();
      const file = {
        id: '123',
        name: 'resume.pdf',
        type: 'resume' as const,
        size: 1024,
        uploadDate: Date.now(),
        preview: 'Lorem ipsum...',
      };
      addContextFile(file);
      expect(useSessionStore.getState().loadedContextFiles).toHaveLength(1);
      expect(useSessionStore.getState().loadedContextFiles[0].name).toBe('resume.pdf');
    });

    it('should remove context file', () => {
      const { addContextFile, removeContextFile } = useSessionStore.getState();
      const file = {
        id: '123',
        name: 'resume.pdf',
        type: 'resume' as const,
        size: 1024,
        uploadDate: Date.now(),
        preview: 'Lorem ipsum...',
      };
      addContextFile(file);
      removeContextFile('123');
      expect(useSessionStore.getState().loadedContextFiles).toHaveLength(0);
    });
  });

  describe('clearSession', () => {
    it('should clear session data but keep context files', () => {
      const { setStatus, appendAnswerText, completeAnswer, addContextFile, clearSession } =
        useSessionStore.getState();

      // Setup some state
      setStatus('listening');
      appendAnswerText('Test answer');
      completeAnswer('high');
      addContextFile({
        id: '123',
        name: 'resume.pdf',
        type: 'resume',
        size: 1024,
        uploadDate: Date.now(),
        preview: 'Lorem ipsum...',
      });

      // Clear session
      clearSession();

      const state = useSessionStore.getState();
      expect(state.status).toBe('idle');
      expect(state.currentTranscription).toBeNull();
      expect(state.currentAnswer).toBeNull();
      expect(state.answerHistory).toHaveLength(0);
      // Context files should be preserved
      expect(state.loadedContextFiles).toHaveLength(1);
    });
  });
});
