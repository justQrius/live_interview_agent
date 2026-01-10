"""
Tests for the Phase 3C Pipeline Integration.

Tests the complete question processing pipeline:
Query Reformulation → Question Splitting → Enhanced Retrieval → Answer Generation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.classification.question_detector import QuestionDetector
from src.classification.query_reformulator import QueryReformulator
from src.classification.question_splitter import QuestionSplitter


class TestPipelineComponents:
    """Test that all pipeline components work together."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_full_pipeline_simple_question(self, detector, reformulator, splitter):
        """Simple question flows through pipeline correctly."""
        question = "What is your experience with Python?"
        history = []
        
        # Step 1: Detection
        is_question, confidence, q_type = detector.is_actionable_question(question, history)
        assert is_question
        assert confidence >= 0.7
        
        # Step 2: Reformulation (no change for standalone question)
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, [])
        assert not was_reformulated
        assert reformulated == question
        
        # Step 3: Splitting (no split for simple question)
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) == 1
        assert sub_questions[0] == question
    
    def test_full_pipeline_follow_up(self, detector, reformulator, splitter):
        """Follow-up question is reformulated correctly."""
        question = "What about testing?"
        history = [
            {"question": "Tell me about your Python experience", "answer": "I have 5 years..."}
        ]
        
        # Step 1: Detection
        is_question, confidence, q_type = detector.is_actionable_question(
            question, 
            [{"role": "user", "content": history[0]["question"]}, 
             {"role": "assistant", "content": history[0]["answer"]}]
        )
        assert is_question
        assert q_type == "follow_up"
        
        # Step 2: Reformulation (should expand)
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, history)
        assert was_reformulated
        assert "testing" in reformulated.lower()
        assert "Python" in reformulated or "python" in reformulated.lower()
        
        # Step 3: Splitting
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) >= 1
    
    def test_full_pipeline_compound_question(self, detector, reformulator, splitter):
        """Compound question is split correctly."""
        question = "What is your experience with Python and how do you handle testing?"
        
        # Step 1: Detection
        is_question, confidence, q_type = detector.is_actionable_question(question, [])
        assert is_question
        
        # Step 2: Reformulation (no change for standalone)
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, [])
        assert not was_reformulated
        
        # Step 3: Splitting (should split on 'and how')
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) == 2
        assert any("Python" in q for q in sub_questions)
        assert any("testing" in q.lower() for q in sub_questions)
    
    def test_pipeline_non_question_filtered(self, detector, reformulator, splitter):
        """Non-questions are filtered at detection stage."""
        statement = "Let me tell you about the next topic."
        
        # Step 1: Detection should filter this
        is_question, confidence, q_type = detector.is_actionable_question(statement, [])
        assert not is_question or confidence < 0.7
        # Pipeline should stop here - no reformulation or splitting needed
    
    def test_pipeline_acknowledgment_filtered(self, detector, reformulator, splitter):
        """Acknowledgments are filtered at detection stage."""
        ack = "Okay, that makes sense."
        
        is_question, confidence, q_type = detector.is_actionable_question(ack, [])
        assert not is_question
        assert q_type == "acknowledgment"


class TestPipelineEdgeCases:
    """Test edge cases in pipeline processing."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_empty_input(self, detector, reformulator, splitter):
        """Empty input is handled gracefully at each stage."""
        # Detection
        is_question, confidence, q_type = detector.is_actionable_question("", [])
        assert not is_question
        
        # Reformulation
        reformulated, was_reformulated = reformulator.reformulate_if_needed("", [])
        assert reformulated == ""
        assert not was_reformulated
        
        # Splitting
        sub_questions = splitter.split_questions("")
        assert sub_questions == []
    
    def test_very_long_question(self, detector, reformulator, splitter):
        """Long questions are processed without error."""
        long_question = "Tell me about your experience with " + "very " * 100 + "complex systems?"
        
        is_question, confidence, q_type = detector.is_actionable_question(long_question, [])
        assert is_question
        
        reformulated, _ = reformulator.reformulate_if_needed(long_question, [])
        assert reformulated == long_question
        
        sub_questions = splitter.split_questions(reformulated)
        assert len(sub_questions) >= 1
    
    def test_special_characters(self, detector, reformulator, splitter):
        """Questions with special characters are handled."""
        question = "What's your experience with C++ & Java?"
        
        is_question, confidence, q_type = detector.is_actionable_question(question, [])
        assert is_question
        
        sub_questions = splitter.split_questions(question)
        assert len(sub_questions) >= 1


class TestConversationHistoryFormats:
    """Test different conversation history formats."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    def test_history_format_conversion(self, reformulator):
        """History in different formats is handled."""
        # Reformulator expects [{"question": ..., "answer": ...}]
        history = [
            {"question": "Tell me about databases", "answer": "I worked with PostgreSQL..."}
        ]
        
        question = "What about NoSQL?"
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, history)
        
        assert was_reformulated
        assert "NoSQL" in reformulated
    
    def test_empty_history(self, reformulator):
        """Empty history doesn't cause errors."""
        question = "What about this?"
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, [])
        
        # Can't reformulate without history context
        assert not was_reformulated
        assert reformulated == question
    
    def test_malformed_history_entry(self, reformulator):
        """Malformed history entries are skipped gracefully."""
        history = [
            {"invalid": "entry"},  # Missing question/answer
            {"question": "Valid question", "answer": "Valid answer"}
        ]
        
        question = "Tell me more"
        reformulated, was_reformulated = reformulator.reformulate_if_needed(question, history)
        
        # Should use the valid entry
        assert was_reformulated


class TestQuestionTypeAwareness:
    """Test question type detection accuracy."""
    
    @pytest.fixture
    def detector(self):
        return QuestionDetector()
    
    def test_behavioral_question(self, detector):
        """Behavioral questions are classified as interview questions."""
        behavioral_questions = [
            "Tell me about a time when you faced a challenge",
            "Describe a situation where you had to lead a team",
            "Give me an example of when you failed",
        ]
        
        for q in behavioral_questions:
            is_question, confidence, q_type = detector.is_actionable_question(q, [])
            assert is_question
            # Current implementation returns 'behavioral' or 'interview_question'
            assert q_type in ["behavioral", "interview_question"], f"Unexpected type for: {q}"
    
    def test_technical_question(self, detector):
        """Technical questions are classified as interview questions."""
        technical_questions = [
            "How would you implement a caching system?",
            "Explain the difference between SQL and NoSQL",
            "What data structures would you use for this problem?",
        ]
        
        for q in technical_questions:
            is_question, confidence, q_type = detector.is_actionable_question(q, [])
            assert is_question
            # Current implementation returns 'technical' or 'interview_question'
            assert q_type in ["technical", "interview_question"], f"Unexpected type for: {q}"
    
    def test_motivation_question(self, detector):
        """Motivation questions are classified as interview questions."""
        motivation_questions = [
            "Why do you want to work here?",
            "What motivates you in your career?",
            "Why are you interested in this role?",
        ]
        
        for q in motivation_questions:
            is_question, confidence, q_type = detector.is_actionable_question(q, [])
            assert is_question
            # Current implementation returns 'motivation' or 'interview_question'
            assert q_type in ["motivation", "interview_question"], f"Unexpected type for: {q}"
