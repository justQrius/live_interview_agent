"""
Manages LiveKit agent sessions for WebSocket connections.

Bridge between LiveKit AgentSession and the existing WebSocket infrastructure.

This provides the 'proper' LiveKit integration approach as an alternative to the
simpler wrapper approach (turn_detector_wrapper.py).
"""

import asyncio
import logging
from typing import Optional, Dict, Any

# LiveKit imports
try:
    from livekit.agents import AgentSession
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
    LIVEKIT_AGENTS_AVAILABLE = True
except ImportError:
    LIVEKIT_AGENTS_AVAILABLE = False
    AgentSession = None
    MultilingualModel = None

from .agent import create_interview_coach_agent

logger = logging.getLogger(__name__)


class LiveKitSessionManager:
    """
    Manages LiveKit agent lifecycle for Tauri frontend connections.

    This class bridges the gap between LiveKit's AgentSession framework and
    the existing WebSocket-based communication architecture.

    Usage:
        manager = LiveKitSessionManager()
        await manager.start()
        # ... process transcripts ...
        await manager.stop()

    Note: This provides an alternative integration path to the simpler
    turn_detector_wrapper.py approach. Both can coexist.
    """

    def __init__(self, config: Optional[Dict] = None, broadcast_callback=None):
        """
        Initialize the session manager.

        Args:
            config: Optional configuration dictionary with keys:
                - turn_detection_enabled: bool (default: True)
                - max_history_turns: int (default: 10)
                - inference_timeout: float (default: 3.0)
            broadcast_callback: Optional async callable for WebSocket broadcasting.
                                Signature: callback(message_json: str) -> None
        """

        if not LIVEKIT_AGENTS_AVAILABLE:
            raise ImportError(
                "livekit-agents package not installed. "
                "Install with: pip install livekit-agents>=1.3.0"
            )

        self.config = config or {}
        self.session: Optional[AgentSession] = None
        self.agent = None
        self._broadcast_callback = broadcast_callback
        self._is_running = False

        # Configuration
        self._turn_detection_enabled = self.config.get(
            'turn_detection_enabled', True
        )
        self._max_history_turns = self.config.get(
            'max_history_turns', 10
        )
        self._inference_timeout = self.config.get(
            'inference_timeout', 3.0
        )

        logger.info("LiveKit Session Manager initialized")

    async def start(self):
        """
        Start LiveKit session manager.

        Initializes the agent, turn detector, and AgentSession.
        """

        if self._is_running:
            logger.warning("Session manager already running")
            return

        logger.info("Starting LiveKit Session Manager...")

        try:
            # Create agent instance with broadcast callback
            self.agent = create_interview_coach_agent(
                broadcast_callback=self._broadcast_callback
            )

            # Configure turn detector if enabled
            # Note: For non-AgentSession deployments, we skip loading MultilingualModel
            # to avoid requiring a LiveKit job context. Turn detection will be handled
            # through the turn_detector_wrapper in handle_transcript().            turn_detector_model = None
            if self._turn_detection_enabled:
                logger.info("Turn detection enabled (using wrapper in handle_transcript)")
            else:
                logger.info("Turn detection disabled by config")

            # Create AgentSession
            # Note: In a real Room-based deployment, you would configure
            # this with actual room/connection details. For text-only local use,
            # we create a minimal session without turn_detection to avoid job context requirements.
            self.session = AgentSession(
                turn_detection=turn_detector_model,
                allow_interruptions=False,  # Text-only, no interruptions needed
            )

            self._is_running = True
            logger.info("LiveKit Session Manager started successfully")

        except Exception as e:
            logger.error(f"Failed to start session manager: {e}")
            raise

    async def handle_transcript(
        self,
        transcript: str,
        speaker: str = "user"
    ) -> None:
        """
        Handle incoming transcript from STT.

        This routes existing WebSocket transcription through LiveKit's
        turn detection and agent processing pipeline.

        Args:
            transcript: The transcribed text
            speaker: Speaker identifier (default: "user" for interviewer)

        Raises:
            RuntimeError: If session is not started
        """

        if not self._is_running or not self.session:
            raise RuntimeError(
                "Session not started. Call start() first."
            )

        if not transcript:
            logger.debug("Ignoring empty transcript")
            return

        logger.info(f"[Session Manager] [{speaker}] {transcript[:80]}...")

        try:
            # Convert to ChatMessage
            # Note: ChatMessage is from livekit.agents.llm module
            if not LIVEKIT_AGENTS_AVAILABLE:
                raise ImportError("livekit-agents not available")

            from livekit.agents.llm import ChatMessage

            # Determine role based on speaker
            # In this context, interviewer = "user", candidate = "assistant"
            role = "user" if speaker.lower() in ["interviewer", "user", "host"] else "assistant"

            message = ChatMessage(
                role=role,
                content=transcript
            )

            # In a proper AgentSession deployment with a room, the message
            # would be automatically routed through the turn detector. For local use,
            # we explicitly add it to the chat context.

            # Add to chat context
            self.session.chat_ctx.add_message(message)

            # For interviewer messages (user role), check if turn should trigger
            # agent processing. In a real WebSocket room, the turn detector
            # would automatically trigger on_user_turn_completed.

            if role == "user" and self._turn_detection_enabled:
                # In a proper implementation, LiveKit's turn detector would
                # automatically detect turn completion and call agent.on_user_turn_completed().
                # For this wrapper approach, we simulate that by directly calling it.

                # Check if user turn is complete using turn detector
                # (This would normally happen automatically in AgentSession)
                from .turn_detector_wrapper import get_turn_detector

                detector = get_turn_detector()

                # Build conversation history
                history = self._extract_chat_context_history()

                # Check if turn is complete
                is_finished, confidence = await detector.check(
                    text=transcript,
                    conversation_history=history[-self._max_history_turns:],
                    timeout=self._inference_timeout
                )

                if is_finished and confidence >= 0.5:
                    logger.info(
                        f"[Session Manager] Turn complete (confidence={confidence:.2f}), "
                        f"triggering agent processing"
                    )

                    # Trigger agent callback
                    await self.agent.on_user_turn_completed(
                        turn_ctx=self.session.chat_ctx,
                        new_message=message
                    )
                else:
                    logger.debug(
                        f"[Session Manager] Turn not complete (confidence={confidence:.2f}), "
                        f"waiting for more input"
                    )
            elif role == "user" and not self._turn_detection_enabled:
                # Turn detection disabled, treat as always complete
                logger.debug(
                    f"[Session Manager] Turn detection disabled, assuming complete"
                )
                await self.agent.on_user_turn_completed(
                    turn_ctx=self.session.chat_ctx,
                    new_message=message
                )
            else:
                # Assistant (candidate) message, just add to context
                logger.debug(f"[Session Manager] Assistant message added to context")

        except Exception as e:
            logger.error(f"[Session Manager] Error processing transcript: {e}", exc_info=True)
            raise

    def _extract_chat_context_history(self) -> list[dict]:
        """
        Extract conversation history from AgentSession's ChatContext.

        Converts to the format expected by the turn detector.
        """

        history = []

        for item in self.session.chat_ctx.items:
            if item.type == "message":
                role = item.role or "unknown"
                content = item.text_content() or ""

                if content:
                    history.append({
                        "role": role,
                        "content": content.strip()
                    })

        return history

    def get_conversation_history(self, limit: int = 10) -> list[dict]:
        """
        Get current conversation history from the session.

        Args:
            limit: Maximum number of recent turns to return

        Returns:
            List of conversation turn dictionaries
        """

        history = self._extract_chat_context_history()
        return history[-limit:] if limit else history

    def clear_conversation_history(self) -> None:
        """
        Clear the conversation history from the session.

        Useful for starting a new interview session.
        """

        if self.session:
            # Clear the chat context
            self.session.chat_ctx.clear()
            logger.info("Conversation history cleared")

    async def stop(self) -> None:
        """
        Stop session manager.

        Cleanup resources and shut down the session.
        """

        if not self._is_running:
            logger.warning("Session manager not running")
            return

        logger.info("Stopping LiveKit Session Manager...")

        try:
            # Cleanup session
            if self.session:
                # AgentSession would have cleanup methods in a real deployment
                # For now, just clear references
                self.session = None

            if self.agent:
                self.agent = None

            self._is_running = False

            logger.info("LiveKit Session Manager stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping session manager: {e}", exc_info=True)
            raise

    @property
    def is_running(self) -> bool:
        """
        Check if session manager is running.
        """

        return self._is_running

    @property
    def chat_context(self):
        """
        Get the chat context from the session.

        Returns:
            ChatContext object or None if session not running
        """

        if self.session:
            return self.session.chat_ctx
        return None


# Singleton instance
_session_manager_instance: Optional[LiveKitSessionManager] = None


def get_session_manager(
    config: Optional[Dict] = None,
    broadcast_callback=None
) -> LiveKitSessionManager:
    """
    Get or create singleton session manager.

    Args:
        config: Optional configuration dictionary
        broadcast_callback: Optional async callable for WebSocket broadcasting.

    Returns:
        LiveKitSessionManager instance

    Note: This provides a singleton pattern similar to get_turn_detector().
    The singleton can be reset by calling the instance's stop() method.
    """

    global _session_manager_instance

    if _session_manager_instance is None:
        _session_manager_instance = LiveKitSessionManager(
            config=config,
            broadcast_callback=broadcast_callback
        )
    elif config is not None:
        # Config provided but instance exists
        logger.warning(
            "Session manager already initialized with default config. "
            "Using existing instance."
        )
    elif broadcast_callback is not None and _session_manager_instance._broadcast_callback is None:
        # Update broadcast callback if it wasn't set before
        logger.info("Setting broadcast callback on existing session manager")
        _session_manager_instance._broadcast_callback = broadcast_callback

    return _session_manager_instance


def reset_session_manager() -> None:
    """
    Reset the singleton session manager.

    This allows creating a fresh instance if needed.
    """

    global _session_manager_instance
    _session_manager_instance = None
    logger.info("Session manager singleton reset")
