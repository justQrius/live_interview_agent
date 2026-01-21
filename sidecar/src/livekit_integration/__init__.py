"""
LiveKit Turn Detection Integration Module.

Provides semantic endpointing capabilities to replace timing-based completeness detection.

Available Integration Paths:
1. Wrapper Approach (turn_detector_wrapper) - Simple, minimal changes
2. AgentSession Approach (agent, session_manager) - Full LiveKit framework
"""

from .config import LiveKitConfig
from .turn_detector_wrapper import LiveKitTurnDetector, get_turn_detector

# Phase 2: AgentSession framework (proper LiveKit integration)
from .agent import LiveKitInterviewCoachAgent, create_interview_coach_agent
from .session_manager import (
    LiveKitSessionManager,
    get_session_manager,
    reset_session_manager
)

# Phase 10: Metrics & Monitoring
from .livekit_metrics import (
    LiveKitMetricsCollector,
    get_metrics_collector,
    TurnDetectionMetric,
    ConfidenceBucket,
    ErrorStats,
    AggregatedMetrics
)

__all__ = [
    # Phase 1: Wrapper Approach
    "LiveKitConfig",
    "LiveKitTurnDetector",
    "get_turn_detector",
    # Phase 2: AgentSession Approach
    "LiveKitInterviewCoachAgent",
    "create_interview_coach_agent",
    "LiveKitSessionManager",
    "get_session_manager",
    "reset_session_manager",
    # Phase 10: Metrics & Monitoring
    "LiveKitMetricsCollector",
    "get_metrics_collector",
    "TurnDetectionMetric",
    "ConfidenceBucket",
    "ErrorStats",
    "AggregatedMetrics",
]
