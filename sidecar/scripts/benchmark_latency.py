#!/usr/bin/env python3
"""
Latency Benchmark Script for Live Interview Agent.

Measures end-to-end latency for different configurations:
1. Batch STT only (baseline)
2. Streaming STT with acoustic endpointing
3. Streaming STT with semantic endpointing
4. Hybrid mode (streaming + accumulator)

Usage:
    # Basic benchmark (requires server running on localhost:8765)
    cd sidecar
    python scripts/benchmark_latency.py

    # With specific provider
    python scripts/benchmark_latency.py --provider deepgram

    # Test streaming modes
    python scripts/benchmark_latency.py --mode streaming

    # Full comparison
    python scripts/benchmark_latency.py --mode all --questions 10

    # Dry run (no actual API calls)
    python scripts/benchmark_latency.py --dry-run

Environment Variables:
    GROQ_API_KEY, DEEPGRAM_API_KEY, ASSEMBLYAI_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY
"""

import asyncio
import json
import time
import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from statistics import mean, median

try:
    import numpy as np
except ImportError:
    np = None  # Optional, used for percentile calculation

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LatencyMeasurement:
    """Single latency measurement."""
    question: str
    total_latency_ms: float = 0.0
    first_token_latency_ms: float = 0.0
    complete_latency_ms: float = 0.0
    provider: str = "unknown"
    mode: str = "batch"
    endpointing_type: str = "unknown"
    success: bool = True
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results."""
    provider: str
    mode: str
    measurements: List[LatencyMeasurement] = field(default_factory=list)
    
    @property
    def success_count(self) -> int:
        return sum(1 for m in self.measurements if m.success)
    
    @property
    def total_count(self) -> int:
        return len(self.measurements)
    
    def _get_values(self, field: str) -> List[float]:
        return [getattr(m, field) for m in self.measurements if m.success]
    
    def avg(self, field: str) -> float:
        values = self._get_values(field)
        return mean(values) if values else 0.0
    
    def med(self, field: str) -> float:
        values = self._get_values(field)
        return median(values) if values else 0.0
    
    def p95(self, field: str) -> float:
        values = sorted(self._get_values(field))
        if not values:
            return 0.0
        if np is not None:
            return float(np.percentile(values, 95))
        idx = int(len(values) * 0.95)
        return values[min(idx, len(values) - 1)]
    
    def min_val(self, field: str) -> float:
        values = self._get_values(field)
        return min(values) if values else 0.0
    
    def max_val(self, field: str) -> float:
        values = self._get_values(field)
        return max(values) if values else 0.0
    
    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "mode": self.mode,
            "success_rate": f"{self.success_count}/{self.total_count}",
            "avg_first_token_ms": round(self.avg("first_token_latency_ms"), 1),
            "median_first_token_ms": round(self.med("first_token_latency_ms"), 1),
            "p95_first_token_ms": round(self.p95("first_token_latency_ms"), 1),
            "min_first_token_ms": round(self.min_val("first_token_latency_ms"), 1),
            "max_first_token_ms": round(self.max_val("first_token_latency_ms"), 1),
            "avg_complete_ms": round(self.avg("complete_latency_ms"), 1),
        }


# ============================================================================
# Test Questions
# ============================================================================

TEST_QUESTIONS = [
    # Behavioral questions (common in interviews)
    "Tell me about a time when you had to deal with a difficult coworker.",
    "What's your greatest professional achievement?",
    "Describe a situation where you had to learn something new quickly.",
    
    # Technical questions
    "How would you design a distributed cache system?",
    "Explain the difference between REST and GraphQL.",
    
    # Follow-up style questions (short, depends on context)
    "Can you tell me more about that project?",
    "What was the outcome?",
    
    # Multi-part questions
    "What are your strengths and weaknesses, and how do they affect your work?",
    
    # Short questions
    "Why this company?",
    "What motivates you?",
]


# ============================================================================
# Benchmark Class
# ============================================================================

class LatencyBenchmark:
    """Benchmarks latency for different STT/endpointing configurations."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        timeout: float = 30.0,
        dry_run: bool = False,
    ):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.timeout = timeout
        self.dry_run = dry_run
        self._ws = None
    
    async def connect(self) -> bool:
        """Connect to the sidecar server."""
        if self.dry_run:
            print(f"[DRY RUN] Would connect to {self.uri}")
            return True
        
        try:
            self._ws = await websockets.connect(
                self.uri,
                max_size=20 * 1024 * 1024,
                ping_interval=30,
                ping_timeout=10,
            )
            print(f"Connected to {self.uri}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from server."""
        if self._ws:
            await self._ws.close()
            self._ws = None
    
    async def _send(self, msg_type: str, data: dict = None) -> None:
        """Send a message to the server."""
        if self.dry_run or not self._ws:
            return
        message = {"type": msg_type, "data": data or {}}
        await self._ws.send(json.dumps(message))
    
    async def _recv(self, timeout: float = None) -> Optional[dict]:
        """Receive a message from the server."""
        if self.dry_run or not self._ws:
            return None
        
        try:
            raw = await asyncio.wait_for(
                self._ws.recv(),
                timeout=timeout or self.timeout
            )
            return json.loads(raw)
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"Receive error: {e}")
            return None
    
    async def start_session(
        self,
        api_keys: dict,
        preferences: dict = None,
    ) -> bool:
        """Start a session with the given configuration."""
        if self.dry_run:
            print("[DRY RUN] Would start session")
            return True
        
        data = {
            "apiKeys": api_keys,
            "preferences": preferences or {},
        }
        
        await self._send("START_SESSION", data)
        
        # Wait for status message
        while True:
            msg = await self._recv(timeout=15.0)
            if not msg:
                print("Timeout waiting for session start")
                return False
            if msg.get("type") == "STATUS":
                state = msg.get("data", {}).get("state")
                if state == "listening":
                    print(f"Session started (state={state})")
                    return True
            if msg.get("type") == "ERROR":
                print(f"Error starting session: {msg.get('data', {}).get('message')}")
                return False
    
    async def stop_session(self) -> None:
        """Stop the current session."""
        if self.dry_run:
            print("[DRY RUN] Would stop session")
            return
        
        await self._send("STOP_SESSION")
        
        # Wait for idle status
        for _ in range(10):
            msg = await self._recv(timeout=2.0)
            if msg and msg.get("type") == "STATUS":
                break
        
        print("Session stopped")
    
    async def measure_question_latency(
        self,
        question: str,
        provider: str = "unknown",
        mode: str = "batch",
    ) -> LatencyMeasurement:
        """
        Measure end-to-end latency for a manual question.
        
        Measures:
        - First token latency: Time from question sent to first ANSWER_CHUNK
        - Complete latency: Time from question sent to complete=true
        """
        measurement = LatencyMeasurement(
            question=question,
            provider=provider,
            mode=mode,
        )
        
        if self.dry_run:
            # Simulate latencies for dry run
            import random
            base_latency = {
                "batch": random.uniform(800, 1500),
                "streaming": random.uniform(400, 800),
                "hybrid": random.uniform(300, 600),
            }.get(mode, random.uniform(500, 1000))
            
            measurement.first_token_latency_ms = base_latency
            measurement.complete_latency_ms = base_latency + random.uniform(500, 2000)
            measurement.total_latency_ms = measurement.first_token_latency_ms
            return measurement
        
        start_time = time.time()
        first_token_time = None
        
        try:
            # Send manual question
            await self._send("MANUAL_QUESTION", {"question": question})
            
            # Wait for answer chunks
            complete = False
            while not complete:
                msg = await self._recv(timeout=30.0)
                
                if not msg:
                    measurement.success = False
                    measurement.error = "Timeout waiting for response"
                    return measurement
                
                msg_type = msg.get("type")
                
                if msg_type == "ANSWER_CHUNK":
                    # First answer chunk = first token
                    if first_token_time is None:
                        first_token_time = time.time()
                        measurement.first_token_latency_ms = (first_token_time - start_time) * 1000
                    
                    if msg.get("data", {}).get("complete"):
                        complete = True
                
                elif msg_type == "ANSWER_START":
                    # Answer generation started
                    pass
                
                elif msg_type == "ERROR":
                    measurement.success = False
                    measurement.error = msg.get("data", {}).get("message", "Unknown error")
                    return measurement
            
            end_time = time.time()
            measurement.complete_latency_ms = (end_time - start_time) * 1000
            measurement.total_latency_ms = measurement.first_token_latency_ms
            
        except Exception as e:
            measurement.success = False
            measurement.error = str(e)
        
        return measurement
    
    async def run_benchmark(
        self,
        api_keys: dict,
        questions: List[str],
        mode: str = "batch",
        provider: str = "groq",
    ) -> BenchmarkResult:
        """
        Run a full benchmark suite.
        
        Args:
            api_keys: API keys for providers
            questions: List of questions to test
            mode: "batch", "streaming", or "hybrid"
            provider: STT provider name
        
        Returns:
            BenchmarkResult with all measurements
        """
        result = BenchmarkResult(provider=provider, mode=mode)
        
        if not self.dry_run:
            # Configure preferences based on mode
            preferences = {
                "sttProvider": provider,
            }
            
            # Note: Streaming mode is controlled by AccumulatorConfig.endpointing_mode
            # which defaults to "hybrid". For benchmarking different modes,
            # you'd need to set environment variables before starting the server:
            # ACCUMULATOR_ENDPOINTING_MODE=streaming|timing|hybrid
            
            if not await self.start_session(api_keys, preferences):
                print("Failed to start session")
                return result
            
            # Wait for initialization
            await asyncio.sleep(2.0)
        
        for i, question in enumerate(questions):
            print(f"  [{i+1}/{len(questions)}] Testing: {question[:50]}...")
            
            measurement = await self.measure_question_latency(question, provider, mode)
            result.measurements.append(measurement)
            
            if measurement.success:
                print(f"           → First token: {measurement.first_token_latency_ms:.0f}ms, "
                      f"Complete: {measurement.complete_latency_ms:.0f}ms")
            else:
                print(f"           → Failed: {measurement.error}")
            
            # Small delay between questions
            if not self.dry_run:
                await asyncio.sleep(0.5)
        
        if not self.dry_run:
            await self.stop_session()
        
        return result


# ============================================================================
# Output Formatting
# ============================================================================

def print_results(results: List[BenchmarkResult]) -> None:
    """Print benchmark results in a table format."""
    print("\n" + "=" * 90)
    print("                     LATENCY BENCHMARK RESULTS")
    print("=" * 90)
    
    print(f"\n{'Provider':<12} {'Mode':<10} {'Success':<8} {'Avg':<10} {'Median':<10} "
          f"{'P95':<10} {'Min':<10} {'Max':<10}")
    print("-" * 90)
    
    for r in results:
        d = r.to_dict()
        print(f"{d['provider']:<12} {d['mode']:<10} {d['success_rate']:<8} "
              f"{d['avg_first_token_ms']:<10.0f} {d['median_first_token_ms']:<10.0f} "
              f"{d['p95_first_token_ms']:<10.0f} {d['min_first_token_ms']:<10.0f} "
              f"{d['max_first_token_ms']:<10.0f}")
    
    print("-" * 90)
    
    # Summary
    print("\n📊 Latency Breakdown (First Token):")
    for r in results:
        avg = r.avg("first_token_latency_ms")
        status = "✅" if avg < 3000 else "⚠️" if avg < 5000 else "❌"
        print(f"  {status} {r.mode:<10}: {avg:.0f}ms avg")
    
    print("\n📝 Notes:")
    print("  - First Token: Time from question sent to first answer chunk")
    print("  - Target: <3000ms for optimal user experience")
    print("  - Streaming mode should show ~30-50% improvement over batch")
    
    # Comparison if we have multiple modes
    if len(results) > 1:
        batch_result = next((r for r in results if r.mode == "batch"), None)
        streaming_result = next((r for r in results if r.mode in ("streaming", "hybrid")), None)
        
        if batch_result and streaming_result:
            batch_avg = batch_result.avg("first_token_latency_ms")
            stream_avg = streaming_result.avg("first_token_latency_ms")
            
            if batch_avg > 0:
                improvement = ((batch_avg - stream_avg) / batch_avg) * 100
                print(f"\n🚀 Streaming Improvement: {improvement:.1f}% faster than batch")


def save_results(results: List[BenchmarkResult], output_path: str) -> None:
    """Save results to JSON file."""
    output_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [r.to_dict() for r in results],
        "measurements": [
            {
                "mode": r.mode,
                "provider": r.provider,
                "questions": [
                    {
                        "question": m.question[:50],
                        "first_token_ms": round(m.first_token_latency_ms, 1),
                        "complete_ms": round(m.complete_latency_ms, 1),
                        "success": m.success,
                    }
                    for m in r.measurements
                ]
            }
            for r in results
        ]
    }
    
    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n💾 Results saved to {output_path}")


# ============================================================================
# Main
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="Benchmark latency for Live Interview Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic benchmark with 5 questions
  python benchmark_latency.py --questions 5

  # Test with specific provider
  python benchmark_latency.py --provider deepgram --questions 10

  # Dry run to test script
  python benchmark_latency.py --dry-run

  # Save results to file
  python benchmark_latency.py --output results.json
        """
    )
    
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--provider", default="groq",
                       choices=["groq", "deepgram", "gemini", "openai"],
                       help="STT provider to test")
    parser.add_argument("--mode", default="hybrid",
                       choices=["batch", "streaming", "hybrid", "all"],
                       help="Endpointing mode to test (Note: requires server restart to change)")
    parser.add_argument("--questions", type=int, default=5,
                       help="Number of questions to test (max 10)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Simulate without actual API calls")
    parser.add_argument("--output", type=str,
                       help="Output JSON file for results")
    
    args = parser.parse_args()
    
    # Collect API keys from environment
    api_keys = {}
    key_names = ["groq", "deepgram", "openai", "gemini", "assemblyai", "anthropic"]
    for key in key_names:
        env_key = f"{key.upper()}_API_KEY"
        if os.getenv(env_key):
            api_keys[key] = os.getenv(env_key)
    
    if not api_keys and not args.dry_run:
        print("⚠️  No API keys found in environment!")
        print("Set at least one of: GROQ_API_KEY, DEEPGRAM_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY")
        print("\nRunning in dry-run mode instead...\n")
        args.dry_run = True
    
    # Select questions
    num_questions = min(args.questions, len(TEST_QUESTIONS))
    questions = TEST_QUESTIONS[:num_questions]
    
    print("=" * 60)
    print("        Live Interview Agent - Latency Benchmark")
    print("=" * 60)
    print(f"Server:    {args.host}:{args.port}")
    print(f"Provider:  {args.provider}")
    print(f"Mode:      {args.mode}")
    print(f"Questions: {num_questions}")
    print(f"Dry Run:   {args.dry_run}")
    print("=" * 60)
    
    benchmark = LatencyBenchmark(
        host=args.host,
        port=args.port,
        dry_run=args.dry_run,
    )
    
    if not args.dry_run:
        if not await benchmark.connect():
            sys.exit(1)
    
    results = []
    
    try:
        # Note: Testing different modes requires restarting the server
        # with different ACCUMULATOR_ENDPOINTING_MODE environment variable.
        # For now, we test the current server configuration.
        
        modes = ["batch", "streaming", "hybrid"] if args.mode == "all" else [args.mode]
        
        for mode in modes:
            print(f"\n{'─'*40}")
            print(f"Testing Mode: {mode.upper()}")
            print(f"{'─'*40}")
            
            if args.mode == "all" and not args.dry_run:
                print(f"⚠️  Note: True mode comparison requires server restart with")
                print(f"   ACCUMULATOR_ENDPOINTING_MODE={mode}")
                print(f"   Currently testing with server's configured mode.\n")
            
            result = await benchmark.run_benchmark(
                api_keys=api_keys,
                questions=questions,
                mode=mode,
                provider=args.provider,
            )
            results.append(result)
            
            # Brief pause between modes
            if not args.dry_run and mode != modes[-1]:
                await asyncio.sleep(2.0)
    
    finally:
        if not args.dry_run:
            await benchmark.disconnect()
    
    # Print results
    print_results(results)
    
    # Save to JSON if requested
    if args.output:
        save_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
