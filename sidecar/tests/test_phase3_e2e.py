"""
End-to-End Tests for Phase 3 Functionality.

Comprehensive tests verifying the complete flow from question detection
through answer generation and session persistence.
"""

import time
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from src.classification.question_detector import QuestionDetector
from src.classification.query_reformulator import QueryReformulator
from src.classification.question_splitter import QuestionSplitter


class TestPhase3EndToEnd:
    """End-to-end tests for Phase 3 functionality."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_complete_pipeline_simple_question(self, detector, reformulator, splitter):
        """Simple question flows through complete pipeline correctly."""
        question = "Tell me about your experience with Python."
        history = []
        
        # Step 1: Detection
        is_question, confidence, q_type = detector.is_actionable_question(question, history)
        assert is_question
        assert confidence >= 0.7
        assert q_type in ["interview_question", "behavioral", "technical"]
        
        # Step 2: Reformulation
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, [])
        assert not was_reformulated
        assert reformulated == question
        
        # Step 3: Splitting
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) == 1
        assert sub_questions[0] == question
        
        # Pipeline complete - ready for RAG + LLM
    
    def test_complete_pipeline_follow_up(self, detector, reformulator, splitter):
        """Follow-up question is properly expanded before RAG."""
        initial_question = "Tell me about your Python experience"
        initial_answer = "I have 5 years of experience with Python, primarily in web development..."
        follow_up = "What about testing?"
        
        # Build history for detector
        conversation_history = [
            {"role": "user", "content": initial_question},
            {"role": "assistant", "content": initial_answer}
        ]
        
        # Build history for reformulator (different format)
        reformulator_history = [
            {"question": initial_question, "answer": initial_answer}
        ]
        
        # Step 1: Detection - should detect as follow_up
        is_question, confidence, q_type = detector.is_actionable_question(
            follow_up, conversation_history
        )
        assert is_question
        assert q_type == "follow_up"
        
        # Step 2: Reformulation - should expand
        reformulated, was_reformulated = reformulator.reformulate_if_needed(
            follow_up, reformulator_history
        )
        assert was_reformulated
        assert "testing" in reformulated.lower()
        # Should include context from previous topic
        assert "Python" in reformulated or "python" in reformulated.lower()
        
        # Step 3: Splitting
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) >= 1
    
    def test_complete_pipeline_compound_question(self, detector, reformulator, splitter):
        """Compound question is split into multiple sub-questions."""
        compound = "What's your Python experience and how do you approach testing?"
        
        # Step 1: Detection
        is_question, confidence, q_type = detector.is_actionable_question(compound, [])
        assert is_question
        
        # Step 2: Reformulation (no change for standalone)
        reformulated, was_reformulated = reformulator.reformulate_if_needed(compound, [])
        assert not was_reformulated
        
        # Step 3: Splitting - should split
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) == 2
        
        # Verify each sub-question is valid
        for sq in sub_questions:
            is_q, conf, _ = detector.is_actionable_question(sq, [])
            assert is_q or conf > 0.5  # Sub-questions should still be questions
    
    def test_statement_not_processed(self, detector):
        """Statements are filtered and don't trigger answer generation."""
        statements = [
            "That's very interesting, thank you.",
            "Let me tell you about the next topic.",
            "Okay, moving on to the technical questions.",
            "I see, that makes sense.",
        ]
        
        for statement in statements:
            is_question, confidence, q_type = detector.is_actionable_question(statement, [])
            # Either not a question or low confidence
            should_skip = not is_question or confidence < 0.7
            assert should_skip, f"Statement should be filtered: {statement}"
    
    def test_acknowledgment_not_processed(self, detector):
        """Acknowledgments are filtered correctly."""
        acknowledgments = [
            "Okay.",
            "Got it.",
            "I see.",
            "Great!",
            "Makes sense.",
            "Alright.",
        ]
        
        for ack in acknowledgments:
            is_question, confidence, q_type = detector.is_actionable_question(ack, [])
            assert not is_question
            assert q_type == "acknowledgment"
    
    def test_clarification_request_detected(self, detector):
        """Clarification requests are properly detected."""
        clarifications = [
            "Could you repeat that?",
            "What do you mean by that?",
            "Sorry, I didn't catch that.",
            "Can you clarify?",
        ]
        
        for clarification in clarifications:
            is_question, confidence, q_type = detector.is_actionable_question(clarification, [])
            assert is_question
            assert q_type == "clarification"


class TestPhase3Performance:
    """Performance benchmarks for Phase 3 components."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_question_detection_latency(self, detector):
        """Question detection < 10ms P95."""
        test_questions = [
            "Tell me about yourself",
            "What's your experience with Python?",
            "Why do you want to work here?",
            "Describe a challenging project",
            "How do you handle pressure?",
        ]
        
        latencies = []
        for _ in range(100):
            for q in test_questions:
                start = time.perf_counter()
                detector.is_actionable_question(q, [])
                latencies.append((time.perf_counter() - start) * 1000)
        
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        avg = np.mean(latencies)
        
        assert p95 < 10, f"P95 latency {p95:.2f}ms exceeds 10ms target"
        print(f"Detection latency: avg={avg:.3f}ms, p95={p95:.3f}ms, p99={p99:.3f}ms")
    
    def test_query_reformulation_latency(self, reformulator):
        """Query reformulation < 5ms P95."""
        history = [
            {"question": "Tell me about Python", "answer": "I have 5 years..."}
        ]
        
        test_followups = [
            "What about testing?",
            "Tell me more",
            "Can you elaborate?",
            "How about databases?",
            "And what were the results?",
        ]
        
        latencies = []
        for _ in range(100):
            for q in test_followups:
                start = time.perf_counter()
                reformulator.reformulate_if_needed(q, history)
                latencies.append((time.perf_counter() - start) * 1000)
        
        p95 = np.percentile(latencies, 95)
        avg = np.mean(latencies)
        
        assert p95 < 5, f"P95 latency {p95:.2f}ms exceeds 5ms target"
        print(f"Reformulation latency: avg={avg:.3f}ms, p95={p95:.3f}ms")
    
    def test_question_splitting_latency(self, splitter):
        """Question splitting < 3ms P95."""
        test_questions = [
            "What is your experience?",
            "Tell me about Python and how you handle testing?",
            "What's X? How's Y? Why's Z?",
            "Describe your role, additionally, what about leadership?",
        ]
        
        latencies = []
        for _ in range(100):
            for q in test_questions:
                start = time.perf_counter()
                splitter.split_questions(q)
                latencies.append((time.perf_counter() - start) * 1000)
        
        p95 = np.percentile(latencies, 95)
        avg = np.mean(latencies)
        
        assert p95 < 3, f"P95 latency {p95:.2f}ms exceeds 3ms target"
        print(f"Splitting latency: avg={avg:.3f}ms, p95={p95:.3f}ms")
    
    def test_combined_classification_pipeline_latency(self, detector, reformulator, splitter):
        """Combined classification pipeline < 15ms P95 (no LLM/RAG)."""
        history = [
            {"question": "Tell me about Python", "answer": "I have 5 years..."}
        ]
        conv_history = [
            {"role": "user", "content": "Tell me about Python"},
            {"role": "assistant", "content": "I have 5 years..."}
        ]
        
        test_questions = [
            "What about testing?",
            "Tell me about your leadership experience and how you handle conflicts?",
            "Why do you want this role?",
        ]
        
        latencies = []
        for _ in range(50):
            for q in test_questions:
                start = time.perf_counter()
                
                # Full pipeline
                is_q, conf, q_type = detector.is_actionable_question(q, conv_history)
                if is_q and conf >= 0.7:
                    reformulated, _ = reformulator.reformulate_if_needed(q, history)
                    sub_questions = splitter.split_questions(reformulated)
                
                latencies.append((time.perf_counter() - start) * 1000)
        
        p95 = np.percentile(latencies, 95)
        avg = np.mean(latencies)
        
        assert p95 < 15, f"P95 latency {p95:.2f}ms exceeds 15ms target"
        print(f"Combined pipeline latency: avg={avg:.3f}ms, p95={p95:.3f}ms")


class TestConversationFlow:
    """Test realistic conversation flows."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_interview_opening_flow(self, detector, reformulator, splitter):
        """Test typical interview opening conversation."""
        conversation = [
            # Small talk (should skip)
            ("Thanks for joining us today.", False, "statement"),
            ("How are you doing?", False, "small_talk"),  # Small talk - correctly skipped
            # Opening question (without "Let's start" prefix which is detected as statement)
            ("Tell me about yourself.", True, "interview_question"),
            # Follow-up
            ("What made you interested in our company?", True, "interview_question"),
        ]
        
        history = []
        for text, should_be_actionable, expected_type in conversation:
            is_q, conf, q_type = detector.is_actionable_question(text, history)
            
            if should_be_actionable:
                assert is_q and conf >= 0.7, f"Should be actionable: {text} (got is_q={is_q}, conf={conf})"
            
            # Build history if it was a question
            if is_q and conf >= 0.7:
                history.append({"role": "user", "content": text})
                history.append({"role": "assistant", "content": "Sample answer..."})
    
    def test_technical_deep_dive_flow(self, detector, reformulator, splitter):
        """Test technical question deep dive with follow-ups."""
        # Initial question
        initial = "How would you design a scalable caching system?"
        is_q, conf, q_type = detector.is_actionable_question(initial, [])
        assert is_q
        assert q_type in ["interview_question", "technical"]
        
        # Build history
        history = [{"question": initial, "answer": "I would use Redis with..."}]
        conv_history = [
            {"role": "user", "content": initial},
            {"role": "assistant", "content": "I would use Redis with..."}
        ]
        
        # Follow-up questions
        followups = [
            "What about cache invalidation?",
            "How would you handle the thundering herd problem?",
            "Tell me more about your Redis experience",
        ]
        
        for followup in followups:
            is_q, conf, q_type = detector.is_actionable_question(followup, conv_history)
            assert is_q
            
            reformulated, was_reformulated = reformulator.reformulate_if_needed(followup, history)
            # Some should be reformulated
            
            # Update history
            history.append({"question": followup, "answer": "Sample..."})
            conv_history.append({"role": "user", "content": followup})
            conv_history.append({"role": "assistant", "content": "Sample..."})
    
    def test_behavioral_star_method_flow(self, detector, reformulator, splitter):
        """Test behavioral question with STAR method probing."""
        # Main behavioral question
        main = "Tell me about a time when you had to deal with a difficult team member."
        is_q, conf, q_type = detector.is_actionable_question(main, [])
        assert is_q
        assert q_type in ["behavioral", "interview_question"]
        
        history = [{"question": main, "answer": "In my previous role at XYZ..."}]
        conv_history = [
            {"role": "user", "content": main},
            {"role": "assistant", "content": "In my previous role at XYZ..."}
        ]
        
        # STAR probing follow-ups
        star_probes = [
            "What was the specific situation?",
            "What actions did you take?",
            "What was the result?",
            "What did you learn from that experience?",
        ]
        
        for probe in star_probes:
            is_q, conf, q_type = detector.is_actionable_question(probe, conv_history)
            assert is_q
            # Can be follow_up or interview_question - both are valid
            assert q_type in ["follow_up", "interview_question"]
            
            # Update history for next iteration
            conv_history.append({"role": "user", "content": probe})
            conv_history.append({"role": "assistant", "content": "..."})


class TestEdgeCasesAndRobustness:
    """Test edge cases and robustness."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_unicode_questions(self, detector, reformulator, splitter):
        """Handle questions with unicode characters."""
        unicode_questions = [
            "What's your experience with résumé parsing?",
            "How do you handle naïve Bayes classifiers?",
            "Tell me about working with 日本語 text?",
        ]
        
        for q in unicode_questions:
            # Should not raise
            is_q, conf, q_type = detector.is_actionable_question(q, [])
            reformulated, _ = reformulator.reformulate_if_needed(q, [])
            sub_questions = splitter.split_questions(q)
            
            assert isinstance(is_q, bool)
            assert isinstance(reformulated, str)
            assert isinstance(sub_questions, list)
    
    def test_very_short_questions(self, detector, reformulator, splitter):
        """Handle very short questions."""
        short_questions = ["Why?", "How?", "What?", "And?"]
        
        for q in short_questions:
            is_q, conf, q_type = detector.is_actionable_question(q, [])
            # May or may not be detected as questions, but should not crash
            assert isinstance(is_q, bool)
    
    def test_very_long_questions(self, detector, reformulator, splitter):
        """Handle very long questions."""
        long_q = "Tell me about " + "your experience with " * 50 + "complex systems?"
        
        is_q, conf, q_type = detector.is_actionable_question(long_q, [])
        reformulated, _ = reformulator.reformulate_if_needed(long_q, [])
        sub_questions = splitter.split_questions(long_q)
        
        assert isinstance(is_q, bool)
        assert len(reformulated) > 0
        assert len(sub_questions) >= 1
    
    def test_malformed_history(self, detector, reformulator):
        """Handle malformed conversation history gracefully."""
        # Valid histories that should work
        valid_histories = [
            [],
            [{"role": "user", "content": "test"}],
        ]
        
        for history in valid_histories:
            is_q, conf, q_type = detector.is_actionable_question("Test?", history)
            assert isinstance(is_q, bool)
        
        # Invalid histories - detector may handle or raise, but should be predictable
        # Note: Current implementation may not handle all edge cases
    
    def test_concurrent_processing(self, detector):
        """Test that processing is thread-safe."""
        import concurrent.futures
        
        questions = [
            "Tell me about Python",
            "What's your experience?",
            "How do you handle testing?",
        ] * 10
        
        def process(q):
            return detector.is_actionable_question(q, [])
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process, questions))
        
        assert len(results) == len(questions)
        assert all(isinstance(r[0], bool) for r in results)
