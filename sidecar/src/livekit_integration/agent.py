"""
LiveKit Agent that hosts the existing question detection logic.

This is the 'proper' LiveKit integration approach using the AgentSession framework.
Note: The wrapper approach (turn_detector_wrapper.py) is also available for simpler integration.
"""

import logging
from typing import Dict, Any, Optional, List, TYPE_CHECKING

# LiveKit imports - these are from the livekit-agents package
# Note: These imports will only work if livekit-agents is installed
try:
    from livekit.agents import Agent, llm
    from livekit.plugins import turn_detector
    LIVEKIT_AGENTS_AVAILABLE = True
except ImportError:
    LIVEKIT_AGENTS_AVAILABLE = False
    Agent = None
    llm = None

# Type hints for when livekit-agents is available
if TYPE_CHECKING and LIVEKIT_AGENTS_AVAILABLE:
    from livekit.agents.llm import ChatContext, ChatMessage
else:
    # Use type hints with strings for compatibility
    ChatContext = 'ChatContext'  # type: ignore
    ChatMessage = 'ChatMessage'  # type: ignore

# Your existing components (Phase 10 metrics)
try:
    from src.classification.question_detector import QuestionDetector
    from src.classification.query_reformulator import QueryReformulator
    from src.classification.question_splitter import QuestionSplitter
    from src.rag.enhanced_engine import EnhancedRAGEngine

    EXISTING_COMPONENTS_AVAILABLE = True
except ImportError:
    EXISTING_COMPONENTS_AVAILABLE = False
    QuestionDetector = None
    QueryReformulator = None
    QuestionSplitter = None
    EnhancedRAGEngine = None

logger = logging.getLogger(__name__)


class LiveKitInterviewCoachAgent:
    """
    LiveKit interview coach agent.

    Wraps the existing question detection pipeline in the LiveKit agent framework.
    This provides the 'proper' LiveKit integration approach as an alternative to the
    simpler wrapper approach (turn_detector_wrapper.py).
    """

    def __init__(self, broadcast_callback=None, vector_store=None, context_manager=None):
        if not LIVEKIT_AGENTS_AVAILABLE:
            raise ImportError(
                "livekit-agents package not installed. "
                "Install with: pip install livekit-agents>=1.3.0"
            )

        if not EXISTING_COMPONENTS_AVAILABLE:
            raise ImportError(
                "Existing components not available. "
                "Ensure sidecar/src is in Python path and components are accessible."
            )

        # Broadcast callback for WebSocket communication
        self._broadcast_callback = broadcast_callback

        # Initialize Agent base class with instructions
        self._agent = Agent(
            instructions="""
            You are an interview coach assistant that detects interview questions
            and provides helpful, STAR-formatted answers from the candidate's
            experience documents.
            """
        )

        # Your existing components
        self.question_detector = QuestionDetector()
        self.query_reformulator = QueryReformulator()
        self.question_splitter = QuestionSplitter()
        rag_engine = None

        # Initialize EnhancedRAGEngine if dependencies are provided
        if vector_store is not None and EXISTING_COMPONENTS_AVAILABLE:
            try:
                rag_engine = EnhancedRAGEngine(
                    vector_store,
                    context_manager=context_manager
                )
                logger.info("[Agent] EnhancedRAGEngine initialized successfully")
            except Exception as e:
                logger.warning(f"[Agent] Could not initialize RAG engine: {e}")
        elif vector_store is None:
            logger.info("[Agent] RAG engine not available - running without contextual retrieval")
        else:
            logger.warning("[Agent] VectorStore provided but EnhancedRAGEngine not available")

        self.rag_engine = rag_engine

        logger.info("LiveKit Interview Coach Agent initialized")

    def set_rag_dependencies(self, vector_store=None, context_manager=None) -> None:
        """
        Set or update RAG dependencies after agent initialization.

        This allows updating the RAG engine lazily after it becomes available,
        following the same pattern as set_llm_provider, set_cached_content, etc.

        Args:
            vector_store: Optional VectorStore instance for RAG retrieval.
            context_manager: Optional context manager for RAG expansion.
        """
        if vector_store is not None and EXISTING_COMPONENTS_AVAILABLE:
            try:
                # Create new RAG engine with updated dependencies
                self.rag_engine = EnhancedRAGEngine(
                    vector_store,
                    context_manager=context_manager
                )
                logger.info("[Agent] RAG dependencies updated successfully")
            except Exception as e:
                logger.warning(f"[Agent] Failed to update RAG dependencies: {e}", exc_info=True)
        else:
            logger.debug("[Agent] RAG dependencies unchanged (vector_store=None)")

        logger.info("[Agent] RAG engine type after update: " + 
                   (type(self.rag_engine).__name__ if self.rag_engine else "None"))

    async def on_user_turn_completed(
        self,
        turn_ctx: 'ChatContext',
        new_message: 'ChatMessage'
    ) -> None:
        """
        Called by LiveKit when turn is detected complete.

        This replaces the `utterance_accumulator.completed()` flow
        with the AgentSession framework's callback approach.
        """

        user_text = new_message.text_content()
        logger.info(f"[Agent] Turn completed: {user_text[:80]}...")

        # Extract conversation history from ChatContext
        conversation_history = self._extract_conversation_history(turn_ctx)

        # Your existing question detection (NOW WITH FULL CONTEXT!)
        question = self.question_detector.detect(
            text=user_text,
            conversation_history=conversation_history
        )

        logger.info(
            f"[Agent] Question detected: {question.get('type')} "
            f"(confidence: {question.get('confidence', 0):.2f})"
        )

        # Check if this is an actionable question
        is_actionable = question.get('is_actionable_question', False)
        if not is_actionable:
            logger.debug("[Agent] Not an interview question, skipping")
            return

        # Process question through existing pipeline
        await self._process_interview_question(
            user_text,
            question,
            conversation_history
        )

    async def _process_interview_question(
        self,
        question_text: str,
        question: Dict[str, Any],
        conversation_history: List[Dict]
    ):
        """
        Process interview question through existing RAG+LLM pipeline.
        """

        question_type = question.get('type', 'general')

        # Step 1: Reformulate follow-ups
        if question_type in ['follow_up', 'clarification']:
            reformulated = await self._reformulate_query(
                question_text,
                conversation_history
            )
        else:
            reformulated = question_text

        # Step 2: Split compound questions
        subquestions = self.question_splitter.split(reformulated)

        logger.info(f"[Agent] Reformulated: {reformulated[:80]}...")
        logger.info(f"[Agent] Subquestions: {subquestions}")

        # Step 3: RAG retrieval (if engine available)
        if self.rag_engine:
            context = await self._retrieve_context(subquestions)
        else:
            logger.warning("[Agent] RAG engine not available, skipping context retrieval")
            context = []

        # Step 4: Prepare answer prompt
        prompt = self._build_answer_prompt(reformulated, context)

        # Step 5: Send to frontend (would be done via WebSocket in real implementation)
        answer = self._generate_answer(prompt, context)

        # Step 6: Send to frontend
        await self._send_to_frontend({
            "type": "answer",
            "question": question_text,
            "reformulated": reformulated,
            "answer": answer,
            "question_type": question_type,
            "subquestions": subquestions
        })

    def _extract_conversation_history(
        self,
        turn_ctx: 'ChatContext'
    ) -> List[Dict]:
        """
        Extract conversation history from LiveKit ChatContext.

        Converts LiveKit's ChatContext format to the format expected by
        the existing QuestionDetector.
        """

        history = []

        for item in turn_ctx.items:
            if item.type == "message":
                # LiveKit uses 'role' (user/assistant/system)
                role = item.role
                content = item.text_content() or ""

                if content:  # Skip empty messages
                    history.append({
                        "role": role,
                        "content": content.strip()
                    })

        return history

    async def _reformulate_query(
        self,
        question_text: str,
        history: List[Dict]
    ) -> str:
        """
        Reformulate follow-up questions using the existing query reformulator.
        """

        try:
            # Extract topic stack from history
            topic_stack = self._extract_topic_stack(history)

            # Use existing reformulator
            reformulated = self.query_reformulator.reformulate(
                current_question=question_text,
                topic_stack=topic_stack
            )

            return reformulated

        except Exception as e:
            logger.warning(f"Query reformulation failed: {e}, using original")
            return question_text

    def _extract_topic_stack(self, history: List[Dict]) -> List[str]:
        """
        Extract topics from conversation history for reformulation.

        Simple keyword extraction from previous turns.
        """

        topics = []

        for turn in history[-5:]:  # Last 5 turns
            content = turn.get("content", "")
            if len(content) > 50:  # Only substantial turns
                words = content.split()
                # Extract first 5 words as topic indicators
                topics.extend(words[:5])

        return topics

    async def _retrieve_context(
        self,
        subquestions: List[str]
    ) -> List[str]:
        """
        Retrieve context from RAG engine.
        """

        chunks = []

        try:
            # Use EnhancedRAGEngine for multi-question retrieval
            results = await self.rag_engine.retrieve_multi_async(
                subquestions,
                max_chunks_per_query=3
            )

            # Extract chunk texts
            for result in results:
                chunks.append(result.text)

            logger.info(f"[Agent] Retrieved {len(chunks)} context chunks")

        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")

        return chunks

    def _build_answer_prompt(
        self,
        question: str,
        context: List[str]
    ) -> str:
        """
        Build prompt for LLM answer generation.
        """

        context_text = "\n\n".join(context) if context else "No specific context available."

        return f"""
Context from candidate's documents:
{context_text}

Interview question: {question}

Provide a helpful, STAR-formatted answer from the candidate's perspective.
Focus on specific examples and outcomes.
Be concise but detailed.

Structure your response with:
1. Situation (brief context)
2. Task (what you needed to do)
3. Action (what you did, specific examples)
4. Result (quantified outcomes if available)
"""

    def _generate_answer(
        self,
        prompt: str,
        context: List[str]
    ) -> str:
        """
        Generate answer from prompt.

        Note: In a real implementation, this would use the LLM provider
        (OpenAI, Anthropic, Gemini, etc.). For now, returns a simulated answer.
        """

        # In real implementation, call LLM provider:
        # answer = await self.llm_provider.generate(prompt, max_tokens=500)

        # Simulated answer for testing
        answer = (
            "Based on my experience, I worked on several projects involving "
            "the skills mentioned. For example, in my previous role, I implemented "
            "a similar feature that improved performance by 40%. I used Python and "
            "SQL, working in a team of 5 engineers. The project was delivered on time "
            "and received positive feedback from stakeholders."
        )

        return answer

    async def _send_to_frontend(self, message: Dict[str, Any]):
        """
        Send message to Tauri frontend via WebSocket.

        Uses the broadcast callback provided by the session manager to send
        messages to connected WebSocket clients.
        """

        if self._broadcast_callback:
            try:
                # Convert message dict to JSON string and broadcast
                import json
                message_json = json.dumps(message)
                await self._broadcast_callback(message_json)
                logger.info(
                    f"[Agent] Sent to frontend: {message['type']}"
                    f" (question: {message.get('question', '')[:50]}...)"
                )
            except Exception as e:
                logger.error(f"[Agent] Failed to send to frontend: {e}")
        else:
            logger.warning(
                f"[Agent] Broadcast callback not set. Message was: {message['type']}"
            )


# Agent factory function
def create_interview_coach_agent(
    broadcast_callback=None,
    vector_store=None,
    context_manager=None
) -> LiveKitInterviewCoachAgent:
    """
    Factory function to create agent instance.

    Args:
        broadcast_callback: Optional async callable for WebSocket broadcasting.
                          Signature: callback(message_json: str) -> None
        vector_store: Optional VectorStore instance for RAG retrieval.
        context_manager: Optional context manager for RAG expansion.

    Returns:
        Initialized LiveKitInterviewCoachAgent instance
    """

    return LiveKitInterviewCoachAgent(
        broadcast_callback=broadcast_callback,
        vector_store=vector_store,
        context_manager=context_manager
    )
