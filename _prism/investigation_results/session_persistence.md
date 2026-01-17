# Session Persistence Analysis Findings

## Overview
Sessions in the Live Interview Agent are designed to be largely ephemeral in terms of conversation context and RAG documents, but persistent in terms of candidate intelligence (Profile, Stories, Claims).

## 1. What Starts Fresh? (Session-Scoped)
These components are **cleared** and reset every time a session ends or the app restarts:

*   **RAG Vector Store (`interview_context` collection)**:
    *   `_handle_stop_session` in `server.py` explicitly calls `self.vector_store.clear()`, which deletes the entire ChromaDB collection.
    *   This means all embeddings from uploaded documents (Resume, Job Description) are lost.
*   **Conversation Context (`context_manager`)**:
    *   `EnhancedContextManager` is in-memory only.
    *   `_handle_stop_session` calls `self.context_manager.clear_context()`, wiping all parsed chunks.
*   **Conversation History (`conversation_history`)**:
    *   The list of chat messages sent to the LLM is cleared on stop. The new session starts with an empty history.

## 2. What Persists? (Cross-Session)
These components are **stored permanently** in SQLite (`~/.live_interview_agent/memory.db`) and are reloaded:

*   **Candidate Profile**: The AI "remembers" who you are.
    *   Loaded in `_handle_start_session` via `self.memory_store.get_profile()`.
    *   Injected into the system prompt of the LLM.
*   **STAR Stories**: Your achievement stories are safe.
    *   Stored in the `stories` table.
    *   Reloaded into the `StoryRecaller` cache on startup.
*   **Session Logs**: History is saved but not "active".
    *   Stored in `sessions.db`.
    *   You can view past sessions in the UI, but the AI doesn't "remember" what was said in them during a new interview (unless explicitly designed to, which currently it isn't).

## 3. Why It Works This Way
This design appears intentional to prevent **context pollution**:
1.  **Privacy**: Different interviews might be for different companies. You don't want the AI confusing "Company A's values" with "Company B's job description" from yesterday.
2.  **Accuracy**: RAG is most effective when the search space is limited to relevant documents. Clearing the vector store ensures only the *current* interview's context is retrievable.
3.  **Cost**: Embeddings and vector storage (if using a cloud provider) cost money/resources. Clearing them keeps the footprint small.

## 4. Conclusion
The system **does start fresh** for documents and chat history by design. To reuse context (like a resume), the user must re-upload it, OR the system relies on the persistent **Candidate Profile** which is an extracted summary of the resume.
