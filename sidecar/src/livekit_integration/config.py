"""
LiveKit Turn Detection Configuration.

Configuration for LiveKit semantic endpointing integration.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class LiveKitConfig:
    """
    Configuration for LiveKit Turn Detection integration.

    Loads settings from environment variables or uses sensible defaults.
    """

    # Turn Detector Settings
    turn_detector_model: str = "qwen2.5-0.5b-instruct"  # Default multilingual
    turn_detector_timeout: float = 3.0  # Max wait for turn detection (seconds)
    turn_device: str = "cpu"  # cpu or cuda (not required for 0.5b model)

    # Session Settings
    max_conversation_history: int = 10  # Number of turns to keep in context
    min_silence_duration: float = 0.5  # Min silence before turn detection (seconds)
    false_interruption_timeout: float = 2.0  # Wait before resuming speech (not used in text-only)

    # Question Detection Settings
    question_confidence_threshold: float = 0.6  # Min confidence for actionable question
    enable_tier3_llm_fallback: bool = True  # Use LLM for ambiguous cases

    # Feature Flags
    livekit_turn_detection_enabled: bool = True  # Enable/disable without code change

    # WebSocket Settings (for Tauri integration - not strictly required for text-only)
    ws_host: str = "localhost"
    ws_port: int = 8765

    @classmethod
    def from_env(cls) -> "LiveKitConfig":
        """
        Load configuration from environment variables.

        Usage:
            config = LiveKitConfig.from_env()
        """
        return cls(
            turn_detector_model=os.getenv(
                "LIVEKIT_TURN_MODEL",
                "qwen2.5-0.5b-instruct"
            ),
            turn_detector_timeout=float(os.getenv(
                "LIVEKIT_TURN_TIMEOUT",
                "3.0"
            )),
            turn_device=os.getenv(
                "LIVEKIT_DEVICE",
                "cpu"
            ),
            max_conversation_history=int(os.getenv(
                "LIVEKIT_MAX_HISTORY",
                "10"
            )),
            livekit_turn_detection_enabled=os.getenv(
                "LIVEKIT_TURN_DETECTION_ENABLED",
                "true"
            ).lower() == "true",
            question_confidence_threshold=float(os.getenv(
                "QUESTION_CONFIDENCE_THRESHOLD",
                "0.6"
            )),
            enable_tier3_llm_fallback=os.getenv(
                "QUESTION_LLM_FALLBACK",
                "true"
            ).lower() == "true",
        )
