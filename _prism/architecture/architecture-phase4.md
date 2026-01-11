# Architecture: Phase 4 - Interview Coach Evolution

**Version**: 1.0
**Date**: 2026-01-10
**Author**: Prism Architect Agent
**Status**: Draft - Pending Approval

---

## Overview

This document defines the technical architecture for Phase 4, transforming the Live Interview Agent from a reactive answer generator into a proactive interview coach. The architecture introduces five major subsystems that work together to provide comprehensive preparation and real-time coaching.

---

## Architecture Principles

1. **Persistent Over Ephemeral**: User context persists across the session, not fetched per-question
2. **Speculative Over Reactive**: Begin work before certainty (retrieval before segment ends)
3. **Layered Classification**: Fast rules first, slow LLM only when needed
4. **User-First Design**: Optimize for user confidence, not just LLM accuracy
5. **Graceful Degradation**: Features work with partial data or provider failures

---

## System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PHASE 4 ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                         DOCUMENT UPLOAD                                   │   │
│  │                                                                           │   │
│  │   Resume ─┬──▶ Parser ──▶ ┌─────────────────────────────────────────┐    │   │
│  │   JD ─────┤               │        EXTRACTION PIPELINE              │    │   │
│  │   Company─┤               │  ┌─────────┐  ┌─────────┐  ┌─────────┐  │    │   │
│  │   HM Info─┘               │  │Summarize│  │Extract  │  │Extract  │  │    │   │
│  │                           │  │(Doc+Sec)│  │Facts    │  │Stories  │  │    │   │
│  │                           │  └────┬────┘  └────┬────┘  └────┬────┘  │    │   │
│  │                           └───────┼───────────┼───────────┼────────┘    │   │
│  │                                   │           │           │              │   │
│  │                                   ▼           ▼           ▼              │   │
│  │                           ┌─────────────────────────────────────────┐    │   │
│  │                           │         PERSISTENT MEMORY STORE         │    │   │
│  │                           │  • Document Summaries                   │    │   │
│  │                           │  • Section Summaries                    │    │   │
│  │                           │  • Skills Inventory                     │    │   │
│  │                           │  • Career Timeline                      │    │   │
│  │                           │  • Achievement Metrics                  │    │   │
│  │                           │  • STAR Story Bank (8-12 stories)       │    │   │
│  │                           │  • Candidate Profile (~1000 tokens)     │    │   │
│  │                           └─────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                          │                                       │
│                                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      PLAYBOOK GENERATION                                  │   │
│  │                                                                           │   │
│  │   Memory Store ──▶ Question Generator ──▶ Answer Drafter ──▶ Playbook    │   │
│  │                          │                      │                         │   │
│  │                          ▼                      ▼                         │   │
│  │                    20+ Questions          Competency Map                  │   │
│  │                    by Category            Story Bank                      │   │
│  │                                           Gap Analysis                    │   │
│  │                                           Cheat Sheet                     │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                      LIVE INTERVIEW SESSION                               │   │
│  │                                                                           │   │
│  │   Audio ──▶ VAD ──▶ ┌────────────────────────────────────────────────┐   │   │
│  │                     │         ENHANCED TRANSCRIPTION                  │   │   │
│  │                     │  • Streaming interim to UI                      │   │   │
│  │                     │  • Speculative clause detection                 │   │   │
│  │                     │  • Segment merging for brief pauses            │   │   │
│  │                     └───────────────────┬────────────────────────────┘   │   │
│  │                                         │                                 │   │
│  │                                         ▼                                 │   │
│  │                     ┌────────────────────────────────────────────────┐   │   │
│  │                     │         ENHANCED DETECTION (3-TIER)             │   │   │
│  │                     │  Tier 1: Rule-based (<2ms)                      │   │   │
│  │                     │  Tier 2: Context-aware (<10ms)                  │   │   │
│  │                     │  Tier 3: LLM fallback (<150ms) ─── NEW          │   │   │
│  │                     └───────────────────┬────────────────────────────┘   │   │
│  │                                         │                                 │   │
│  │                           ┌─────────────┴─────────────┐                  │   │
│  │                           │                           │                  │   │
│  │                           ▼                           ▼                  │   │
│  │   ┌───────────────────────────────┐   ┌───────────────────────────────┐ │   │
│  │   │     COACHING ENGINE           │   │     ANSWER GENERATION         │ │   │
│  │   │  • Story Recall (<1s)         │   │  • Candidate Profile injected │ │   │
│  │   │  • Structure Suggestion       │   │  • RAG + Extracted Facts      │ │   │
│  │   │  • Duration Tracking          │   │  • Consistency Check          │ │   │
│  │   │  • Consistency Panel          │   │  • Streaming Response         │ │   │
│  │   └───────────────────────────────┘   └───────────────────────────────┘ │   │
│  │                           │                           │                  │   │
│  │                           └───────────┬───────────────┘                  │   │
│  │                                       ▼                                  │   │
│  │                     ┌────────────────────────────────────────────────┐   │   │
│  │                     │              UI DISPLAY                         │   │   │
│  │                     │  • Suggested Story Panel                        │   │   │
│  │                     │  • Answer Structure Hints                       │   │   │
│  │                     │  • Generated Answer (streaming)                 │   │   │
│  │                     │  • Consistency Tracker                          │   │   │
│  │                     │  • Duration Indicator                           │   │   │
│  │                     └────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Extraction Pipeline

#### 1.1 Document Summarizer

**Purpose**: Generate hierarchical summaries for persistent memory

**Input**: Parsed document text + document type
**Output**: Document-level summary + section-level summaries

```python
@dataclass
class DocumentSummary:
    document_id: str
    document_type: DocumentType
    document_summary: str  # ~200 words
    section_summaries: Dict[str, str]  # section_name -> ~50 words each
    key_points: List[str]  # 5-10 bullet points
    generated_at: datetime
```

**Implementation**:
- Single LLM call with structured output prompt
- Prompt includes document type for tailored extraction
- Cache summaries in memory store

#### 1.2 Fact Extractor

**Purpose**: Extract structured factual data for profile and consistency tracking

**Input**: Parsed document text (primarily resume)
**Output**: Structured facts

```python
@dataclass
class ExtractedFacts:
    skills: List[SkillEntry]  # skill, years, proficiency
    timeline: List[CareerEntry]  # company, role, dates, highlights
    achievements: List[Achievement]  # description, metrics, context
    education: List[Education]  # institution, degree, year
    certifications: List[str]
    total_experience_years: int
    current_role: str
    industries: List[str]
```

```python
@dataclass
class SkillEntry:
    name: str
    years: Optional[int]
    proficiency: str  # expert, proficient, familiar
    last_used: Optional[str]
    
@dataclass
class CareerEntry:
    company: str
    role: str
    start_date: str
    end_date: Optional[str]
    highlights: List[str]
    metrics: List[str]
    
@dataclass
class Achievement:
    description: str
    metrics: List[str]  # "40% reduction", "$2M saved"
    context: str  # which company/role
    tags: List[str]  # leadership, technical, scale
```

**Implementation**:
- LLM call with JSON schema enforcement
- Fallback to regex extraction for common patterns
- Merge facts from multiple documents (resume + JD requirements)

#### 1.3 Story Extractor

**Purpose**: Identify and structure STAR story candidates from resume

**Input**: Career entries + achievements from Fact Extractor
**Output**: STAR Story Bank

```python
@dataclass
class STARStory:
    id: str
    title: str  # "The Migration Crisis"
    situation: str  # 2-3 sentences
    task: str  # 1-2 sentences
    action: str  # 3-5 sentences with specifics
    result: str  # 1-2 sentences with metrics
    metrics: List[str]  # ["40% latency reduction", "zero downtime"]
    tags: List[str]  # ["leadership", "crisis", "technical", "scale"]
    source_company: str
    opening_line: str  # Suggested first sentence
    twenty_second_version: str  # Compressed version
    confidence: float  # How complete is this story
```

**Implementation**:
- LLM identifies story candidates from achievements
- Prompts for STAR structure completion
- Tags generated based on content analysis
- Stories ranked by completeness and relevance

---

### 2. Persistent Memory Store

**Purpose**: Central storage for all extracted and generated context

**Storage**: SQLite database + JSON files

```sql
-- Schema
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    filename TEXT,
    uploaded_at TIMESTAMP,
    summary TEXT,
    section_summaries JSON
);

CREATE TABLE facts (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(id),
    fact_type TEXT,  -- skill, career, achievement, education
    data JSON,
    extracted_at TIMESTAMP
);

CREATE TABLE stories (
    id TEXT PRIMARY KEY,
    title TEXT,
    situation TEXT,
    task TEXT,
    action TEXT,
    result TEXT,
    metrics JSON,
    tags JSON,
    source_company TEXT,
    opening_line TEXT,
    twenty_second_version TEXT,
    confidence REAL,
    created_at TIMESTAMP
);

CREATE TABLE candidate_profile (
    id TEXT PRIMARY KEY,
    profile_text TEXT,  -- The ~1000 token summary
    generated_at TIMESTAMP,
    source_documents JSON
);

CREATE TABLE session_claims (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    claim_text TEXT,
    claim_type TEXT,  -- experience_years, skill_level, metric
    timestamp TIMESTAMP
);
```

**Profile Generation**:

```python
def generate_candidate_profile(facts: ExtractedFacts, summaries: List[DocumentSummary]) -> str:
    """Generate compact profile for prompt injection (~1000 tokens)"""
    template = """
## Candidate Profile

**Current Role**: {current_role}
**Experience**: {total_years} years across {industries}

### Core Competencies
{skills_summary}

### Career Highlights
{career_summary}

### Key Achievements
{achievements_summary}

### Target Role Context
{role_context}
"""
    # Fill template from extracted facts
    return formatted_profile
```

---

### 3. Playbook Generator

**Purpose**: Generate comprehensive interview preparation document

#### 3.1 Question Generator

**Input**: JD requirements, role level, company context, interviewer info
**Output**: 20+ categorized questions

```python
@dataclass
class PlaybookQuestion:
    id: str
    text: str
    category: str  # behavioral, technical, motivation, situational, curveball
    subcategory: str  # leadership, conflict, technical_depth, etc.
    difficulty: str  # standard, challenging, curveball
    why_likely: str  # Why this question is expected
    jd_requirement: Optional[str]  # Which JD requirement it tests
    suggested_story: Optional[str]  # Story ID to use
    answer_framework: str  # STAR, Concept-Example, etc.
    suggested_answer: str  # Full suggested answer
    key_points: List[str]  # Bullet points to hit
```

**Question Categories**:

| Category | Count | Source |
|----------|-------|--------|
| Behavioral | 6-8 | JD competencies + universal |
| Technical | 4-6 | JD requirements + resume skills |
| Motivation | 3-4 | Company + role specific |
| Situational | 3-4 | Role level + industry |
| Curveball | 2-3 | Weakness areas + edge cases |

**Implementation**:
- Multi-prompt pipeline:
  1. Extract JD competencies → question topics
  2. Match topics to question templates
  3. Tailor questions to role level
  4. Generate suggested answers from resume
  5. Map stories to behavioral questions

#### 3.2 Competency Mapper

**Input**: JD requirements, extracted facts
**Output**: Requirement-to-evidence mapping

```python
@dataclass
class CompetencyMapping:
    requirement: str  # "5+ years Python experience"
    evidence: str  # "7 years at Companies X, Y, Z"
    metrics: List[str]  # Supporting numbers
    emphasis: str  # What to highlight
    gap_risk: Optional[str]  # Any concern
    talking_points: List[str]
```

#### 3.3 Playbook Assembler

**Output Format**:

```markdown
# Interview Playbook: [Role] at [Company]
Generated: [Date]

## Executive Summary
[Positioning statement - 20s/60s/2min versions]

## Competency Mapping
| Requirement | Your Evidence | Key Metrics |
|-------------|---------------|-------------|
...

## Question Bank (20+ Questions)

### Behavioral Questions (8)
#### Q1: Tell me about a time you led a team through a difficult project
**Why Expected**: JD mentions "leadership" and "cross-functional collaboration"
**Suggested Story**: The Migration Crisis
**Key Points**:
- Led 8-person team
- 6-week deadline
- 40% latency improvement
**Suggested Answer**: [Full STAR answer]
...

### Technical Questions (6)
...

### Motivation Questions (4)
...

### Situational Questions (3)
...

### Curveball Questions (2)
...

## STAR Story Bank
| Story | Tags | 20s Version | When to Use |
|-------|------|-------------|-------------|
...

## Gap Analysis & Mitigations
| Gap/Risk | Mitigation Script |
|----------|-------------------|
...

## Questions to Ask
1. [High-signal question]
...

## One-Page Cheat Sheet
[Condensed reference for right before interview]
```

---

### 4. Enhanced Question Detection (Tier 3)

**Purpose**: Catch ambiguous questions that Tier 1+2 miss

#### 4.1 Tier 3 Trigger Logic

```python
def should_invoke_tier3(tier1_result: ClassificationResult, 
                         tier2_result: ClassificationResult,
                         text: str) -> bool:
    """Determine if Tier 3 LLM fallback needed"""
    confidence = max(tier1_result[1], tier2_result[1])
    
    # Low confidence AND looks potentially interrogative
    if confidence < 0.7:
        interrogative_signals = [
            '?' in text,
            text.lower().startswith(('what', 'how', 'why', 'tell', 'describe')),
            'you' in text.lower(),
            len(text.split()) > 5,  # Not just a short acknowledgment
        ]
        if sum(interrogative_signals) >= 2:
            return True
    
    return False
```

#### 4.2 Tier 3 Implementation

```python
TIER3_PROMPT = """You are analyzing interview transcriptions.
Determine if this utterance is a question that requires the interviewee to respond.

Utterance: "{text}"

Recent context:
{recent_context}

Respond with ONLY one of:
- QUESTION: This requires a substantive answer
- NOT_QUESTION: This is a statement, acknowledgment, or small talk

Your response:"""

async def tier3_classify(text: str, history: List[str]) -> Tuple[bool, float]:
    """Fast LLM classification for ambiguous cases"""
    prompt = TIER3_PROMPT.format(
        text=text,
        recent_context="\n".join(history[-3:])
    )
    
    # Use fastest available model
    response = await fast_llm.complete(prompt, max_tokens=10)
    
    is_question = "QUESTION" in response.upper()
    confidence = 0.85 if is_question else 0.80
    
    return is_question, confidence
```

#### 4.3 Parallel Execution

```python
async def detect_with_speculation(text: str, history: List) -> ClassificationResult:
    """Run Tier 3 in parallel with speculative retrieval"""
    
    # Start both in parallel
    tier3_task = asyncio.create_task(tier3_classify(text, history))
    speculative_rag_task = asyncio.create_task(speculative_retrieve(text))
    
    # Tier 3 result determines if we use the RAG results
    is_question, confidence = await tier3_task
    
    if is_question:
        # RAG results ready or nearly ready
        rag_results = await speculative_rag_task
        return (True, confidence, "interview_question", rag_results)
    else:
        # Cancel RAG if not needed
        speculative_rag_task.cancel()
        return (False, confidence, "statement", None)
```

---

### 5. Continuous-Feel Transcription

**Purpose**: Make the system feel responsive during interviewer speech

#### 5.1 Interim Streaming

```python
class StreamingTranscriber:
    """Wrapper for STT with interim result streaming"""
    
    async def transcribe_streaming(self, audio_stream: AsyncIterator[bytes]):
        """Yield interim and final transcripts"""
        
        async for audio_chunk in audio_stream:
            # If provider supports streaming
            if self.provider.supports_streaming:
                async for interim in self.provider.transcribe_stream(audio_chunk):
                    yield TranscriptUpdate(
                        text=interim.text,
                        is_final=interim.is_final,
                        confidence=interim.confidence
                    )
            else:
                # Fallback: buffer and send on VAD segment
                self.buffer.append(audio_chunk)
                if self.vad.is_segment_end():
                    result = await self.provider.transcribe(self.buffer)
                    yield TranscriptUpdate(text=result.text, is_final=True)
```

#### 5.2 Speculative Query Formation

```python
class SpeculativeProcessor:
    """Begin processing before segment is complete"""
    
    def __init__(self):
        self.clause_detector = ClauseDetector()
        self.pending_query = None
        self.pending_retrieval = None
    
    async def on_interim_transcript(self, text: str):
        """Called with each interim transcript update"""
        
        # Detect if we have a complete clause
        if self.clause_detector.has_complete_clause(text):
            # Form speculative query
            self.pending_query = self.reformulate_partial(text)
            
            # Start speculative retrieval
            self.pending_retrieval = asyncio.create_task(
                self.rag_engine.retrieve(self.pending_query, limit=5)
            )
    
    async def on_segment_complete(self, final_text: str):
        """Called when VAD detects segment end"""
        
        # If we have pending retrieval, check if still valid
        if self.pending_retrieval and self.is_query_still_valid(final_text):
            # Use pre-fetched results
            results = await self.pending_retrieval
        else:
            # Query changed significantly, fetch fresh
            results = await self.rag_engine.retrieve(final_text, limit=5)
        
        return results
```

#### 5.3 Segment Merging

```python
class SegmentMerger:
    """Merge segments when interviewer pauses briefly mid-question"""
    
    MERGE_WINDOW_MS = 500  # Merge if gap < 500ms
    
    def __init__(self):
        self.pending_segment = None
        self.pending_timer = None
    
    async def on_segment(self, segment: SpeechSegment):
        """Process incoming segment with merge logic"""
        
        if self.pending_segment is None:
            self.pending_segment = segment
            self.pending_timer = asyncio.create_task(
                self._wait_for_continuation()
            )
        else:
            # Check if this continues the previous segment
            gap = segment.start_time - self.pending_segment.end_time
            
            if gap < self.MERGE_WINDOW_MS:
                # Merge
                self.pending_segment = self._merge(self.pending_segment, segment)
                # Reset timer
                self.pending_timer.cancel()
                self.pending_timer = asyncio.create_task(
                    self._wait_for_continuation()
                )
            else:
                # Gap too long, finalize previous
                await self._finalize(self.pending_segment)
                self.pending_segment = segment
```

---

### 6. Coaching Engine

**Purpose**: Provide real-time guidance during interview

#### 6.1 Story Recall

```python
class StoryRecaller:
    """Match detected questions to STAR stories"""
    
    def __init__(self, story_bank: List[STARStory], embedder):
        self.stories = story_bank
        self.embedder = embedder
        # Pre-compute story embeddings
        self.story_embeddings = {
            s.id: embedder.embed(f"{s.title} {s.situation} {' '.join(s.tags)}")
            for s in story_bank
        }
    
    async def find_relevant_story(self, question: str, question_type: str) -> Optional[StoryMatch]:
        """Find best matching story for question"""
        
        if question_type != "behavioral":
            return None
        
        question_embedding = await self.embedder.embed_async(question)
        
        best_match = None
        best_score = 0.0
        
        for story in self.stories:
            score = cosine_similarity(question_embedding, self.story_embeddings[story.id])
            if score > best_score and score > 0.6:  # Threshold
                best_score = score
                best_match = story
        
        if best_match:
            return StoryMatch(
                story=best_match,
                relevance_score=best_score,
                suggested_opening=best_match.opening_line
            )
        
        return None
```

#### 6.2 Answer Structure Suggestion

```python
STRUCTURE_BY_TYPE = {
    "behavioral": {
        "name": "STAR Method",
        "structure": ["Situation (15%)", "Task (10%)", "Action (60%)", "Result (15%)"],
        "tips": ["Focus on YOUR actions", "Include specific metrics", "End with learning"]
    },
    "technical": {
        "name": "Concept-Example-Tradeoff",
        "structure": ["Core Concept", "Your Experience", "Tradeoffs/Considerations"],
        "tips": ["Start with the 'what'", "Ground in real examples", "Show depth"]
    },
    "motivation": {
        "name": "Company-Role-Value",
        "structure": ["Company Insight", "Role Alignment", "Mutual Value"],
        "tips": ["Be specific about the company", "Show genuine interest"]
    }
}

def get_structure_hint(question_type: str) -> StructureHint:
    template = STRUCTURE_BY_TYPE.get(question_type, STRUCTURE_BY_TYPE["behavioral"])
    return StructureHint(
        method_name=template["name"],
        sections=template["structure"],
        tips=template["tips"]
    )
```

#### 6.3 Consistency Tracker

```python
class ConsistencyTracker:
    """Track claims made during session for consistency"""
    
    def __init__(self):
        self.claims: List[Claim] = []
        self.claim_patterns = [
            (r"(\d+)\s*(?:years?|yrs?)\s+(?:of\s+)?experience", "experience_years"),
            (r"led\s+(?:a\s+)?team\s+of\s+(\d+)", "team_size"),
            (r"(\d+)%\s+(?:improvement|reduction|increase)", "metric_percent"),
            (r"\$(\d+(?:,\d+)?(?:\.\d+)?[KMB]?)", "metric_money"),
        ]
    
    def extract_claims(self, text: str) -> List[Claim]:
        """Extract factual claims from text"""
        claims = []
        for pattern, claim_type in self.claim_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                claims.append(Claim(
                    value=match,
                    claim_type=claim_type,
                    context=text[:100],
                    timestamp=datetime.now()
                ))
        return claims
    
    def check_consistency(self, new_claims: List[Claim]) -> List[Inconsistency]:
        """Check new claims against existing ones"""
        inconsistencies = []
        
        for new_claim in new_claims:
            for existing in self.claims:
                if existing.claim_type == new_claim.claim_type:
                    if existing.value != new_claim.value:
                        inconsistencies.append(Inconsistency(
                            existing=existing,
                            new=new_claim,
                            message=f"Previously said {existing.value}, now saying {new_claim.value}"
                        ))
        
        return inconsistencies
```

---

## Data Flow

### Document Upload Flow

```
1. User uploads document
2. Parser extracts text (existing)
3. NEW: Summarizer generates doc + section summaries
4. NEW: Fact Extractor pulls structured data
5. NEW: Story Extractor identifies STAR candidates
6. Chunker creates RAG chunks (existing)
7. NEW: Profile Generator creates/updates candidate profile
8. All stored in Memory Store
```

### Playbook Generation Flow

```
1. User clicks "Generate Playbook"
2. Load all data from Memory Store
3. Question Generator creates 20+ questions
4. Answer Drafter generates suggested answers
5. Competency Mapper creates JD→Evidence table
6. Story Mapper links stories to questions
7. Gap Analyzer identifies weaknesses
8. Cheat Sheet Generator creates 1-pager
9. Playbook Assembler creates final document
10. Export to Markdown/PDF
```

### Live Session Flow

```
1. Audio captured (existing)
2. NEW: Interim transcript streamed to UI
3. NEW: Speculative retrieval starts on clause detection
4. VAD finalizes segment (existing, with merging)
5. Tier 1+2 classification (existing)
6. NEW: Tier 3 LLM if confidence < 0.7
7. If question:
   a. NEW: Story Recaller finds matching STAR
   b. NEW: Structure Suggester provides framework
   c. Answer Generator with injected profile (enhanced)
   d. NEW: Consistency Tracker checks claims
8. Stream answer to UI (existing)
9. NEW: Display coaching hints alongside answer
```

---

## API Changes

### New WebSocket Messages

```typescript
// Client → Server
{ type: "GENERATE_PLAYBOOK" }
{ type: "START_PRACTICE_MODE", data: { questionIds: string[] } }

// Server → Client
{ type: "PLAYBOOK_READY", data: { playbook: PlaybookData, exportUrl: string } }
{ type: "PLAYBOOK_PROGRESS", data: { step: string, progress: number } }
{ type: "INTERIM_TRANSCRIPT", data: { text: string, speaker: string } }
{ type: "STORY_SUGGESTION", data: { story: STARStory, relevance: number } }
{ type: "STRUCTURE_HINT", data: { method: string, sections: string[] } }
{ type: "CONSISTENCY_WARNING", data: { message: string, existing: string, new: string } }
{ type: "EXTRACTION_COMPLETE", data: { facts: ExtractedFacts, stories: STARStory[] } }
```

### New REST Endpoints (Optional)

```
GET  /api/playbook/{session_id}/export?format=pdf
GET  /api/profile
PUT  /api/profile  (manual edits)
GET  /api/stories
PUT  /api/stories/{id}  (manual edits)
```

---

## File Structure

```
sidecar/src/
├── extraction/                    # NEW
│   ├── __init__.py
│   ├── summarizer.py             # Document/section summarization
│   ├── fact_extractor.py         # Structured fact extraction
│   ├── story_extractor.py        # STAR story identification
│   └── profile_generator.py      # Candidate profile generation
├── memory/                        # NEW
│   ├── __init__.py
│   ├── store.py                  # SQLite-based memory store
│   ├── models.py                 # Data models (Facts, Stories, Profile)
│   └── migrations.py             # Schema migrations
├── playbook/                      # NEW
│   ├── __init__.py
│   ├── question_generator.py     # 20+ question generation
│   ├── answer_drafter.py         # Suggested answer generation
│   ├── competency_mapper.py      # JD→Evidence mapping
│   ├── gap_analyzer.py           # Weakness identification
│   ├── assembler.py              # Final playbook assembly
│   └── exporter.py               # PDF/Markdown export
├── coaching/                      # NEW
│   ├── __init__.py
│   ├── story_recaller.py         # Match questions to stories
│   ├── structure_suggester.py    # Answer framework hints
│   ├── consistency_tracker.py    # Claim tracking
│   └── duration_monitor.py       # Answer length tracking
├── classification/
│   ├── question_detector.py      # MODIFIED: Add Tier 3
│   └── tier3_detector.py         # NEW: LLM fallback
├── audio/
│   ├── vad.py                    # MODIFIED: Segment merging
│   └── streaming.py              # NEW: Interim transcript handling
└── server.py                      # MODIFIED: New handlers
```

---

## Migration Strategy

1. **Phase 4A**: Extraction + Memory Store + Playbook (no breaking changes)
2. **Phase 4B**: Enhanced Detection (backward compatible, feature-flagged)
3. **Phase 4C**: Streaming Transcription (graceful degradation)
4. **Phase 4D**: Coaching Engine (additive UI features)

All features behind feature flags for gradual rollout.

---

## Testing Strategy

| Component | Test Type | Coverage Target |
|-----------|-----------|-----------------|
| Extractors | Unit | 90%+ |
| Memory Store | Integration | 85%+ |
| Playbook Generator | Integration + Golden Tests | 80%+ |
| Tier 3 Detector | Unit + Benchmark | 95%+ accuracy |
| Story Recaller | Unit + Similarity Tests | 80%+ |
| Coaching | Unit + UI Integration | 75%+ |

---

## Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Extraction per document | < 10s | Timer in extraction pipeline |
| Profile generation | < 5s | Timer in profile generator |
| Playbook generation | < 30s | Timer in playbook assembler |
| Tier 3 detection | < 150ms P95 | Latency histogram |
| Story recall | < 1s | Timer from question detection |
| Interim transcript | < 500ms from speech | UI timestamp diff |

---

## Approval

- [ ] Technical Lead approval
- [ ] Ready for Implementation phase

**Approved by**: ___________________ **Date**: ___________
