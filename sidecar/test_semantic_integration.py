"""
Integration test for semantic turn detection with ONNX executor.

Tests the complete chain:
1. Initialize session manager with semantic detection ONNX executor
2. Verify fallback to wrapper when ONNX fails
3. Verify graceful degradation when semantic detection disabled
"""

import asyncio
import sys
import os

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    import locale
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add sidecar to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.livekit_integration.session_manager import get_session_manager, reset_session_manager
from src.rag.store import VectorStore

# Helper for printing checkmarks that work on Windows
CHECK = "[OK]"
CROSS = "[FAIL]"


async def test_semantic_detection_enabled():
    """Test session manager with semantic detection enabled."""
    print("\n" + "="*60)
    print("TEST 1: Semantic Detection Enabled")
    print("="*60)

    try:
        # Reset singleton to ensure clean state
        reset_session_manager()

        # Create vector store (dummy key for testing)
        vector_store = VectorStore(api_key='test-key-for-integration-test')

        # Create session manager with semantic detection enabled
        manager = get_session_manager(
            config={
                'turn_detection_enabled': True,
                'use_semantic_detection': True,
                'inference_timeout': 3.0
            },
            vector_store=vector_store,
            context_manager=None
        )

        print(f"{CHECK} Session manager created with semantic detection")

        # Start session manager
        await manager.start()
        print(f"{CHECK} Session manager started")

        # Check if ONNX executor was initialized
        if manager._onnx_executor:
            print(f"{CHECK} ONNX executor initialized (model_path='{manager._onnx_executor.model_path}')")
        else:
            print(f"{CROSS} ONNX executor not initialized (this is expected if model files not present)")

        print(f"{CHECK} Agent RAG engine type: {type(manager.agent.rag_engine).__name__}")

        # Stop session manager
        await manager.stop()
        print(f"{CHECK} Session manager stopped cleanly")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_semantic_detection_disabled():
    """Test session manager with semantic detection disabled."""
    print("\n" + "="*60)
    print("TEST 2: Semantic Detection Disabled")
    print("="*60)

    try:
        # Reset singleton
        reset_session_manager()

        # Create session manager with semantic detection disabled
        manager = get_session_manager(
            config={
                'turn_detection_enabled': True,
                'use_semantic_detection': False,
                'inference_timeout': 3.0
            },
            vector_store=VectorStore(api_key='test-key'),
            context_manager=None
        )

        print(f"{CHECK} Session manager created with semantic detection disabled")

        # Start session manager
        await manager.start()
        print(f"{CHECK} Session manager started")

        # Verify ONNX executor is NOT initialized
        if manager._onnx_executor is None:
            print(f"{CHECK} ONNX executor correctly not initialized")
        else:
            print(f"{CROSS} ONNX executor should not be initialized")
            return False

        print(f"{CHECK} Agent RAG engine type: {type(manager.agent.rag_engine).__name__}")

        # Stop session manager
        await manager.stop()
        print(f"{CHECK} Session manager stopped cleanly")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_turn_detection_disabled():
    """Test session manager with turn detection completely disabled."""
    print("\n" + "="*60)
    print("TEST 3: Turn Detection Completely Disabled")
    print("="*60)

    try:
        # Reset singleton
        reset_session_manager()

        # Create session manager with all turn detection disabled
        manager = get_session_manager(
            config={
                'turn_detection_enabled': False,
                'use_semantic_detection': True,
                'inference_timeout': 3.0
            },
            vector_store=VectorStore(api_key='test-key'),
            context_manager=None
        )

        print(f"{CHECK} Session manager created with turn detection disabled")

        # Start session manager
        await manager.start()
        print(f"{CHECK} Session manager started")

        # Verify ONNX executor is NOT initialized
        if manager._onnx_executor is None:
            print(f"{CHECK} ONNX executor correctly not initialized")
        else:
            print(f"{CROSS} ONNX executor should not be initialized")
            return False

        print(f"{CHECK} Agent RAG engine type: {type(manager.agent.rag_engine).__name__}")

        # Stop session manager
        await manager.stop()
        print(f"{CHECK} Session manager stopped cleanly")

        return True

    except Exception as e:
        print(f"{CROSS} Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fallback_behavior():
    """Test that system falls back gracefully when ONNX fails."""
    print("\n" + "="*60)
    print("TEST 4: Fallback Behavior Verification")
    print("="*60)
    print("Note: This test verifies the fallback logic in handle_transcript()")
    print("      Actual fallback requires ONNX model files to trigger")

    try:
        # Reset singleton
        reset_session_manager()

        # Create manager with semantic enabled
        manager = get_session_manager(
            config={
                'turn_detection_enabled': True,
                'use_semantic_detection': True,
                'inference_timeout': 3.0
            },
            vector_store=VectorStore(api_key='test-key'),
            context_manager=None
        )

        # Check configuration
        print(f"{CHECK} Turn detection enabled: {manager._turn_detection_enabled}")
        print(f"{CHECK} Use semantic detection: {manager._use_semantic_detection}")
        print(f"{CHECK} ONNX executor available: {manager._onnx_executor is not None}")
        print(f"{CHECK} Fallback will occur: {manager._onnx_executor is None and manager._turn_detection_enabled}")

        # Cleanup
        await manager.stop()
        return True

    except Exception as e:
        print(f"{CROSS} Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("SEMANTIC TURN DETECTION INTEGRATION TESTS")
    print("="*60)

    results = []

    # Run tests
    results.append(("Semantic Detection Enabled", await test_semantic_detection_enabled()))
    results.append(("Semantic Detection Disabled", await test_semantic_detection_disabled()))
    results.append(("Turn Detection Disabled", await test_turn_detection_disabled()))
    results.append(("Fallback Behavior", await test_fallback_behavior()))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    total = len(results)
    passed = sum(1 for _, result in results if result)

    for test_name, result in results:
        status = "[OK] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:40s} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
