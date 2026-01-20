# Live Interview Agent - System Architecture

> **Version**: 2.0 (Phase 9)  
> **Last Updated**: January 2026

A comprehensive technical reference for the Live Interview Agent, a real-time AI-powered interview coaching system.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Component Overview](#2-component-overview)
3. [Data Flow](#3-data-flow)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Python Sidecar Architecture](#5-python-sidecar-architecture)
6. [Provider System](#6-provider-system)
7. [Intelligence Pipeline](#7-intelligence-pipeline)
8. [RAG & Context Management](#8-rag--context-management)
9. [Coaching & Memory Systems](#9-coaching--memory-systems)
10. [IPC Protocol Reference](#10-ipc-protocol-reference)
11. [Latency Architecture](#11-latency-architecture)
12. [Security & Privacy](#12-security--privacy)

---

## 1. High-Level Architecture

The application follows a **Sidecar Architecture** pattern with three distinct layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DESKTOP LAYER                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Tauri Shell (Rust)                           │   │
│  │  • Window Management  • OS Integration  • Keyring (Secure Storage)  │   │
│  │  • Sidecar Lifecycle  • System Tray     • Auto-updater              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ IPC (Tauri Commands)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      React UI (TypeScript)                           │   │
│  │  • Zustand State Store    • WebSocket Client    • Tailwind CSS      │   │
│  │  • Coaching Panels        • Settings Modal      • History View       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ WebSocket (localhost:8765)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTELLIGENCE LAYER                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Python Sidecar (asyncio)                        │   │
│  │                                                                       │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐   │   │
│  │  │   Audio   │ │ Providers │ │    RAG    │ │   Intelligence    │   │   │
│  │  │  Capture  │ │ STT / LLM │ │  Engine   │ │     Pipeline      │   │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘   │   │
│  │                                                                       │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐   │   │
│  │  │  Memory   │ │ Coaching  │ │Extraction │ │    Evaluation     │   │   │
│  │  │   Store   │ │  Engine   │ │ Pipeline  │ │    (Grounding)    │   │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ API Calls
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │  Gemini  │  │  OpenAI  │  │Anthropic │  │ Deepgram │  │  Local   │     │
│  │ STT/LLM  │  │   LLM    │  │   LLM    │  │Streaming │  │ Whisper  │     │
│  │  Cache   │  │  Search  │  │          │  │   STT    │  │  (GPU)   │     │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Overview

### 2.1 Tauri Shell (`src-tauri/`)

| Component | File | Responsibility |
|-----------|------|----------------|
| **Sidecar Manager** | `commands/sidecar.rs` | Spawn/terminate Python process |
| **Keyring** | `utils/keyring.rs` | Secure API key storage (OS keychain) |
| **Config** | `commands/config.rs` | Get/set secure configuration |
| **Window** | `main.rs` | Window creation, system tray |

### 2.2 React Frontend (`src/ui/`)

| Component | File | Responsibility |
|-----------|------|----------------|
| **App** | `App.tsx` | Main layout orchestrator |
| **Session Store** | `store/sessionStore.ts` | Global Zustand state |
| **WebSocket Hook** | `hooks/useWebSocket.ts` | IPC communication hub |
| **Answer Display** | `components/AnswerDisplay.tsx` | Question/answer rendering |
| **Coaching Panel** | `components/CoachingPanel.tsx` | Story/structure suggestions |
| **Settings Modal** | `components/SettingsModal.tsx` | Provider configuration |

### 2.3 Python Sidecar (`sidecar/src/`)

| Module | Directory | Responsibility |
|--------|-----------|----------------|
| **Server** | `server.py` | WebSocket server, message routing |
| **Audio** | `audio/` | Capture, VAD, diarization, noise reduction |
| **Providers** | `providers/` | STT, LLM, Search provider implementations |
| **Classification** | `classification/` | Question detection, reformulation, splitting |
| **RAG** | `rag/` | Vector store, enhanced retrieval |
| **Context** | `context/` | Document processing, Gemini caching |
| **Memory** | `memory/` | SQLite persistence, candidate profile |
| **Coaching** | `coaching/` | Story recall, structure suggestion, consistency |
| **Extraction** | `extraction/` | Document fact/story extraction |
| **Evaluation** | `evaluation/` | Groundedness scoring, analytics |

---

## 3. Data Flow

### 3.1 End-to-End Question-Answer Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           AUDIO CAPTURE PHASE                                 │
│                                                                               │
│  System Audio ──► WASAPI/CoreAudio ──► 16kHz PCM ──► Circular Buffer         │
│                         (500ms chunks)                                        │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SPEECH PROCESSING PHASE                             │
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  Silero VAD │───►│   Speaker   │───►│  Streaming  │───►│  Utterance  │   │
│  │  (32ms win) │    │   Diarize   │    │     STT     │    │ Accumulator │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                                                  │            │
│                                              ┌───────────────────┘            │
│                                              ▼                                │
│                                    ┌─────────────────┐                       │
│                                    │  4-Tier Check:  │                       │
│                                    │ Punct→Syntax→   │                       │
│                                    │ Timing→LLM      │                       │
│                                    └─────────────────┘                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ Complete Utterance
┌──────────────────────────────────────────────────────────────────────────────┐
│                          INTELLIGENCE PHASE                                   │
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │  Question   │───►│    Query    │───►│  Question   │                      │
│  │  Detector   │    │ Reformulator│    │  Splitter   │                      │
│  │ (3-tier)    │    │ (TopicStack)│    │             │                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                      │
│         │                                     │                              │
│         ▼                                     ▼                              │
│  ┌─────────────┐                      ┌─────────────┐                       │
│  │   Coaching  │ (parallel)           │ Enhanced    │                       │
│  │   Engine    │◄─────────────────────│ RAG Engine  │                       │
│  └─────────────┘                      └─────────────┘                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼ Retrieved Context + Profile
┌──────────────────────────────────────────────────────────────────────────────┐
│                           GENERATION PHASE                                    │
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Prompt    │───►│     LLM     │───►│  Streaming  │───►│ Groundedness│   │
│  │  Assembly   │    │  Provider   │    │   Output    │    │  Evaluator  │   │
│  │ (Framework) │    │             │    │             │    │ (background)│   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│                                              │                               │
│                                              ▼                               │
│                                    ┌─────────────────┐                      │
│                                    │    WebSocket    │                      │
│                                    │  ANSWER_CHUNK   │                      │
│                                    └─────────────────┘                      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Latency Breakdown (Target: <1.5s end-to-end)

| Stage | Target | Optimization |
|-------|--------|--------------|
| VAD Detection | <50ms | Silero V4, 32ms windows |
| Streaming STT | ~150ms | Deepgram Nova-3 WebSocket |
| Accumulation | <200ms | Hybrid semantic endpointing |
| Question Detection | <10ms | Regex-first, LLM fallback |
| RAG Retrieval | <200ms | Child-to-parent expansion |
| LLM First Token | <500ms | Gemini context caching |
| **Total** | **<1.5s** | |

---

## 4. Frontend Architecture

### 4.1 Component Hierarchy

```
App.tsx
├── Header
│   ├── StatusPill (connection state)
│   ├── ThemeToggle
│   └── SettingsButton / HistoryButton
├── Sidebar (Sliding Overlay)
│   ├── SessionControls (Start/Stop/Pause)
│   ├── ContextLoader (Document upload)
│   └── PreparationButton
├── Main Content
│   ├── PreparationSummary (collapsible)
│   ├── AccumulatingIndicator (buffering state)
│   ├── CoachingPanel
│   │   ├── StorySuggestionCard
│   │   ├── StructureHintCard
│   │   └── ConsistencyPanel
│   └── AnswerDisplay
│       ├── QuestionHeader
│       ├── StreamingAnswer
│       └── EnhanceButton
└── Modals
    ├── SettingsModal
    ├── CalibrationModal
    └── HistoryPanel
```

### 4.2 State Management (Zustand)

```typescript
// sessionStore.ts - Key State Slices
interface SessionState {
  // Connection
  status: 'idle' | 'calibrating' | 'listening' | 'processing' | 'listening_paused';
  isConnected: boolean;
  
  // Transcription
  transcriptionHistory: TranscriptionEntry[];
  currentTranscription: string;
  
  // Answers
  answerHistory: AnswerEntry[];
  currentAnswer: { text: string; isStreaming: boolean; confidence: string };
  
  // Context/RAG
  loadedContextFiles: ContextFile[];
  ragState: { hasDocuments: boolean; cacheExpired: boolean };
  
  // Coaching
  storySuggestion: StorySuggestion | null;
  structureHint: StructureHint | null;
  consistencyWarnings: ConsistencyWarning[];
  
  // Accumulation
  accumulating: { speaker: string; preview: string; segmentCount: number } | null;
  
  // Preferences
  preferences: UserPreferences;
}
```

### 4.3 WebSocket Communication

The `useWebSocket` hook manages bidirectional IPC:

```typescript
// Outbound messages
sendMessage(type: MessageType, data: object): void
startSession(apiKeys: ApiKeys, preferences: Preferences): void
stopSession(): void
uploadContext(files: ContextFile[]): void
enhanceAnswer(type: EnhancementType, question: string, answer: string): void

// Inbound message routing (automatic)
TRANSCRIPTION       → transcriptionHistory.push()
ANSWER_CHUNK        → currentAnswer.text += chunk
STORY_SUGGESTION    → storySuggestion = data
CONSISTENCY_WARNING → consistencyWarnings.push()
STATUS              → status = data.state
```

---

## 5. Python Sidecar Architecture

### 5.1 Server Initialization Sequence

```python
# server.py - Startup Flow
1. ModelWarmer.start()           # Background thread loads ML models
   ├── Silero VAD
   ├── ECAPA-TDNN (Speaker ID)
   └── Local Whisper (if GPU available)

2. SidecarServer.__init__()
   ├── SessionHistoryStore()     # SQLite session persistence
   ├── EnhancedContextManager()  # Document processing
   ├── MemoryStore()             # Candidate data persistence
   └── RAGPersistenceManager()   # Document survival across restarts

3. websockets.serve(handler, "localhost", 8765)
```

### 5.2 Message Routing

```python
# _process_message() dispatcher
MESSAGE_TYPE        → HANDLER
─────────────────────────────────────
START_SESSION       → _handle_start_session()
STOP_SESSION        → _handle_stop_session()
UPLOAD_CONTEXT      → _handle_upload_context()
MANUAL_QUESTION     → _handle_manual_question()
ENHANCE_ANSWER      → _handle_enhance_answer()
CALIBRATE_VOICE     → _handle_calibrate_voice()
PREPARE_INTERVIEW   → _handle_prepare_interview()
LOAD_RAG_STATE      → _handle_load_rag_state()
REFRESH_CACHE       → _handle_refresh_cache()
CLEAR_ALL_DATA      → _handle_clear_all_data()
```

### 5.3 Audio Processing Pipeline

```python
async def _audio_loop():
    async for chunk in audio_capture.get_audio_stream():
        # 1. Noise Reduction (optional)
        chunk = noise_reducer.reduce_noise(chunk)
        
        # 2. VAD Processing
        segments = vad_processor.process_chunk(chunk)
        
        # 3. For each speech segment
        for segment in segments:
            # 4. Speaker Diarization
            speaker = speaker_recognizer.identify(segment)
            
            # 5. Streaming STT (parallel)
            streaming_manager.send_audio(segment)
            
            # 6. Utterance Accumulation
            result = accumulator.add_segment(speaker, segment)
            
            if result.is_complete:
                # 7. Trigger Intelligence Pipeline
                await _process_complete_utterance(result)
```

---

## 6. Provider System

### 6.1 Provider Interface Contracts

```python
# STT Provider (Batch)
class STTProvider(ABC):
    async def transcribe(audio: bytes, language: str) -> TranscriptionResult
    def is_available() -> bool

# STT Provider (Streaming)
class StreamingSTTProvider(ABC):
    async def connect(config: StreamingConfig) -> StreamingSession
    
class StreamingSession(ABC):
    async def send_audio(chunk: bytes) -> None
    async def results() -> AsyncIterator[InterimResult | EndOfTurnEvent]

# LLM Provider
class LLMProvider(ABC):
    async def generate_response(prompt, context, history) -> AsyncIterator[str]
    def set_candidate_profile(profile: CandidateProfile) -> None
```

### 6.2 Provider Factory & Fallback

```python
# Factory instantiation with fallback chains
class ProviderFactory:
    STT_FALLBACK_CHAIN = [
        "LOCAL_WHISPER",  # Primary: GPU-accelerated, 100% private
        "GEMINI",         # Fallback: Cloud-based
    ]
    
    LLM_FALLBACK_CHAIN = [
        "GEMINI",     # Primary: Context caching benefits
        "OPENAI",     # Fallback: GPT-5/4o
        "ANTHROPIC",  # Fallback: Claude 4/3.5
    ]
    
    STREAMING_STT_OPTIONS = [
        "DEEPGRAM",      # Nova-3: Acoustic endpointing
        "DEEPGRAM_FLUX", # Semantic endpointing
    ]
```

### 6.3 Provider Capabilities Matrix

| Provider | Type | Model | Key Features |
|----------|------|-------|--------------|
| **LocalWhisper** | STT | large-v3-turbo | GPU (CUDA), 17-34x realtime, private |
| **Gemini** | STT/LLM | Gemini 3 Pro/Flash | Context caching (2h TTL), native search |
| **OpenAI** | LLM | GPT-5.2 / 4o | High reasoning, thinking budget |
| **Anthropic** | LLM | Claude 4 / 3.5 | Precision reasoning, STAR formatting |
| **Deepgram** | Streaming | Nova-3 | ~150ms latency, acoustic endpointing |
| **Deepgram Flux** | Streaming | flux-general | Semantic endpointing |

---

## 7. Intelligence Pipeline

### 7.1 Question Detection (3-Tier)

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: Fast Regex (<2ms)                                       │
│ • WH-questions (What, Why, How, When, Where, Who)               │
│ • Behavioral starters ("Tell me about", "Describe a time")      │
│ • Imperative commands ("Explain", "Walk me through")            │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2: Context-Aware (<10ms)                                   │
│ • Follow-up detection (after long candidate response)           │
│ • Pronoun analysis ("that", "it", "this")                       │
│ • Turn-taking patterns                                          │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3: LLM Fallback (~150ms)                                   │
│ • Ambiguous cases (confidence 0.4-0.75)                         │
│ • Complex multi-clause sentences                                │
│ • Async verification with Gemini Flash                          │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Query Reformulation (TopicStack)

```python
class TopicStack:
    """Maintains conversation context for multi-turn resolution."""
    
    stack: List[TopicEntry]  # Up to 10 recent topics
    
    # Resolution capabilities:
    # 1. Anaphora: "that project" → "the AWS migration project"
    # 2. Ordinal: "the first topic" → stack[0].topic
    # 3. Recency: "go back to earlier" → stack[-3].topic
    
    def resolve(question: str) -> str:
        """Expand references to full context."""
        # Fast path: Template expansion (<5ms)
        # Slow path: LLM reformulation (~150ms)
```

### 7.3 Utterance Accumulation (4-Tier Completeness)

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: Punctuation (<1ms)                                      │
│ • Terminal: ? or . (if imperative)                              │
│ • Immediate finalization                                        │
├─────────────────────────────────────────────────────────────────┤
│ TIER 2: Syntax (<5ms)                                           │
│ • Complete sentence patterns (WH + aux + subject)               │
│ • Imperative structures                                         │
├─────────────────────────────────────────────────────────────────┤
│ TIER 3: Timing (<1ms)                                           │
│ • Soft timeout: 2s (wait for more speech)                       │
│ • Hard timeout: 5s (force completion)                           │
├─────────────────────────────────────────────────────────────────┤
│ TIER 4: LLM (~150ms)                                            │
│ • Semantic completeness check                                   │
│ • Only for ambiguous fragments                                  │
├─────────────────────────────────────────────────────────────────┤
│ HYBRID MODE: Streaming Integration                              │
│ • Semantic endpoint (confidence > 0.7) → Bypass timing          │
│ • Acoustic endpoint → Fall back to timing tiers                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. RAG & Context Management

### 8.1 Document Ingestion Flow

```
Document Upload
      │
      ▼
┌─────────────────┐
│  Parse & Decode │ (PDF, DOCX, TXT → plaintext)
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Section Detect  │ (Pre-chunking: "Experience", "Requirements", etc.)
└─────────────────┘
      │
      ▼
┌─────────────────┐
│  Hierarchical   │ Parent (4096 chars) + Children (1024 chars)
│    Chunking     │ QA-Atomic: Keep Q&A pairs together
└─────────────────┘
      │
      ▼
┌─────────────────┐
│   Enrichment    │ Extract: tech keywords, companies, dates, roles
└─────────────────┘
      │
      ├──────────────────────────────────┐
      ▼                                  ▼
┌─────────────────┐              ┌─────────────────┐
│   ChromaDB      │              │  Gemini Cache   │
│ (Vector Store)  │              │  (File API)     │
└─────────────────┘              └─────────────────┘
```

### 8.2 Retrieval Strategy

```python
# Document Priority by Question Type
DOC_PRIORITY = {
    "behavioral":  [SAMPLE_QA, RESUME],
    "technical":   [SAMPLE_QA, RESUME, JOB_DESCRIPTION],
    "motivation":  [COMPANY_INFO, JOB_DESCRIPTION, RESUME],
    "intro":       [RESUME, SAMPLE_QA],
    "weakness":    [SAMPLE_QA, RESUME],
    "general":     [SAMPLE_QA, RESUME, JOB_DESCRIPTION, COMPANY_INFO],
}

# Retrieval Flow
1. Embed question + sub-questions (batch)
2. Query ChromaDB for child chunks (high precision)
3. Expand to parent chunks (high context)
4. Sort by: DocumentType priority → Vector distance
5. Deduplicate by 200-char prefix hash
```

### 8.3 Gemini Context Caching

```python
class GeminiCacheManager:
    """Manages 2-hour TTL context caches for reduced latency."""
    
    # Atomic swap pattern for cache updates
    def update_cache(new_content):
        new_cache = create_cache(new_content)
        old_cache = self.current_cache
        self.current_cache = new_cache  # Atomic pointer swap
        delete_cache(old_cache)         # Cleanup after success
    
    # Version tracking with SHA-256
    def needs_refresh(content, profile) -> bool:
        current_hash = sha256(content + profile)
        return current_hash != self.cached_hash
```

---

## 9. Coaching & Memory Systems

### 9.1 Memory Store Schema (SQLite)

```sql
-- Documents metadata
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT,
    document_type TEXT,
    summary TEXT,
    created_at TIMESTAMP
);

-- Extracted facts (skills, timeline, achievements)
CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    facts_json TEXT,  -- ExtractedFacts serialized
    created_at TIMESTAMP
);

-- STAR stories (8-12 per candidate)
CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    title TEXT,
    situation TEXT,
    task TEXT,
    action TEXT,
    result TEXT,
    metrics TEXT,      -- JSON array
    tags TEXT,         -- JSON array
    opening_line TEXT,
    source_company TEXT
);

-- Candidate profile (singleton)
CREATE TABLE profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    profile_json TEXT,  -- CandidateProfile serialized
    updated_at TIMESTAMP
);

-- Session claims (for consistency tracking)
CREATE TABLE session_claims (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    claim_type TEXT,
    claim_value TEXT,
    source_answer TEXT,
    timestamp TIMESTAMP
);
```

### 9.2 Extraction Pipeline

```
Document Upload
      │
      ▼
┌─────────────────┐
│  Summarization  │ → High-level summary + key points
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Fact Extraction │ → Skills, timeline, metrics, achievements
└─────────────────┘
      │
      ▼
┌─────────────────┐
│Story Extraction │ → 8-12 STAR stories with opening lines
└─────────────────┘
      │
      ▼
┌─────────────────┐
│Profile Generate │ → ~1000 token candidate summary
└─────────────────┘
      │
      ▼
    Memory Store + Profile Injection into LLM prompts
```

### 9.3 Coaching Engine Components

| Component | Algorithm | Output |
|-----------|-----------|--------|
| **Story Recaller** | Embedding similarity (cosine, threshold 0.65) | `STORY_SUGGESTION` message |
| **Structure Suggester** | Heuristic question subtype classification | `STRUCTURE_SUGGESTION` message |
| **Consistency Tracker** | Regex claim extraction + variance detection | `CONSISTENCY_WARNING` message |

---

## 10. IPC Protocol Reference

### 10.1 Message Format

```json
{
  "type": "MESSAGE_TYPE",
  "data": { ... }
}
```

### 10.2 Client → Server Messages

| Type | Data | Purpose |
|------|------|---------|
| `START_SESSION` | `{apiKeys, preferences}` | Initialize providers, start audio |
| `STOP_SESSION` | `{}` | End session, preserve RAG context |
| `UPLOAD_CONTEXT` | `{files: [{name, content, documentType}]}` | Upload documents |
| `MANUAL_QUESTION` | `{question}` | Trigger answer for typed question |
| `ENHANCE_ANSWER` | `{enhancementType, originalQuestion, originalAnswer}` | Refine previous answer |
| `CALIBRATE_VOICE` | `{audioData}` | Train speaker recognition |
| `PREPARE_INTERVIEW` | `{}` | Generate interview preparation |
| `LOAD_RAG_STATE` | `{}` | Check persisted documents |
| `REFRESH_CACHE` | `{}` | Rebuild Gemini context cache |
| `CLEAR_ALL_DATA` | `{}` | Delete all documents |

### 10.3 Server → Client Messages

| Type | Data | Purpose |
|------|------|---------|
| `STATUS` | `{state}` | Session state change |
| `TRANSCRIPTION` | `{speaker, text, timestamp, confidence}` | Final transcription |
| `INTERIM_TRANSCRIPTION` | `{text, timestamp, speaker}` | Partial transcription |
| `ACCUMULATING` | `{speaker, bufferPreview, segmentCount}` | Buffering indicator |
| `ANSWER_START` | `{}` | LLM generation started |
| `ANSWER_CHUNK` | `{chunk, complete, confidence}` | Streaming answer token |
| `STORY_SUGGESTION` | `{storyId, title, situation, relevanceScore, ...}` | Relevant STAR story |
| `STRUCTURE_SUGGESTION` | `{name, sections, tips}` | Answer framework hint |
| `CONSISTENCY_WARNING` | `{contradictions}` | Claim contradiction alert |
| `EXTRACTION_PROGRESS` | `{stage, progress, message}` | Document processing update |
| `RAG_STATE` | `{hasDocuments, documentCount, cacheExpired}` | Persistence status |
| `ERROR` | `{message, code}` | Error notification |

### 10.4 Enhancement Types

| Type | Behavior |
|------|----------|
| `add_detail` | Re-query RAG with higher limit, expand context |
| `make_specific` | Add metrics, numbers, concrete examples |
| `suggest_star` | Link to relevant STAR story from memory |
| `adjust_tone` | Rewrite with different tone (confident/humble) |
| `shorten` | Compress to key points only |

---

## 11. Latency Architecture

### 11.1 Pre-warming Strategy

```python
class ModelWarmer:
    """Background thread loads models at app startup."""
    
    WARMUP_ORDER = [
        ("silero_vad", 1.2),      # ~1.2s
        ("ecapa_tdnn", 2.5),      # ~2.5s (speaker ID)
        ("whisper_turbo", 8.0),   # ~8s (if GPU available)
    ]
    
    # Result: <1s session start after warmup complete
```

### 11.2 Parallel Processing

```python
# Concurrent operations during question processing
async def _process_question_pipeline(question):
    # Launch coaching in parallel (don't block answer generation)
    story_task = asyncio.create_task(story_recaller.find_relevant_story(question))
    structure_task = asyncio.create_task(structure_suggester.suggest(question))
    
    # Main path: RAG + LLM
    context = await rag_engine.retrieve(question)
    async for chunk in llm_provider.generate_response(question, context):
        await broadcast(ANSWER_CHUNK, chunk)
    
    # Collect coaching results (already running in parallel)
    story = await story_task
    structure = await structure_task
```

### 11.3 Streaming STT Integration

```
Traditional Pipeline:
  Audio → VAD → Batch STT (wait) → Process
  Latency: ~800-1500ms

Streaming Pipeline:
  Audio → VAD → Streaming STT → Hybrid Endpointing → Process
  Latency: ~300-600ms (30-50% improvement)
```

---

## 12. Security & Privacy

### 12.1 API Key Storage

```rust
// keyring.rs - OS-level secure storage
// Windows: Credential Manager
// macOS: Keychain
// Linux: Secret Service API

pub fn store_key(service: &str, key: &str) -> Result<()>
pub fn retrieve_key(service: &str) -> Result<String>
pub fn delete_key(service: &str) -> Result<()>
```

### 12.2 Privacy Modes

| Mode | STT | LLM | Data Location |
|------|-----|-----|---------------|
| **Full Privacy** | Local Whisper | Local (future) | 100% on-device |
| **Hybrid** | Local Whisper | Cloud LLM | Audio stays local |
| **Cloud** | Gemini/Deepgram | Gemini/OpenAI | Encrypted transit |

### 12.3 Session Isolation

```python
# On STOP_SESSION:
# Cleared:
- Conversation history
- Session claims
- Streaming buffers

# Preserved (for UX):
- RAG indexes
- Gemini context cache
- Memory store (candidate profile)

# On CLEAR_ALL_DATA:
# Everything deleted, fresh start
```

---

## Appendix A: File Structure

```
live_interview_agent/
├── src/                          # React Frontend
│   └── ui/
│       ├── components/           # React components
│       ├── hooks/                # useWebSocket, useVAD
│       └── store/                # Zustand sessionStore
├── src-tauri/                    # Tauri Backend
│   └── src/
│       ├── commands/             # sidecar.rs, config.rs
│       └── utils/                # keyring.rs
├── sidecar/                      # Python Sidecar
│   └── src/
│       ├── server.py             # WebSocket server
│       ├── protocol.py           # IPC definitions
│       ├── warmup.py             # Model pre-loading
│       ├── audio/                # capture, vad, diarization
│       ├── providers/            # stt/, llm/, factory
│       ├── classification/       # detector, reformulator, splitter
│       ├── rag/                  # engine, store, embeddings
│       ├── context/              # manager, chunker, cache
│       ├── memory/               # store, models
│       ├── coaching/             # recaller, suggester, tracker
│       ├── extraction/           # pipeline, extractors
│       └── evaluation/           # groundedness, analytics
├── ARCHITECTURE.md               # This document
├── AGENTS.md                     # AI agent instructions
└── README.md                     # User-facing documentation
```

---

## Appendix B: Environment Variables

```bash
# Streaming STT
STREAMING_STT_PROVIDER=deepgram      # deepgram, deepgram_flux, disabled

# Utterance Accumulation
ACCUMULATOR_ENABLED=true
ACCUMULATOR_MERGE_GAP_MS=500
ACCUMULATOR_SOFT_TIMEOUT_MS=2000
ACCUMULATOR_HARD_TIMEOUT_MS=5000
ACCUMULATOR_ENDPOINTING_MODE=hybrid  # timing, streaming, hybrid

# Evaluation
GROUNDEDNESS_EVALUATION_ENABLED=true
GROUNDEDNESS_USE_LLM=false           # Use heuristic by default

# Local Whisper
WHISPER_MODEL_SIZE=large-v3-turbo    # large-v3-turbo, distil-large-v3, medium
WHISPER_DEVICE=cuda                  # cuda, cpu
WHISPER_COMPUTE_TYPE=int8_float16    # int8_float16, float16, int8
```

---

*This document is auto-generated from codebase analysis. For implementation details, refer to the source files listed in each section.*
