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

export interface ExtractionResult {
  hasSummary: boolean;
  hasFacts: boolean;
  storyCount: number;
  hasProfile: boolean;
  success: boolean;
  errors?: string[];
}

export interface ContextFile {
  id: string;
  name: string;
  type: 'resume' | 'job_description' | 'company_info' | 'industry_research' | 'sample_qa' | 'interviewer_info' | 'custom';
  size: number;
  uploadDate: number;
  preview: string; // First 200 chars
  
  // Processing status (Phase 4)
  status?: 'pending' | 'processing' | 'ready' | 'error';
  progress?: number;
  processingMessage?: string;
  extractionResult?: ExtractionResult;
}

export type Provider = 'gemini' | 'groq' | 'deepgram' | 'openai' | 'anthropic';

// Session History Types (Phase 3: STORY-040)
export interface SessionSummary {
  id: string;
  startedAt: number; // Unix ms
  endedAt: number | null;
  contextFiles: string[];
  transcriptionCount: number;
  answerCount: number;
}

export interface SessionData {
  id: string;
  startedAt: number;
  endedAt: number | null;
  contextFiles: string[];
  transcriptions: Transcription[];
  answers: Array<{
    question: string;
    answer: string;
    confidence: string;
    timestamp?: number;
    latency_ms?: number;
  }>;
}

// Coaching Types (Phase 4E: STORY-070)
export interface StorySuggestion {
  storyId: string;
  title: string;
  situation: string;
  relevanceScore: number;
  suggestedOpening: string;
  keyMetrics: string[];
  tags: string[];
}

export interface StructureSection {
  name: string;
  percentage: string;
  description: string;
}

export interface StructureHint {
  name: string;
  sections: StructureSection[];
  tips: string[];
}

export interface Contradiction {
  claim_type: string;
  existing: string;
  new: string;
  message: string;
}

// Enhancement Types (Phase 5)
export type EnhancementType = 'add_detail' | 'make_specific' | 'suggest_star' | 'adjust_tone' | 'shorten';

export interface EnhancementState {
  isEnhancing: boolean;
  enhancementType: EnhancementType | null;
  enhancedText: string;
  originalQuestion: string | null;
  originalAnswer: string | null;
}

export interface SessionState {
  // Session status
  status: 'idle' | 'calibrating' | 'listening' | 'processing';
  isScreenInvisible: boolean;
  voiceProfileActive: boolean;

  // Context loading status (for status indicator)
  contextStatus: 'empty' | 'analyzing' | 'uploading' | 'cache_ready' | 'rag_ready' | 'error';

  /**
   * API key for Gemini API.
   *
   * SECURITY WARNING: Stored in plaintext in memory temporarily.
   * This is ONLY for development testing until STORY-004 keychain integration.
   * DO NOT use in production builds without keychain support.
   * @see STORY-004 for secure keychain-based storage implementation
   */
  apiKey: string | null;

  // Preferences
  preferredSttProvider: Provider | 'auto';
  preferredLlmProvider: Provider | 'auto';

  // Current data
  currentTranscription: Transcription | null;
  currentAnswer: Answer | null;
  lastError: string | null;

  // History (session only, not persisted)
  transcriptionHistory: Transcription[];
  answerHistory: Answer[];
  loadedContextFiles: ContextFile[];

  // Session History (Phase 3: STORY-040) - persisted sessions from sidecar
  savedSessions: SessionSummary[];
  selectedSession: SessionData | null;
  isHistoryOpen: boolean;
  isHistoryLoading: boolean;

  // Preparation State (STORY-047/048)
  preparationStatus: 'not_started' | 'preparing' | 'ready' | 'error';
  preparationSummary: string | null;
  isPreparationExpanded: boolean;

  // Coaching State (Phase 4E: STORY-070)
  storySuggestion: StorySuggestion | null;
  structureHint: StructureHint | null;
  consistencyWarnings: Contradiction[];
  interimTranscript: string | null;

  // Enhancement State (Phase 5)
  enhancement: EnhancementState;

  // Actions
  setStatus: (status: SessionState['status']) => void;
  setScreenInvisibility: (enabled: boolean) => void;
  setVoiceProfileActive: (active: boolean) => void;
  setApiKey: (key: string | null) => void;
  setPreferredSttProvider: (provider: Provider | 'auto') => void;
  setPreferredLlmProvider: (provider: Provider | 'auto') => void;
  setContextStatus: (status: 'empty' | 'analyzing' | 'uploading' | 'cache_ready' | 'rag_ready' | 'error') => void;
  setCurrentTranscription: (transcription: Transcription | null) => void;
  setCurrentAnswer: (answer: Answer | null) => void;
  setLastError: (error: string | null) => void;
  startAnswer: (question: string, timestamp?: number) => void;
  appendAnswerText: (text: string) => void;
  completeAnswer: (confidence: 'high' | 'medium' | 'low') => void;
  addContextFile: (file: ContextFile) => void;
  updateContextFile: (id: string, updates: Partial<ContextFile>) => void;
  removeContextFile: (id: string) => void;
  addTranscription: (transcription: Transcription) => void;
  clearSession: () => void;

  // Session History Actions (Phase 3: STORY-040)
  setHistoryOpen: (open: boolean) => void;
  setSavedSessions: (sessions: SessionSummary[]) => void;
  setSelectedSession: (session: SessionData | null) => void;
  setHistoryLoading: (loading: boolean) => void;
  removeSession: (sessionId: string) => void;

  // Preparation Actions (STORY-047/048)
  setPreparationStatus: (status: 'not_started' | 'preparing' | 'ready' | 'error') => void;
  setPreparationSummary: (summary: string | null) => void;
  setPreparationExpanded: (expanded: boolean) => void;

  // Coaching Actions (Phase 4E: STORY-070)
  setStorySuggestion: (suggestion: StorySuggestion | null) => void;
  setStructureHint: (hint: StructureHint | null) => void;
  setConsistencyWarnings: (warnings: Contradiction[]) => void;
  setInterimTranscript: (text: string | null) => void;
  addConsistencyWarning: (warning: Contradiction) => void;
  clearCoachingData: () => void;

  // Enhancement Actions (Phase 5)
  startEnhancement: (type: EnhancementType, question: string, answer: string) => void;
  appendEnhancedText: (text: string) => void;
  completeEnhancement: () => void;
  cancelEnhancement: () => void;
  applyEnhancement: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  // Initial state
  status: 'idle',
  isScreenInvisible: false,
  voiceProfileActive: false,
  apiKey: null,
  contextStatus: 'empty',

  // Preferences
  preferredSttProvider: (localStorage.getItem('preferredSttProvider') as Provider | 'auto') || 'auto',
  preferredLlmProvider: (localStorage.getItem('preferredLlmProvider') as Provider | 'auto') || 'auto',

  currentTranscription: null,
  currentAnswer: null,
  lastError: null,
  transcriptionHistory: [],
  answerHistory: [],
  loadedContextFiles: [],

  // Session History initial state (Phase 3: STORY-040)
  savedSessions: [],
  selectedSession: null,
  isHistoryOpen: false,
  isHistoryLoading: false,

  // Preparation initial state
  preparationStatus: 'not_started',
  preparationSummary: null,
  isPreparationExpanded: false,

  // Coaching initial state
  storySuggestion: null,
  structureHint: null,
  consistencyWarnings: [],
  interimTranscript: null,

  // Enhancement initial state (Phase 5)
  enhancement: {
    isEnhancing: false,
    enhancementType: null,
    enhancedText: '',
    originalQuestion: null,
    originalAnswer: null,
  },

  // Actions
  setStatus: (status) => set({ status }),

  setScreenInvisibility: (enabled) => set({ isScreenInvisible: enabled }),

  setVoiceProfileActive: (active) => set({ voiceProfileActive: active }),

  setApiKey: (key) => set({ apiKey: key }),

  setPreferredSttProvider: (provider) => {
    localStorage.setItem('preferredSttProvider', provider);
    set({ preferredSttProvider: provider });
  },

  setPreferredLlmProvider: (provider) => {
    localStorage.setItem('preferredLlmProvider', provider);
    set({ preferredLlmProvider: provider });
  },

  setContextStatus: (status: SessionState['contextStatus']) => set({ contextStatus: status }),

  setCurrentTranscription: (transcription) => set({ currentTranscription: transcription }),


  setCurrentAnswer: (answer) => set({ currentAnswer: answer }),

  setLastError: (error) => set({ lastError: error }),

  startAnswer: (question, timestamp) =>
    set({
      currentAnswer: {
        question,
        answerText: '',
        confidence: 'medium',
        timestamp: timestamp ?? Date.now(),
        isComplete: false,
      },
    }),

  appendAnswerText: (text) =>
    set((state) => {
      const trimOverlap = (existingText: string, incomingText: string) => {
        if (!existingText || !incomingText) return incomingText;

        // If provider streams cumulative content from the start, keep only the delta.
        if (incomingText.startsWith(existingText)) {
          return incomingText.slice(existingText.length);
        }

        // If provider re-sends a prefix of what we already have, ignore it.
        if (existingText.startsWith(incomingText)) {
          return '';
        }

        const maxOverlap = Math.min(existingText.length, incomingText.length);
        for (let overlap = maxOverlap; overlap > 0; overlap -= 1) {
          if (existingText.endsWith(incomingText.slice(0, overlap))) {
            return incomingText.slice(overlap);
          }
        }

        return incomingText;
      };


      if (!state.currentAnswer) {
        return {
          currentAnswer: {
            question: '',
            answerText: text,
            confidence: 'medium',
            timestamp: Date.now(),
            isComplete: false,
          },
        };
      }

      const deduped = trimOverlap(state.currentAnswer.answerText, text);

      const candidate = deduped.trim();
      if (candidate.length >= 40 && state.currentAnswer.answerText.includes(candidate)) {
        return state;
      }

      return {
        currentAnswer: {
          ...state.currentAnswer,
          answerText: state.currentAnswer.answerText + deduped,
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

  updateContextFile: (id, updates) =>
    set((state) => ({
      loadedContextFiles: state.loadedContextFiles.map((f) =>
        f.id === id ? { ...f, ...updates } : f
      ),
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

  // Session History Actions (Phase 3: STORY-040)
  setHistoryOpen: (open) => set({ isHistoryOpen: open }),

  setSavedSessions: (sessions) => set({ savedSessions: sessions }),

  setSelectedSession: (session) => set({ selectedSession: session }),

  setHistoryLoading: (loading) => set({ isHistoryLoading: loading }),

  removeSession: (sessionId) =>
    set((state) => ({
      savedSessions: state.savedSessions.filter((s) => s.id !== sessionId),
      selectedSession: state.selectedSession?.id === sessionId ? null : state.selectedSession,
    })),

  setPreparationStatus: (status) => set({ preparationStatus: status }),
  setPreparationSummary: (summary) => set({ preparationSummary: summary }),
  setPreparationExpanded: (expanded) => set({ isPreparationExpanded: expanded }),

  // Coaching Actions (Phase 4E: STORY-070)
  setStorySuggestion: (suggestion) => set({ storySuggestion: suggestion }),
  setStructureHint: (hint) => set({ structureHint: hint }),
  setConsistencyWarnings: (warnings) => set({ consistencyWarnings: warnings }),
  setInterimTranscript: (text) => set({ interimTranscript: text }),
  
  addConsistencyWarning: (warning) =>
    set((state) => ({
      consistencyWarnings: [...state.consistencyWarnings, warning]
    })),
    
  clearCoachingData: () =>
    set({
      storySuggestion: null,
      structureHint: null,
      consistencyWarnings: [],
      interimTranscript: null
    }),

  // Enhancement Actions (Phase 5)
  startEnhancement: (type, question, answer) =>
    set({
      enhancement: {
        isEnhancing: true,
        enhancementType: type,
        enhancedText: '',
        originalQuestion: question,
        originalAnswer: answer,
      },
    }),

  appendEnhancedText: (text) =>
    set((state) => ({
      enhancement: {
        ...state.enhancement,
        enhancedText: state.enhancement.enhancedText + text,
      },
    })),

  completeEnhancement: () =>
    set((state) => ({
      enhancement: {
        ...state.enhancement,
        isEnhancing: false,
      },
    })),

  cancelEnhancement: () =>
    set({
      enhancement: {
        isEnhancing: false,
        enhancementType: null,
        enhancedText: '',
        originalQuestion: null,
        originalAnswer: null,
      },
    }),

  applyEnhancement: () =>
    set((state) => {
      // Replace current answer with enhanced version
      if (!state.currentAnswer || !state.enhancement.enhancedText) {
        return {
          enhancement: {
            isEnhancing: false,
            enhancementType: null,
            enhancedText: '',
            originalQuestion: null,
            originalAnswer: null,
          },
        };
      }

      return {
        currentAnswer: {
          ...state.currentAnswer,
          answerText: state.enhancement.enhancedText,
        },
        enhancement: {
          isEnhancing: false,
          enhancementType: null,
          enhancedText: '',
          originalQuestion: null,
          originalAnswer: null,
        },
      };
    }),
}));
