# STORY-012: Gemini LLM Integration

## Description
Implement the LLM generation layer using Google's Gemini 1.5 Flash model. This module will take the retrieved context from the RAG engine and the user's/interviewer's question to generate a helpful, concise answer. It must support streaming responses to ensure low latency in the UI.

## Acceptance Criteria
- [ ] `GeminiLLM` class initialized with API key
- [ ] `generate_answer(question, context)` method implemented
- [ ] Streaming support (yield chunks as they arrive)
- [ ] Prompt template includes system instructions and injected context
- [ ] Context injection handles empty context gracefully
- [ ] Error handling for API failures (rate limits, network issues)
- [ ] Unit tests for prompt construction and mocking API response

## Technical Implementation
- **File**: `sidecar/src/llm/gemini_llm.py`
- **Model**: `gemini-1.5-flash`
- **Library**: `google-generativeai`
- **Input**: `query: str`, `context_chunks: List[str]`
- **Output**: Generator/Iterator of string chunks

## Prompt Template
```text
You are an expert technical interview assistant. Your goal is to help the candidate answer the interviewer's question using the provided context.

Context:
{context_str}

Question:
{question}

Answer the question clearly and concisely based on the context provided. If the context is not relevant, answer based on your general knowledge but mention that the context didn't help. Keep the answer conversational but professional.
```
