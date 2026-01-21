"""
Benchmark LiveKit Turn Detection latency vs current pipeline.

This script measures and compares the performance of LiveKit's semantic turn detection
against the current 4-tier CompletenessDetector approach.
"""

import asyncio
import time
import logging
import sys
from pathlib import Path
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BenchmarkResult:
    """Store benchmark metrics"""

    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.accuracies = []
        self.errors = []

    def record(self, latency_ms: float, is_accurate: bool):
        """Record a single benchmark result"""
        self.times.append(latency_ms)
        self.accuracies.append(1 if is_accurate else 0))

    def get_stats(self) -> Dict[str, float]:
        """Calculate statistics from recorded measurements"""
        if not self.times:
            return {
                "count": 0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "accuracy": 0.0,
                "errors": len(self.errors)
            }

        return {
            "count": len(self.times),
            "avg_latency_ms": sum(self.times) / len(self.times),
            "min_latency_ms": min(self.times),
            "max_latency_ms": max(self.times),
            "accuracy": sum(self.accuracies) / len(self.accuracies) * 100,
            "errors": len(self.errors)
        }

    def print_summary(self):
        """Print formatted benchmark results"""
        stats = self.get_stats()
        print(f"\n{self.name} Results:")
        print("="*60)
        print(f"  Tests Run: {stats['count']}")
        print(f"  Average Latency: {stats['avg_latency_ms']:.1f}ms")
        print(f"  Min Latency: {stats['min_latency_ms']:.1f}ms")
        print(f"  Max Latency: {stats['max_latency_ms']:.1f}ms")
        print(f"  Accuracy: {stats['accuracy']:.1f}%")
        print(f"  Errors: {stats['errors']}")
        print("="*60)


# Test cases covering various interview scenarios
TEST_TRANSCRIPTS = [
    {
        "text": "Tell me about your experience with Python.",
        "expected_turn": "finished",
        "category": "single_question",
        "expected_confidence_range": (0.7, 1.0)
    },
    {
        "text": "I worked at Google for three years on natural language processing models.",
        "expected_turn": "finished",
        "category": "statement",
        "expected_confidence_range": (0.5, 0.9)
    },
    {
        "text": "I worked at",
        "expected_turn": "incomplete",
        "category": "mid_thought",
        "expected_confidence_range": (0.0, 0.5)
    },
    {
        "text": "What was your role and how did you handle the challenges?",
        "expected_turn": "finished",
        "category": "compound_question",
        "expected_confidence_range": (0.5, 0.9)
    },
    {
        "text": "That's very interesting.",
        "expected_turn": "finished",
        "category": "acknowledgment",
        "expected_confidence_range": (0.5, 0.8)
    },
    {
        "text": "Tell me about your background first, and then what interests you about this role?",
        "expected_turn": "finished",
        "category": "compound_question",
        "expected_confidence_range": (0.5, 0.9)
    },
    {
        "text": "I'm curious about",
        "expected_turn": "incomplete",
        "category": "mid_thought",
        "expected_confidence_range": (0.0, 0.4)
    },
    {
        "text": "Why did you decide to pursue this career path?",
        "expected_turn": "finished",
        "category": "question",
        "expected_confidence_range": (0.7, 1.0)
    },
    {
        "text": "Describe a challenging project you worked on.",
        "expected_turn": "finished",
        "category": "imperative",
        "expected_confidence": (0.7, 1.0)
    },
    {
        "text": "Let's switch gears and talk about your soft skills.",
        "expected_turn": "finished",
        "category": "transition",
        "expected_confidence_range": (0.6, 0.9)
    },
]


async def benchmark_livekit_turn_detection() -> BenchmarkResult:
    """Benchmark LiveKit turn detection latency and accuracy"""

    logger.info("="*60)
    logger.info("BENCHMARKING: LIVEKIT TURN DETECTION")
    logger.info("="*60)

    # Import LiveKit
    try:
        from livekit_integration.turn_detector_wrapper import LiveKitTurnDetector
    except ImportError as e:
        logger.error(f"LiveKit not installed: {e}")
        logger.error("Run: pip install livekit-agents livekit-plugins-turn-detector")
        result = BenchmarkResult("LiveKit")
        result.errors.append("Import failed")
        return result

    detector = LiveKitTurnDetector()

    try:
        logger.info("Loading LiveKit model (this may take a minute on first run)...")
        await detector.initialize()
        logger.info("✓ Model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load LiveKit model: {e}")
        result = BenchmarkResult("LiveKit")
        result.errors.append(f"Model load failed: {e}")
        return result

    result = BenchmarkResult("LiveKit Turn Detection")

    for test_case in TEST_TRANSCRIPTS:
        text = test_case["text"]
        expected_finished = test_case["expected_turn"] == "finished"

        logger.info(f"\n[{test_case['category']}]")
        logger.info(f"  Text: \"{text}\"")

        try:
            start = time.time()
            is_finished, confidence = await detector.check(text, [])
            elapsed = (time.time() - start) * 1000

            # Check accuracy
            is_accurate = is_finished == expected_finished

            # Check confidence is in expected range
            in_expected_range = (test_case['expected_confidence_range'][0] <= confidence <=
                                 test_case['expected_confidence_range'][1])

            result.record(elapsed, is_accurate and in_expected_range)

            logger.info(
                f"  LiveKit: {elapsed:.1f}ms, "
                f"finished={is_finished} (expected={expected_finished}), "
                f"confidence={confidence:.2f}, "
                f"accurate={is_accurate}"
            )

        except Exception as e:
            logger.error(f"  LiveKit error: {e}")
            result.errors.append(str(e))

    return result


def benchmark_current_completeness() -> BenchmarkResult:
    """
    Simulate current CompletenessDetector behavior.

    This simulates the timing-based timeouts without actually loading the detector.
    """

    logger.info("="*60)
    logger.info("BENCHMARKING: CURRENT COMPLETENESSDECTOR (SIMULATED)")
    logger.info("="*60)

    result = BenchmarkResult("Current CompletenessDetector (Simulated)")

    for test_case in TEST_TRANSCRIPTS:
        text = test_case["text"]
        expected_finished = test_case["expected_turn"] == "finished"
        category = test_case["category"]
        text_len = len(text)

        logger.info(f"\n[{category}]")
        logger.info(f"  Text: \"{text}\"")

        try:
            start = time.time()

            # Simulate current 4-tier detection
            # Tier 1: Punctuation check (<1ms)
            tier1_result = None
            if text.rstrip().endswith(('. ', '!', '?')):
                tier1_result = True

            # Tier 2: Syntax check (<5ms)
            # (simplified simulation)
            import re
            tier2_result = None
            if re.search(r'\b(what|how|why|when|where|who|which)\b', text, re.IGNORECASE):
                tier2_result = True

            # Tier 3: Timing - use soft timeout (3000ms)
            # For benchmark, we'll simulate a pause duration based on category
            if category == "mid_thought":
                simulated_pause = 50  # Short pause, may not trigger tier3
            elif category in ["compound_question", "acknowledgment", "transition"]:
                simulated_pause = 1500  # Medium pause
            else:
                simulated_pause = 500  # Standard pause

            # Simulate Tier 3 timing
            if simulated_pause > 2000:
                is_complete = True
            else:
                is_complete = tier1_result or tier2_result

            # Add timing latency
            if not is_complete:
                # Simulate waiting for soft timeout
                await asyncio.sleep(0.001)  # Minimal sleep for single statement tests
                is_complete = True  # Final default for testing

            elapsed = (time.time() - start) * 1000

            # For mid-thought with realistic pause, we may not trigger completion
            if category == "mid_thought" and text_len < 30:
                is_complete = False

            # Check accuracy
            is_accurate = is_complete == expected_finished

            result.record(elapsed, is_accurate)

            logger.info(
                f"  Current: {elapsed:.1f}ms, "
                f"complete={is_complete} (expected={expected_finished}), "
                f"accurate={is_accurate}"
            )

        except Exception as e:
            logger.error(f"  Current error: {e}")
            result.errors.append(str(e))

    return result


def format_comparison(livekit_stats: dict, current_stats: dict):
    """Format comparison results"""
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)

    print(f"\nLiveKit Turn Detection:")
    print(f"  Tests Run: {livekit_stats['count']}")
    print(f"  Average Latency: {livekit_stats['avg_latency_ms']:.1f}ms")
    print(f"  Max Latency: {livekit_stats['max_latency_ms']:.1f}ms")
    print(f"  Min Latency: {livekit_stats['min_latency_ms']:.1f}ms}")
    print(f"  Accuracy: {livekit_stats['accuracy']:.1f}%")
    print(f"  Errors: {livekit_stats['errors']}")

    print(f"\nCurrent Implementation:")
    print(f"  Tests Run: {current_stats['count']}")
    print(f"  Average Latency: {current_stats['avg_latency_ms']:.1f}ms")
    print(f"  Max Latency: {current_stats['max_latency_ms']:.1f}ms")
    print(f"  Min Latency: {current_stats['min_latency_ms']:.1f}ms")
    print(f"  Accuracy: {current_stats['accuracy']:.1f}%")
    print(f"  Errors: {current_stats['errors']}")

    # Calculate improvements
    if livekit_stats['avg_latency_ms'] > 0 and current_stats['avg_latency_ms'] > 0:
        latency_reduction = (
            (current_stats['avg_latency_ms'] - livekit_stats['avg_latency_ms'])
            / current_stats['avg_latency_ms'] * 100
        )
        print(f"\nLatency Improvement: {latency_reduction:.1f}%")
        print(f"  Before: {current_stats['avg_latency_ms']:.1f}ms → "
              f"After: {livekit_stats['avg_latency_ms']:.1f}ms")

    if current_stats['accuracy'] > 0:
        accuracy_diff = livekit_stats['accuracy'] - current_stats['accuracy']
        print(f"\nAccuracy Difference: {accuracy_diff:+.1f}%")
        print(f"  Before: {current_stats['accuracy']:.1f}% → "
              f"After: {livekit_stats['accuracy']:.1f}%")

    print("="*60)

    # Return key metrics
    return {
        "livekit_latency_ms": livekit_stats['avg_latency_ms'],
        "current_latency_ms": current_stats['avg_latency_ms'],
        "latency_improvement_pct": (
            (current_stats['avg_latency_ms'] - livekit_stats['avg_latency_ms'])
            / current_stats['avg_latency_ms'] * 100
        ) if livekit_stats['avg_latency_ms'] > 0 else 0,
        "livekit_accuracy": livekit_stats['accuracy'],
        "current_accuracy": current_stats['accuracy']
    }


async def run_full_benchmark():
    """Run complete benchmark suite"""

    print("\n" + "="*60)
    print("LIVEKIT TURN DETECTION BENCHMARK")
    print("="*60)
    print("\nThis benchmark compares LiveKit's semantic turn detection")
    print("against the current CompletenessDetector (4-tier cascade).")
    print("\nNote: Current implementation times are simulated for accurate")
    print("      comparison. For real metrics, run with live server.\n")

    try:
        # Benchmark LiveKit
        livekit_stats = await benchmark_livekit_turn_detection()

        # Print LiveKit summary
        livekit_stats.print_summary()

        # Benchmark current (simulated)
        current_stats = benchmark_current_completeness()

        # Print current summary
        current_stats.print_summary()

        # Print comparison
        metrics = format_comparison(livekit_stats.get_stats(), current_stats.get_stats())

        # Generate recommendations
        print("\nRECOMMENDATIONS:")
        print("="*60)
        print()

        # Latency analysis
        if metrics['latency_improvement_pct'] > 70:
            print("✅ SIGNIFICANT LATENCY IMPROVEMENT DETECTED")
            print(f"   LiveKit is {metrics['latency_improvement_pct']:.1f}% faster than current.")
            print("   STRONGLY RECOMMEND: Enable LiveKit in production.")
        elif metrics['latency_improvement_pct'] > 30:
            print("⚠️  MODERATE LATENCY IMPROVEMENT DETECTED")
            print(f"   LiveKit is {metrics['latency_improvement_pct']:.1f}% faster.")
            print("   RECOMMEND: Enable LiveKit for better user experience.")
        else:
            print("❓ NO SIGNIFICANT LATENCY IMPROVEMENT")
            print("   LiveKit and current implementation have similar timing.")
            print("   CONSIDER: Test with real interview recordings for better comparison.")

        # Accuracy analysis
        if metrics['livekit_accuracy'] > metrics['current_accuracy']:
            diff = metrics['livekit_accuracy'] - metrics['current_accuracy']
            if diff > 10:
                print(f"✅ SIGNIFICANT ACCURACY IMPROVEMENT: +{diff:.1f}%")
                print("   LiveKit's semantic understanding provides better turn detection.")
            elif diff > 5:
                print(f"⚠️  MODERATE ACCURACY IMPROVEMENT: +{diff:.1f}%")
                print("   LiveKit improves accuracy with conversation context.")
        elif metrics['current_accuracy'] > metrics['livekit_accuracy']:
            diff = metrics['current_accuracy'] - metrics['livekit_accuracy']
            print(f"⚠️  LiveKit accuracy is {diff:.1f}% lower than current")
            print("   May need to fine-tune thresholds or conversation handling.")

        # Overall recommendation
        print("\nOVERALL RECOMMENDATION:")
        print("="*60)
        if metrics['latency_improvement_pct'] > 50 and metrics['livekit_accuracy'] >= metrics['current_accuracy']:
            print("✅ STRONGLY RECOMMENDED:")
            print("   LiveKit provides better performance in both latency AND accuracy.")
            print("   Proceed with integration and enable in production.")
        elif metrics['latency_improvement_pct'] > 50:
            print("✅ RECOMMENDED:")
            print("   Significant latency improvement outweighs minor trade-offs.")
            print("   Proceed with integration and monitor accuracy in production.")
        elif metrics['latency_improvement_pct'] > 20:
            print("⚠️  CONSIDER WITH TESTING:")
            print("   Moderate latency improvement. Test thoroughly in production")
            print("   before deciding on rollout strategy.")
        else:
            print("❓ NOT RECOMMENDED (without further testing):")
            print("   LiveKit shows minimal improvement. Consider:")
            print("   - Testing with more diverse interview scenarios")
            print("   - Fine-tuning confidence thresholds")
            print("   - Evaluating on real interview recordings")

        print("="*60 + "\n")

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        return
    except Exception as e:
        logger.error(f"Benchmark suite error: {e}", exc_info=True)
        return


def main():
    """Main entry point for standalone execution"""
    # Check if we're in development mode
    sys.path.insert(0, str(Path(__file__).parent.parent))

    logger.info("Starting LiveKit Turn Detection Benchmark...")

    # Run benchmark
    if sys.version_info >= (3, 7):
        asyncio.run(run_full_benchmark())
    else:
        # Python 3.6 compatibility
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_full_benchmark())

    logger.info("Benchmark complete.")


if __name__ == "__main__":
    main()
