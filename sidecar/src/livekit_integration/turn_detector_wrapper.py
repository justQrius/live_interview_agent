"""
Wrapper around LiveKit's turn detector for direct use in existing pipeline.

This allows using LiveKit's semantic turn detection without adopting the full
AgentSession framework initially.
"""

import asyncio
import logging
import time
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class LiveKitTurnDetector:
    """
    Wraps LiveKit's Qwen2.5 turn detector for use in existing pipeline.

    Usage:
        detector = LiveKitTurnDetector()
        await detector.initialize()
        is_finished, confidence = await detector.check(text, conversation_history)
        if is_finished:
            proceed_to_question_detection()
    """

    def __init__(self, model_name: str = "qwen2.5-0.5b-instruct", device: str = "cpu"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._loaded = False

    async def initialize(self):
        """
        Load turn detector model (lazy initialization).

        This is called lazily when first used to avoid blocking startup.
        """
        if self._loaded:
            return

        try:
            from livekit.plugins.turn_detector.multilingual import MultilingualModel

            logger.info(f"Loading LiveKit Turn Detector model ({self.model_name})...")
            self._model = MultilingualModel()
            self._loaded = True

            logger.info("LiveKit Turn Detector loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load LiveKit Turn Detector: {e}")
            raise

    async def check(
        self,
        text: str,
        conversation_history: List[dict],
        timeout: float = 3.0
    ) -> Tuple[bool, float]:
        """
        Check if speaker has finished their turn.

        Args:
            text: Latest transcript segment
            conversation_history: List of {'role', 'content'} dicts (last N turns)
            timeout: Max wait for inference (seconds)

        Returns:
            (is_finished, confidence): Whether turn is complete and confidence score (0.0-1.0)
        """
        start_time = time.time()
        error = None

        if not self._loaded:
            await self.initialize()

        try:
            # Build ChatContext-like structure
            messages = self._build_messages(text, conversation_history)

            # Call LiveKit's turn detection
            completion_probability = await asyncio.wait_for(
                self._model.predict_end_of_turn(messages),
                timeout=timeout
            )

            # Threshold based on confidence
            is_finished = completion_probability > 0.5

            logger.debug(
                f"Turn detection: {is_finished} (confidence: {completion_probability:.2f})"
            )

            # Record metrics
            try:
                from livekit_integration.livekit_metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_turn_detection(
                    latency_ms=(time.time() - start_time) * 1000,
                    confidence=completion_probability,
                    is_finished=is_finished,
                    text=text,
                    tier_used="livekit"
                )
            except ImportError:
                # Import failed (module not available), skip metrics
                pass
            except Exception as metrics_error:
                # Metrics recording failed, don't fail the turn detection
                logger.debug(f"Metrics recording failed: {metrics_error}")

            return is_finished, completion_probability

        except asyncio.TimeoutError:
            error = "timeout"
            logger.warning("Turn detection inference timed out, assuming finished")

            # Record timeout metric
            try:
                from livekit_integration.livekit_metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_turn_detection(
                    latency_ms=(time.time() - start_time) * 1000,
                    confidence=0.5,
                    is_finished=True,
                    text=text,
                    tier_used="livekit",
                    error=error
                )
            except (ImportError, Exception):
                pass

            return True, 0.5  # Safe default: finish

        except Exception as e:
            error = f"inference_error: {str(e)}"
            logger.error(f"Turn detection error: {e}")

            # Record error metric
            try:
                from livekit_integration.livekit_metrics import get_metrics_collector
                collector = get_metrics_collector()
                collector.record_turn_detection(
                    latency_ms=(time.time() - start_time) * 1000,
                    confidence=0.5,
                    is_finished=True,
                    text=text,
                    tier_used="livekit",
                    error=error
                )
            except (ImportError, Exception):
                pass

            return True, 0.5  # Safe default: finish

    def _build_messages(self, current_text: str, history: List[dict]) -> List[dict]:
        """
        Build message list for turn detector similar to ChatContext.

        Formats the conversation history and current text in the structure
        expected by LiveKit's turn detector model.
        """
        # Start with history (limit to last 6 turns as LiveKit does)
        messages = []

        for turn in history[-6:]:  # Last 6 turns
            if turn.get("role") in ["user", "assistant"] or turn.get("speaker") == "interviewer":
                content = turn.get("content", "") or turn.get("text", "")
                if content:  # Skip empty messages
                    messages.append({
                        "role": "user" if turn.get("speaker") == "interviewer" or turn.get("role") == "user" else "assistant",
                        "content": content.strip()
                    })

        # Add current text
        messages.append({
            "role": "user",
            "content": current_text.strip()
        })

        return messages

    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self._loaded


# Singleton instance for reuse
_detector_instance: Optional[LiveKitTurnDetector] = None

def get_turn_detector(
    model_name: str = "qwen2.5-0.5b-instruct",
    device: str = "cpu"
) -> LiveKitTurnDetector:
    """
    Get or create singleton turn detector instance.

    This ensures the model is only loaded once per application lifetime.

    Args:
        model_name: Model to use (default: qwen2.5-0.5b-instruct)
        device: Device to load on (cpu or cuda)

    Returns:
        LiveKitTurnDetector instance
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = LiveKitTurnDetector(model_name=model_name, device=device)
    return _detector_instance
