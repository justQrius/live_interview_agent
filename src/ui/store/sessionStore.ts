import { create } from 'zustand';

// Types matching the architecture
export interface Transcription {
  speaker: 'User' | 'Interviewer';
  text: string;
  timestamp: number;
  confidence: number;
}

export interface Answer {
  question: string;
  answerText: string;
  confidence: 'high' | 'medium' | 'low';
  timestamp: number;
  isComplete: boolean;
}

export interface ContextFile {
  id: string;
  name: string;
  type: 'resume' | 'job_description' | 'company_info' | 'qa';
  size: number;
  uploadDate: number;
  preview: string; // First 200 chars
}

export interface SessionState {
  // Session status
  status: 'idle' | 'calibrating' | 'listening' | 'processing';
  isScreenInvisible: boolean;
  voiceProfileActive: boolean;

  /**
   * API key for Gemini API.
   *
   * SECURITY WARNING: Stored in plaintext in memory temporarily.
   * This is ONLY for development testing until STORY-004 keychain integration.
   * DO NOT use in production builds without keychain support.
   * @see STORY-004 for secure keychain-based storage implementation
   */
  apiKey: string | null;

  // Current data
  currentTranscription: Transcription | null;
  currentAnswer: Answer | null;
  lastError: string | null;

  // History (session only, not persisted)
  transcriptionHistory: Transcription[];
  answerHistory: Answer[];
  loadedContextFiles: ContextFile[];

  // Actions
  setStatus: (status: SessionState['status']) => void;
  setScreenInvisibility: (enabled: boolean) => void;
  setVoiceProfileActive: (active: boolean) => void;
  setApiKey: (key: string | null) => void;
  setCurrentTranscription: (transcription: Transcription | null) => void;
  setCurrentAnswer: (answer: Answer | null) => void;
  setLastError: (error: string | null) => void;
  appendAnswerText: (text: string) => void;
  completeAnswer: (confidence: 'high' | 'medium' | 'low') => void;
  addContextFile: (file: ContextFile) => void;
  removeContextFile: (id: string) => void;
  addTranscription: (transcription: Transcription) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  // Initial state
  status: 'idle',
  isScreenInvisible: false,
  voiceProfileActive: false,
  apiKey: null,
  currentTranscription: null,
  currentAnswer: null,
  lastError: null,
  transcriptionHistory: [],
  answerHistory: [],
  loadedContextFiles: [],

  // Actions
  setStatus: (status) => set({ status }),

  setScreenInvisibility: (enabled) => set({ isScreenInvisible: enabled }),

  setVoiceProfileActive: (active) => set({ voiceProfileActive: active }),

  setApiKey: (key) => set({ apiKey: key }),

  setCurrentTranscription: (transcription) => set({ currentTranscription: transcription }),

  setCurrentAnswer: (answer) => set({ currentAnswer: answer }),

  setLastError: (error) => set({ lastError: error }),

  appendAnswerText: (text) =>
    set((state) => {
      if (!state.currentAnswer) {
        return {
          currentAnswer: {
            question: '',
            answerText: text,
            confidence: 'high',
            timestamp: Date.now(),
            isComplete: false,
          },
        };
      }
      return {
        currentAnswer: {
          ...state.currentAnswer,
          answerText: state.currentAnswer.answerText + text,
        },
      };
    }),

  completeAnswer: (confidence) =>
    set((state) => {
      if (!state.currentAnswer) return state;
      const completedAnswer = {
        ...state.currentAnswer,
        confidence,
        isComplete: true,
      };
      return {
        currentAnswer: completedAnswer,
        answerHistory: [...state.answerHistory, completedAnswer],
      };
    }),

  addContextFile: (file) =>
    set((state) => ({
      loadedContextFiles: [...state.loadedContextFiles, file],
    })),

  removeContextFile: (id) =>
    set((state) => ({
      loadedContextFiles: state.loadedContextFiles.filter((f) => f.id !== id),
    })),

  addTranscription: (transcription) =>
    set((state) => ({
      currentTranscription: transcription,
      transcriptionHistory: [...state.transcriptionHistory, transcription],
    })),

  clearSession: () =>
    set({
      status: 'idle',
      currentTranscription: null,
      currentAnswer: null,
      transcriptionHistory: [],
      answerHistory: [],
      lastError: null,
    }),
}));
