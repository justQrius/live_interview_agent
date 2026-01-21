"""
LiveKit Turn Detection Metrics Collector

Tracks and aggregates metrics for LiveKit turn detection performance:
- Latency (P50, P95, P99, min/max/avg)
- Accuracy (TP, FP, TN, FN, precision, recall, F1)
- Confidence score distribution
- Error rates
- Operational statistics

Thread-safe for async/await usage.
"""

import time
import threading
import json
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from statistics import mean, median
import logging

logger = logging.getLogger(__name__)


@dataclass
class TurnDetectionMetric:
    """Single turn detection event metric"""
    timestamp: float
    latency_ms: float
    confidence: float
    is_finished: bool
    text_preview: str  # First 100 chars
    text_length: int
    tier_used: Optional[str] = None  # "livekit", "accumulator", "timing"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "latency_ms": self.latency_ms,
            "confidence": self.confidence,
            "is_finished": self.is_finished,
            "text_preview": self.text_preview,
            "text_length": self.text_length,
            "tier_used": self.tier_used,
            "error": self.error
        }


@dataclass
class ConfidenceBucket:
    """Groups confidence scores into buckets for distribution analysis"""
    min_conf: float
    max_conf: float
    count: int
    avg_confidence: float


@dataclass
class ErrorStats:
    """Error statistics by error type"""
    timeout_count: int = 0
    inference_error_count: int = 0
    import_error_count: int = 0
    other_error_count: int = 0
    total_errors: int = 0

    def record_error(self, error_type: str):
        self.total_errors += 1
        if "timeout" in error_type.lower():
            self.timeout_count += 1
        elif "inference" in error_type.lower():
            self.inference_error_count += 1
        elif "import" in error_type.lower():
            self.import_error_count += 1
        else:
            self.other_error_count += 1


@dataclass
class AggregatedMetrics:
    """Aggregated metrics summary"""
    total_checks: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0

    # Accuracy metrics
    # True Positive: LiveKit said complete, and it actually was complete
    true_positive: int = 0
    # False Positive: LiveKit said complete, but should have continued
    false_positive: int = 0
    # True Negative: LiveKit said incomplete, and it actually was incomplete
    true_negative: int = 0
    # False Negative: LiveKit said incomplete, but should have been complete
    false_negative: int = 0

    # Confidence stats
    confidence_scores: List[float] = field(default_factory=list)

    # Error stats
    error_stats: ErrorStats = field(default_factory=ErrorStats)
    error_count: int = 0

    # Tier distribution
    tier_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def add_metric(self, metric: TurnDetectionMetric):
        """Add a single metric to aggregated stats"""
        self.total_checks += 1

        # Latency
        if metric.error is None:
            self.total_latency_ms += metric.latency_ms
            self.min_latency_ms = min(self.min_latency_ms, metric.latency_ms)
            self.max_latency_ms = max(self.max_latency_ms, metric.latency_ms)

        # Confidence
        if metric.error is None and 0 <= metric.confidence <= 1:
            self.confidence_scores.append(metric.confidence)

        # Errors
        if metric.error:
            self.error_count += 1
            self.error_stats.record_error(metric.error)

        # Tier distribution
        if metric.tier_used:
            self.tier_distribution[metric.tier_used] += 1

    def calculate_stats(self) -> Dict[str, Any]:
        """Calculate derived statistics"""
        if self.total_checks == 0:
            return self._empty_stats()

        # Latency stats
        avg_latency = self.total_latency_ms / max(1, self.total_checks - self.error_count)
        sorted_confidence = sorted(self.confidence_scores)
        n = len(sorted_confidence)

        # Percentiles
        p50 = sorted_confidence[n // 2] if n > 0 else 0.0
        p95 = sorted_confidence[int(n * 0.95)] if n > 0 else 0.0
        p99 = sorted_confidence[int(n * 0.99)] if n > 0 else 0.0

        # Accuracy metrics
        total_decisions = self.true_positive + self.false_positive + self.true_negative + self.false_negative
        accuracy = (self.true_positive + self.true_negative) / max(1, total_decisions)

        precision = self.true_positive / max(1, self.true_positive + self.false_positive)
        recall = self.true_positive / max(1, self.true_positive + self.false_negative)
        f1 = 2 * (precision * recall) / max(0.001, precision + recall)

        # Error rate
        error_rate = self.error_count / self.total_checks

        # Confidence buckets
        buckets = self._get_confidence_buckets()

        return {
            "total_checks": self.total_checks,
            "successful_checks": self.total_checks - self.error_count,
            "error_rate": error_rate,
            "error_count": self.error_count,
            "error_breakdown": asdict(self.error_stats),
            "latency": {
                "avg_ms": round(avg_latency, 2),
                "min_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float('inf') else 0,
                "max_ms": round(self.max_latency_ms, 2),
                "total_ms": round(self.total_latency_ms, 2)
            },
            "accuracy": {
                "true_positive": self.true_positive,
                "false_positive": self.false_positive,
                "true_negative": self.true_negative,
                "false_negative": self.false_negative,
                "accuracy": round(accuracy, 4),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4)
            },
            "confidence": {
                "avg": round(mean(self.confidence_scores), 4) if self.confidence_scores else 0,
                "p50": round(p50, 4),
                "p95": round(p95, 4),
                "p99": round(p99, 4),
                "buckets": buckets
            },
            "tier_distribution": dict(self.tier_distribution)
        }

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_checks": 0,
            "successful_checks": 0,
            "error_rate": 0,
            "error_count": 0,
            "error_breakdown": asdict(self.error_stats),
            "latency": {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "total_ms": 0},
            "accuracy": {
                "true_positive": 0, "false_positive": 0,
                "true_negative": 0, "false_negative": 0,
                "accuracy": 0, "precision": 0, "recall": 0, "f1_score": 0
            },
            "confidence": {"avg": 0, "p50": 0, "p95": 0, "p99": 0, "buckets": []},
            "tier_distribution": {}
        }

    def _get_confidence_buckets(self) -> List[Dict]:
        """Create 10 buckets for confidence distribution"""
        if not self.confidence_scores:
            return []

        buckets = []
        for i in range(10):
            min_c = i / 10
            max_c = (i + 1) / 10
            scores = [c for c in self.confidence_scores if min_c <= c < max_c]
            if scores:
                buckets.append({
                    "range": f"{min_c:.1f}-{max_c:.1f}",
                    "count": len(scores),
                    "avg_confidence": round(mean(scores), 4)
                })
        return buckets


class LiveKitMetricsCollector:
    """Singleton metrics collector for LiveKit turn detection"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        # All recorded metrics (in memory)
        self._metrics: List[TurnDetectionMetric] = []

        # Aggregated stats (updated incrementally)
        self._aggregated = AggregatedMetrics()

        # Thread safety
        self._metrics_lock = threading.Lock()

        # Start time for uptime calculation
        self._start_time = time.time()

        # Max metrics to keep in memory (Ring buffer-like)
        self._max_metrics = 10000

        logger.info("LiveKit Metrics Collector initialized")

    def record_turn_detection(
        self,
        latency_ms: float,
        confidence: float,
        is_finished: bool,
        text: str,
        tier_used: str = "livekit",
        error: Optional[str] = None
    ):
        """Record a single turn detection event

        Args:
            latency_ms: Detection latency in milliseconds
            confidence: Confidence score (0.0 - 1.0)
            is_finished: Whether turn was detected as complete
            text: Full text (will truncate for preview)
            tier_used: Which detection tier was used
            error: Error message if detection failed
        """
        metric = TurnDetectionMetric(
            timestamp=time.time(),
            latency_ms=latency_ms,
            confidence=confidence,
            is_finished=is_finished,
            text_preview=text[:100] + "..." if len(text) > 100 else text,
            text_length=len(text),
            tier_used=tier_used,
            error=error
        )

        with self._metrics_lock:
            # Add to history
            self._metrics.append(metric)

            # Update aggregates
            self._aggregated.add_metric(metric)

            # Prune old metrics if needed (ring buffer)
            if len(self._metrics) > self._max_metrics:
                self._metrics.pop(0)

        logger.debug(
            f"Recorded turn detection: latency={latency_ms:.1f}ms, "
            f"confidence={confidence:.2f}, finished={is_finished}, tier={tier_used}"
        )

    def record_accuracy(self, is_finished: bool, correct: bool):
        """Record accuracy outcome for evaluation

        Args:
            is_finished: What LiveKit predicted
            correct: Whether prediction was correct (requires manual labeling or benchmark)

        Note: This is optional. For full accuracy metrics, you need ground truth labels.
        """
        with self._metrics_lock:
            if is_finished and correct:
                self._aggregated.true_positive += 1
            elif is_finished and not correct:
                self._aggregated.false_positive += 1
            elif not is_finished and correct:
                self._aggregated.true_negative += 1
            elif not is_finished and not correct:
                self._aggregated.false_negative += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current aggregated statistics"""
        with self._metrics_lock:
            base_stats = self._aggregated.calculate_stats()
            base_stats["uptime_seconds"] = round(time.time() - self._start_time, 2)
            base_stats["metrics_in_memory"] = len(self._metrics)
            return base_stats

    def get_recent_metrics(self, count: int = 100) -> List[Dict[str, Any]]:
        """Get most recent metrics"""
        with self._metrics_lock:
            recent = self._metrics[-count:]
            return [m.to_dict() for m in recent]

    def export_json(self) -> str:
        """Export all metrics as JSON string"""
        with self._metrics_lock:
            output = {
                "export_time": datetime.now().isoformat(),
                "uptime_seconds": round(time.time() - self._start_time, 2),
                "total_metrics": len(self._metrics),
                "aggregated_stats": self._aggregated.calculate_stats(),
                "raw_metrics": [m.to_dict() for m in self._metrics]
            }
            return json.dumps(output, indent=2)

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format

        Returns:
            Prometheus-compatible metrics text
        """
        stats = self.get_stats()

        lines = [
            "# LiveKit Turn Detection Metrics",
            f"# Generated at {datetime.now().isoformat()}",
            "",
            "# Latency metrics"
        ]

        if stats["total_checks"] > 0:
            latency = stats["latency"]
            lines.extend([
                f"livekit_turn_detection_latency_avg_ms {latency['avg_ms']}",
                f"livekit_turn_detection_latency_min_ms {latency['min_ms']}",
                f"livekit_turn_detection_latency_max_ms {latency['max_ms']}",
            ])

        lines.extend([
            "",
            "# Accuracy metrics"
        ])

        acc = stats["accuracy"]
        lines.extend([
            f"livekit_turn_detection_true_positive {acc['true_positive']}",
            f"livekit_turn_detection_false_positive {acc['false_positive']}",
            f"livekit_turn_detection_true_negative {acc['true_negative']}",
            f"livekit_turn_detection_false_negative {acc['false_negative']}",
            f"livekit_turn_detection_accuracy {acc['accuracy']}",
            f"livekit_turn_detection_precision {acc['precision']}",
            f"livekit_turn_detection_recall {acc['recall']}",
            f"livekit_turn_detection_f1_score {acc['f1_score']}",
        ])

        lines.extend([
            "",
            "# Confidence metrics"
        ])

        conf = stats["confidence"]
        lines.extend([
            f"livekit_turn_detection_confidence_avg {conf['avg']}",
            f"livekit_turn_detection_confidence_p50 {conf['p50']}",
            f"livekit_turn_detection_confidence_p95 {conf['p95']}",
            f"livekit_turn_detection_confidence_p99 {conf['p99']}",
        ])

        lines.extend([
            "",
            "# Operational metrics"
        ])

        lines.extend([
            f"livekit_turn_detection_total_checks {stats['total_checks']}",
            f"livekit_turn_detection_successful_checks {stats['successful_checks']}",
            f"livekit_turn_detection_error_count {stats['error_count']}",
            f"livekit_turn_detection_error_rate {stats['error_rate']}",
            f"livekit_turn_detection_uptime_seconds {stats['uptime_seconds']}",
        ])

        return "\n".join(lines)

    def export_csv(self) -> str:
        """Export raw metrics as CSV string

        Returns:
            CSV-compatible string with header
        """
        with self._metrics_lock:
            if not self._metrics:
                return "timestamp,datetime,latency_ms,confidence,is_finished,text_preview,text_length,tier_used,error\n"

            header = "timestamp,datetime,latency_ms,confidence,is_finished,text_preview,text_length,tier_used,error\n"
            rows = []

            for m in self._metrics:
                row = (
                    f"{m.timestamp},"
                    f"{datetime.fromtimestamp(m.timestamp).isoformat()},"
                    f"{m.latency_ms},"
                    f"{m.confidence},"
                    f"{m.is_finished},"
                    f'"{m.text_preview.replace('"', '""')}",'  # Escape quotes
                    f"{m.text_length},"
                    f"{m.tier_used or ''},"
                    f'"{m.error or ""}"'
                )
                rows.append(row)

            return header + "\n".join(rows)

    def reset(self):
        """Reset all metrics (use with caution)"""
        with self._metrics_lock:
            self._metrics.clear()
            self._aggregated = AggregatedMetrics()
            self._start_time = time.time()
        logger.warning("LiveKit metrics collector reset")

    def get_health_check(self) -> Dict[str, Any]:
        """Get health check status

        Returns:
            Health status dictionary
        """
        stats = self.get_stats()

        # Determine health status
        if stats["total_checks"] == 0:
            status = "degraded"  # No checks yet
        elif stats["error_rate"] > 0.10:  # > 10%
            status = "unhealthy"
        elif stats["error_rate"] >= 0.05:  # >= 5%  (changed from > to >=)
            status = "warning"
        else:
            status = "healthy"

        return {
            "status": status,
            "uptime_seconds": stats["uptime_seconds"],
            "total_checks": stats["total_checks"],
            "error_rate": stats["error_rate"],
            "avg_latency_ms": stats["latency"]["avg_ms"],
            "last_check_time": datetime.fromtimestamp(
                self._metrics[-1].timestamp if self._metrics else self._start_time
            ).isoformat() if self._metrics else None
        }


def get_metrics_collector() -> LiveKitMetricsCollector:
    """Get singleton metrics collector instance"""
    return LiveKitMetricsCollector()
