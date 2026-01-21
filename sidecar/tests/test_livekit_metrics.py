"""
Tests for LiveKit Turn Detection Metrics Collector.

Tests:
- Metric recording
- Aggregated statistics calculation
- Percentile calculation
- Error tracking
- Health check
- Export formats (JSON, Prometheus, CSV)
- Thread safety
- Singleton behavior
"""

import pytest
import time
import json
from livekit_integration.livekit_metrics import (
    LiveKitMetricsCollector,
    get_metrics_collector,
    TurnDetectionMetric,
    ConfidenceBucket,
    ErrorStats,
    AggregatedMetrics
)


class TestTurnDetectionMetric:
    """Test TurnDetectionMetric dataclass"""

    def test_metric_creation(self):
        """Test creating a metric"""
        metric = TurnDetectionMetric(
            timestamp=time.time(),
            latency_ms=100.5,
            confidence=0.85,
            is_finished=True,
            text_preview="Tell me about Python",
            text_length=22,
            tier_used="livekit"
        )

        assert metric.latency_ms == 100.5
        assert metric.confidence == 0.85
        assert metric.is_finished is True
        assert metric.tier_used == "livekit"
        assert metric.error is None

    def test_metric_to_dict(self):
        """Test converting metric to dictionary"""
        timestamp = time.time()
        metric = TurnDetectionMetric(
            timestamp=timestamp,
            latency_ms=100.5,
            confidence=0.85,
            is_finished=True,
            text_preview="Tell me about Python",
            text_length=22,
            tier_used="livekit",
            error=None
        )

        result = metric.to_dict()

        assert result["timestamp"] == timestamp
        assert "datetime" in result
        assert result["latency_ms"] == 100.5
        assert result["confidence"] == 0.85
        assert result["is_finished"] is True
        assert result["text_preview"] == "Tell me about Python"
        assert result["text_length"] == 22
        assert result["tier_used"] == "livekit"
        assert result["error"] is None

    def test_metric_with_error(self):
        """Test metric with error"""
        metric = TurnDetectionMetric(
            timestamp=time.time(),
            latency_ms=5000.0,
            confidence=0.5,
            is_finished=True,
            text_preview="",
            text_length=0,
            tier_used="livekit",
            error="timeout"
        )

        assert metric.error == "timeout"


class TestErrorStats:
    """Test ErrorStats tracking"""

    def test_default_error_stats(self):
        """Test default error stats"""
        stats = ErrorStats()
        assert stats.total_errors == 0
        assert stats.timeout_count == 0
        assert stats.inference_error_count == 0
        assert stats.import_error_count == 0
        assert stats.other_error_count == 0

    def test_record_timeout_error(self):
        """Test recording timeout error"""
        stats = ErrorStats()
        stats.record_error("timeout")
        assert stats.total_errors == 1
        assert stats.timeout_count == 1
        assert stats.other_error_count == 0

    def test_record_inference_error(self):
        """Test recording inference error"""
        stats = ErrorStats()
        stats.record_error("inference_error: model failed")
        assert stats.total_errors == 1
        assert stats.inference_error_count == 1

    def test_record_import_error(self):
        """Test recording import error"""
        stats = ErrorStats()
        stats.record_error("import_error: module not found")
        assert stats.total_errors == 1
        assert stats.import_error_count == 1

    def test_record_other_error(self):
        """Test recording other error"""
        stats = ErrorStats()
        stats.record_error("unknown_error: something happened")
        assert stats.total_errors == 1
        assert stats.other_error_count == 1

    def test_multiple_errors(self):
        """Test recording multiple errors"""
        stats = ErrorStats()
        stats.record_error("timeout")
        stats.record_error("inference_error: failed")
        stats.record_error("timeout")
        stats.record_error("other error")

        assert stats.total_errors == 4
        assert stats.timeout_count == 2
        assert stats.inference_error_count == 1
        assert stats.other_error_count == 1


class TestAggregatedMetrics:
    """Test AggregatedMetrics calculation"""

    def test_default_aggregated_metrics(self):
        """Test default aggregated metrics"""
        agg = AggregatedMetrics()
        assert agg.total_checks == 0
        assert agg.true_positive == 0
        assert agg.false_positive == 0
        assert agg.total_latency_ms == 0.0
        assert len(agg.confidence_scores) == 0
        assert agg.min_latency_ms == float('inf')
        assert agg.max_latency_ms == 0.0

    def test_add_metric_success(self):
        """Test adding a successful metric"""
        agg = AggregatedMetrics()
        metric = TurnDetectionMetric(
            timestamp=time.time(),
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text_preview="Test",
            text_length=4,
            tier_used="livekit"
        )
        agg.add_metric(metric)

        assert agg.total_checks == 1
        assert agg.total_latency_ms == 100.0
        assert agg.min_latency_ms == 100.0
        assert agg.max_latency_ms == 100.0
        assert len(agg.confidence_scores) == 1
        assert agg.confidence_scores[0] == 0.85
        assert agg.error_count == 0

    def test_add_metric_with_error(self):
        """Test adding metric with error"""
        agg = AggregatedMetrics()
        metric = TurnDetectionMetric(
            timestamp=time.time(),
            latency_ms=0.0,
            confidence=0.0,
            is_finished=False,
            text_preview="",
            text_length=0,
            tier_used="livekit",
            error="timeout"
        )
        agg.add_metric(metric)

        assert agg.total_checks == 1
        assert agg.error_count == 1
        assert agg.error_stats.total_errors == 1

    def test_calculate_stats_empty(self):
        """Test calculating stats with no metrics"""
        agg = AggregatedMetrics()
        stats = agg.calculate_stats()

        assert stats["total_checks"] == 0
        assert stats["latency"]["avg_ms"] == 0
        assert stats["latency"]["min_ms"] == 0
        assert stats["latency"]["max_ms"] == 0
        assert stats["accuracy"]["accuracy"] == 0
        assert stats["confidence"]["avg"] == 0

    def test_calculate_stats_with_data(self):
        """Test calculating stats with metrics"""
        agg = AggregatedMetrics()

        # Add 5 metrics
        for i in range(5):
            metric = TurnDetectionMetric(
                timestamp=time.time(),
                latency_ms=100.0 + i * 50,  # 100, 150, 200, 250, 300
                confidence=0.5 + i * 0.1,  # 0.5, 0.6, 0.7, 0.8, 0.9
                is_finished=True,
                text_preview="Test",
                text_length=4,
                tier_used="livekit"
            )
            agg.add_metric(metric)

        stats = agg.calculate_stats()

        assert stats["total_checks"] == 5
        assert stats["latency"]["total_ms"] == 1000.0  # sum of 100,150,200,250,300
        assert stats["latency"]["avg_ms"] == 200.0  # 1000/5
        assert stats["latency"]["min_ms"] == 100.0
        assert stats["latency"]["max_ms"] == 300.0
        assert stats["confidence"]["avg"] == 0.7  # avg of 0.5,0.6,0.7,0.8,0.9

    def test_confidence_percentiles(self):
        """Test confidence percentile calculation"""
        agg = AggregatedMetrics()

        # Add metrics with known confidence scores
        confidences = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        for conf in confidences:
            metric = TurnDetectionMetric(
                timestamp=time.time(),
                latency_ms=100.0,
                confidence=conf,
                is_finished=True,
                text_preview="Test",
                text_length=4,
                tier_used="livekit"
            )
            agg.add_metric(metric)

        stats = agg.calculate_stats()

        assert stats["confidence"]["p50"] == 0.6  # median of 10 values
        assert stats["confidence"]["p95"] == 1.0
        assert stats["confidence"]["p99"] == 1.0


class TestLiveKitMetricsCollector:
    """Test LiveKitMetricsCollector singleton and methods"""

    def test_singleton_behavior(self):
        """Test that collector is a singleton"""
        collector1 = LiveKitMetricsCollector()
        collector2 = LiveKitMetricsCollector()
        assert collector1 is collector2

    def test_get_metrics_collector(self):
        """Test get_metrics_collector helper"""
        collector = get_metrics_collector()
        assert isinstance(collector, LiveKitMetricsCollector)

        # Should return same instance
        collector2 = get_metrics_collector()
        assert collector is collector2

    def test_record_turn_detection(self):
        """Test recording a turn detection"""
        collector = LiveKitMetricsCollector()
        collector.reset()  # Clear any existing metrics

        collector.record_turn_detection(
            latency_ms=100.5,
            confidence=0.85,
            is_finished=True,
            text="Tell me about Python",
            tier_used="livekit"
        )

        stats = collector.get_stats()
        assert stats["total_checks"] == 1
        assert stats["latency"]["avg_ms"] == 100.5
        assert stats["latency"]["min_ms"] == 100.5
        assert stats["latency"]["total_ms"] == 100.5

    def test_record_multiple_turn_detections(self):
        """Test recording multiple turn detections"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Record 10 metrics
        for i in range(10):
            collector.record_turn_detection(
                latency_ms=100.0 + i * 10,
                confidence=0.5 + i * 0.05,
                is_finished=i % 2 == 0,  # Alternate finished/not finished
                text=f"Question {i}",
                tier_used="livekit"
            )

        stats = collector.get_stats()
        assert stats["total_checks"] == 10
        assert stats["latency"]["avg_ms"] == 145.0  # Average of 100,110,...,190
        assert stats["latency"]["min_ms"] == 100.0
        assert stats["latency"]["max_ms"] == 190.0

    def test_record_turn_detection_with_error(self):
        """Test recording turn detection with error"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        collector.record_turn_detection(
            latency_ms=5000.0,
            confidence=0.0,
            is_finished=True,
            text="Test",
            tier_used="livekit",
            error="timeout"
        )

        stats = collector.get_stats()
        assert stats["total_checks"] == 1
        assert stats["error_count"] == 1
        assert stats["error_rate"] == 1.0

    def test_get_recent_metrics(self):
        """Test getting recent metrics"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Record 5 metrics
        for i in range(5):
            collector.record_turn_detection(
                latency_ms=100.0 + i,
                confidence=0.5,
                is_finished=True,
                text=f"Test {i}",
                tier_used="livekit"
            )

        recent = collector.get_recent_metrics(count=3)
        assert len(recent) == 3
        # Should get last 3 metrics
        assert recent[0]["text_preview"] == "Test 2"
        assert recent[1]["text_preview"] == "Test 3"
        assert recent[2]["text_preview"] == "Test 4"

    def test_export_json(self):
        """Test JSON export"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="livekit"
        )

        json_str = collector.export_json()
        data = json.loads(json_str)

        assert "export_time" in data
        assert "uptime_seconds" in data
        assert "total_metrics" in data
        assert "aggregated_stats" in data
        assert "raw_metrics" in data
        assert data["total_metrics"] == 1

        # Cleanup
        collector.reset()

    def test_export_prometheus(self):
        """Test Prometheus export"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="livekit"
        )

        prometheus = collector.export_prometheus()

        assert "# LiveKit Turn Detection Metrics" in prometheus
        assert "livekit_turn_detection_latency_avg_ms" in prometheus
        assert "livekit_turn_detection_total_checks" in prometheus
        assert "livekit_turn_detection_uptime_seconds" in prometheus

    def test_export_csv(self):
        """Test CSV export"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="livekit"
        )

        csv = collector.export_csv()
        lines = csv.split("\n")

        assert lines[0].startswith("timestamp,datetime,latency_ms")
        assert len(lines) == 2  # Header + 1 data line

        # Cleanup
        collector.reset()

    def test_reset(self):
        """Test resetting metrics"""
        collector = LiveKitMetricsCollector()
        # Ensure clean state from any previous tests
        collector.reset()

        # Add some metrics (1)
        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="livekit"
        )

        assert collector.get_stats()["total_checks"] == 1

        # Reset
        collector.reset()

        assert collector.get_stats()["total_checks"] == 0
        assert collector.get_stats()["uptime_seconds"] < 1.0

    def test_health_check_no_checks(self):
        """Test health check with no checks (degraded)"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        health = collector.get_health_check()

        assert health["status"] == "degraded"
        assert health["uptime_seconds"] < 1.0
        assert health["total_checks"] == 0

    def test_health_check_healthy(self):
        """Test healthy status"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Add checks with low error rate
        for i in range(10):
            collector.record_turn_detection(
                latency_ms=100.0 + i * 10,
                confidence=0.8,
                is_finished=True,
                text=f"Test {i}",
                tier_used="livekit"
            )

        health = collector.get_health_check()

        assert health["status"] == "healthy"
        assert health["total_checks"] == 10
        assert health["error_rate"] == 0.0
        assert health["avg_latency_ms"] > 0

    def test_health_check_unhealthy(self):
        """Test unhealthy status with high error rate"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Add checks with high error rate (>10%)
        for i in range(10):
            if i < 2:  # 2 errors = 20% error rate
                collector.record_turn_detection(
                    latency_ms=5000.0,
                    confidence=0.0,
                    is_finished=True,
                    text=f"Test {i}",
                    tier_used="livekit",
                    error="timeout"
                )
            else:
                collector.record_turn_detection(
                    latency_ms=100.0,
                    confidence=0.8,
                    is_finished=True,
                    text=f"Test {i}",
                    tier_used="livekit"
                )

        health = collector.get_health_check()

        assert health["status"] == "unhealthy"
        assert health["error_rate"] == 0.2  # 20%

    def test_health_check_warning(self):
        """Test warning status with moderate error rate"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Add checks with moderate error rate (5-10%)
        for i in range(20):
            if i == 0:  # 1 error = 5% error rate
                collector.record_turn_detection(
                    latency_ms=5000.0,
                    confidence=0.0,
                    is_finished=True,
                    text=f"Test {i}",
                    tier_used="livekit",
                    error="timeout"
                )
            else:
                collector.record_turn_detection(
                    latency_ms=100.0,
                    confidence=0.8,
                    is_finished=True,
                    text=f"Test {i}",
                    tier_used="livekit"
                )

        health = collector.get_health_check()

        assert health["status"] == "warning"
        assert health["error_rate"] == 0.05  # 5%

    def test_tier_distribution(self):
        """Test tier distribution tracking"""
        collector = LiveKitMetricsCollector()
        collector.reset()

        # Add metrics with different tiers
        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="livekit"
        )
        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="accumulator"
        )
        collector.record_turn_detection(
            latency_ms=100.0,
            confidence=0.85,
            is_finished=True,
            text="Test",
            tier_used="timing"
        )

        stats = collector.get_stats()
        assert stats["tier_distribution"]["livekit"] == 1
        assert stats["tier_distribution"]["accumulator"] == 1
        assert stats["tier_distribution"]["timing"] == 1
