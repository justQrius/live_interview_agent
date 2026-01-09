import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from './sessionStore';

describe('sessionStore', () => {
  beforeEach(() => {
    // Reset store to a predictable baseline before each test.
    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: null,
      preferredSttProvider: 'auto',
      preferredLlmProvider: 'auto',
      currentTranscription: null,
      currentAnswer: null,
      lastError: null,
      transcriptionHistory: [],
      answerHistory: [],
      loadedContextFiles: [],
    });
  });

  describe('status', () => {
    it('should start with idle status', () => {
      expect(useSessionStore.getState().status).toBe('idle');
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
      expect(useSessionStore.getState().apiKey).toBeNull();
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
      expect(useSessionStore.getState().currentTranscription).toBeNull();
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

    it('should add transcription to history', () => {
      const { addTranscription } = useSessionStore.getState();

      addTranscription({ speaker: 'Interviewer', text: 'Q1', timestamp: 1, confidence: 0.9 });
      addTranscription({ speaker: 'User', text: 'A1', timestamp: 2, confidence: 0.8 });

      const state = useSessionStore.getState();
      expect(state.transcriptionHistory).toHaveLength(2);
      expect(state.currentTranscription?.text).toBe('A1');
    });
  });

  describe('answer', () => {
    it('should start with null answer', () => {
      expect(useSessionStore.getState().currentAnswer).toBeNull();
    });

    it('should append answer text (delta chunks)', () => {
      const { startAnswer, appendAnswerText } = useSessionStore.getState();

      startAnswer('Q', 1);
      appendAnswerText('Hello');
      appendAnswerText(' World');

      expect(useSessionStore.getState().currentAnswer?.answerText).toBe('Hello World');
    });

    it('should avoid duplicated overlap when appending cumulative chunks', () => {
      const { startAnswer, appendAnswerText } = useSessionStore.getState();

      startAnswer('Q', 1);
      appendAnswerText('I build systems that bridge business and engineering.');
      appendAnswerText('I build systems that bridge business and engineering. Currently, I focus on agentic AI.');

      expect(useSessionStore.getState().currentAnswer?.answerText).toBe(
        'I build systems that bridge business and engineering. Currently, I focus on agentic AI.'
      );
    });

    it('should avoid duplicated overlap when appending suffix-overlapping chunks', () => {
      const { startAnswer, appendAnswerText } = useSessionStore.getState();

      startAnswer('Q', 1);
      appendAnswerText('I build systems that bridge business and engineering.');
      appendAnswerText('engineering. Currently, I focus on agentic AI.');

      expect(useSessionStore.getState().currentAnswer?.answerText).toBe(
        'I build systems that bridge business and engineering. Currently, I focus on agentic AI.'
      );
    });

    it('should start a fresh answer when a new question begins', () => {
      const { startAnswer, appendAnswerText } = useSessionStore.getState();

      startAnswer('Q1', 111);
      appendAnswerText('A1');

      startAnswer('Q2', 222);
      appendAnswerText('A2');

      const state = useSessionStore.getState();
      expect(state.currentAnswer?.question).toBe('Q2');
      expect(state.currentAnswer?.timestamp).toBe(222);
      expect(state.currentAnswer?.answerText).toBe('A2');
      expect(state.currentAnswer?.isComplete).toBe(false);
    });

    it('should complete answer and add to history', () => {
      const { startAnswer, appendAnswerText, completeAnswer } = useSessionStore.getState();

      startAnswer('Q', 1);
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

      addContextFile({
        id: '123',
        name: 'resume.pdf',
        type: 'resume',
        size: 1024,
        uploadDate: Date.now(),
        preview: 'Lorem ipsum...',
      });

      expect(useSessionStore.getState().loadedContextFiles).toHaveLength(1);
      expect(useSessionStore.getState().loadedContextFiles[0].name).toBe('resume.pdf');
    });

    it('should remove context file', () => {
      const { addContextFile, removeContextFile } = useSessionStore.getState();

      addContextFile({
        id: '123',
        name: 'resume.pdf',
        type: 'resume',
        size: 1024,
        uploadDate: Date.now(),
        preview: 'Lorem ipsum...',
      });

      removeContextFile('123');
      expect(useSessionStore.getState().loadedContextFiles).toHaveLength(0);
    });
  });

  describe('clearSession', () => {
    it('should clear session data but keep context files', () => {
      const { setStatus, startAnswer, appendAnswerText, completeAnswer, addContextFile, clearSession } =
        useSessionStore.getState();

      setStatus('listening');
      startAnswer('Q', 1);
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

      clearSession();

      const state = useSessionStore.getState();
      expect(state.status).toBe('idle');
      expect(state.currentTranscription).toBeNull();
      expect(state.currentAnswer).toBeNull();
      expect(state.answerHistory).toHaveLength(0);
      expect(state.transcriptionHistory).toHaveLength(0);
      expect(state.lastError).toBeNull();

      // Context files should be preserved
      expect(state.loadedContextFiles).toHaveLength(1);
    });
  });
});
