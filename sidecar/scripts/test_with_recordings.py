"""
Test LiveKit integration with real interview recordings.

This script tests the agent and session manager with actual interview
transcripts to verify real-world performance.

Usage:
    python scripts/test_with_recordings.py path/to/recording.json
    python scripts/test_with_recordings.py --sample  # Use sample recording
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add sidecar/src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from livekit_integration.session_manager import (
    get_session_manager,
    reset_session_manager
)
from livekit_integration.livekit_metrics import get_metrics_collector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Sample recording for testing when no file is provided
SAMPLE_RECORDING = {
    "metadata": {
        "interviewer": "HR Manager",
        "candidate": "Jane Doe",
        "date": "2024-01-15",
        "duration_minutes": 30
    },
    "utterances": [
        {
            "speaker": "interviewer",
            "text": "Tell me about your experience with Python.",
            "timestamp": "00:00:05"
        },
        {
            "speaker": "candidate",
            "text": "I have five years of experience with Python. I've worked with Django, Flask, and FastAPI.",
            "timestamp": "00:00:12"
        },
        {
            "speaker": "interviewer",
            "text": "What frameworks are you most comfortable with?",
            "timestamp": "00:00:30"
        },
        {
            "speaker": "candidate",
            "text": "I'm most comfortable with Django for web applications and FastAPI for APIs.",
            "timestamp": "00:00:35"
        },
        {
            "speaker": "interviewer",
            "text": "Tell me about a challenging project you worked on.",
            "timestamp": "00:01:00"
        },
        {
            "speaker": "candidate",
            "text": "I worked on a payment processing system that had to handle 1M transactions per day. The main challenge was ensuring consistency across multiple servers.",
            "timestamp": "00:01:15"
        },
        {
            "speaker": "interviewer",
            "text": "That's interesting.",
            "timestamp": "00:01:45"
        },
        {
            "speaker": "candidate",
            "text": "Thank you. I was responsible for designing the architecture and leading a team of 5 engineers.",
            "timestamp": "00:01:50"
        }
    ]
}


async def test_with_recording(recording_path: Path, config: dict = None):
    """
    Test using actual interview recording transcription.

    Args:
        recording_path: Path to JSON recording file
        config: Optional configuration for session manager
    """

    logger.info("="*70)
    logger.info("LIVEKIT AGENT INTEGRATION TEST - REAL RECORDINGS")
    logger.info("="*70)

    # Reset session manager singleton
    reset_session_manager()

    try:
        # Load recording
        with open(recording_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)

        logger.info(f"Loaded recording: {recording_path.name}")
        logger.info(f"Metadata: {transcript_data.get('metadata', {})}")

        # Get session manager
        session_manager = get_session_manager(config=config)
        await session_manager.start()
        logger.info("Session manager started")

        # Get metrics collector for tracking
        metrics_collector = get_metrics_collector()

        # Process utterances
        utterances = transcript_data.get("utterances", [])
        turn_count = 0
        question_count = 0
        error_count = 0

        logger.info(f"\nProcessing {len(utterances)} utterances...\n")

        for i, utterance in enumerate(utterances, 1):
            speaker = utterance.get("speaker", "unknown")
            text = utterance.get("text", "")
            timestamp = utterance.get("timestamp", "")

            # Filter: only process interviewer utterances
            # (In real agent flow, candidate responses would also be processed)

            is_interviewer = speaker.lower() in [
                "interviewer", "host", "hr", "hiring manager"
            ]

            logger.info(f"[{i}/{len(utterances)}] [{timestamp}] [{speaker}] {text[:60]}...")

            try:
                if is_interviewer or speaker.lower() == "user":
                    # Send through session manager
                    await session_manager.handle_transcript(
                        transcript=text,
                        speaker=speaker
                    )
                    turn_count += 1

                    # Rough heuristic: question detection
                    # (Agent would do this properly)
                    if "?" in text or any(q in text.lower().split()[:3] for q in ["tell", "what", "how", "why", "describe", "explain"]):
                        question_count += 1
                        logger.info(f"  → Question detected")

                elif speaker.lower() in ["candidate", "assistant", "user"]:
                    # Candidate/assistant response
                    # These would typically be added to conversation history
                    pass

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ Error: {e}")

        # Summary
        logger.info("\n" + "="*70)
        logger.info("TEST SUMMARY")
        logger.info("="*70)
        logger.info(f"Total interview turns processed: {turn_count}")
        logger.info(f"Questions detected (heuristic): {question_count}")
        logger.info(f"Errors encountered: {error_count}")

        # Metrics summary
        livekit_stats = metrics_collector.get_stats()
        logger.info(f"\nLiveKit Metrics:")
        logger.info(f"  Total checks: {livekit_stats['total_checks']}")
        logger.info(f"  Latency avg: {livekit_stats['latency']['avg_ms']:.1f}ms")
        logger.info(f"  Error rate: {livekit_stats['error_rate']:.1%}")

        logger.info("✅ Test completed successfully")

        # Stop manager
        await session_manager.stop()
        logger.info("Session manager stopped")

    except FileNotFoundError as e:
        logger.error(f"❌ Recording file not found: {recording_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in recording file")
        raise
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


def create_sample_recording(output_path: Path):
    """
    Create a sample recording JSON file for testing.

    Args:
        output_path: Where to save the sample recording
    """

    logger.info(f"Creating sample recording at: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(SAMPLE_RECORDING, f, indent=2)

    logger.info("Sample recording created")


def main():
    """Main entry point."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Test LiveKit agent with interview recordings"
    )
    parser.add_argument(
        "recording",
        nargs="?",
        help="Path to recording JSON file"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use built-in sample recording"
    )
    parser.add_argument(
        "--create-sample",
        metavar="PATH",
        help="Create sample recording at specified path"
    )
    parser.add_argument(
        "--config",
        help="JSON config for session manager"
    )

    args = parser.parse_args()

    # Handle create-sample flag
    if args.create_sample:
        create_sample_recording(Path(args.create_sample))
        return

    # Determine recording path
    if args.sample:
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False
        ) as f:
            sample_path = Path(f.name)
            json.dump(SAMPLE_RECORDING, f, indent=2)

        logger.info(f"Using sample recording: {sample_path}")
        recording_path = sample_path
    elif args.recording:
        recording_path = Path(args.recording)
        if not recording_path.exists():
            logger.error(f"Recording file not found: {recording_path}")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    # Parse config
    config = None
    if args.config:
        with open(args.config, 'r') as f:
            config = json.load(f)

    # Run test
    asyncio.run(test_with_recording(recording_path, config))


if __name__ == "__main__":
    main()
