"""
Tests for QueryReformulator - expanding follow-up questions into standalone queries.
"""

import pytest

from src.classification.query_reformulator import (
    QueryReformulator,
    FOLLOW_UP_INDICATORS,
)


class TestFollowUpIndicators:
    """Tests for follow-up pattern detection."""
    
    def test_what_about_pattern(self):
        """'What about X' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("What about Python?")
        assert reformulator._is_follow_up("what about the backend?")
    
    def test_how_about_pattern(self):
        """'How about X' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("How about scalability?")
    
    def test_elaborate_pattern(self):
        """'Can you elaborate' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("Can you elaborate?")
        assert reformulator._is_follow_up("Could you expand on that?")
        assert reformulator._is_follow_up("Can you explain more?")
    
    def test_tell_me_more_pattern(self):
        """'Tell me more' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("Tell me more")
        assert reformulator._is_follow_up("Go on")
    
    def test_and_what_pattern(self):
        """'And what/how' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("And what happened next?")
        assert reformulator._is_follow_up("And how did you handle it?")
    
    def test_results_pattern(self):
        """'What were the results' should be detected as follow-up."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("What were the results?")
        assert reformulator._is_follow_up("What are the outcomes?")
    
    def test_pronoun_ending(self):
        """Questions ending with pronouns should be detected."""
        reformulator = QueryReformulator()
        assert reformulator._is_follow_up("Why is that?")
        assert reformulator._is_follow_up("How did you handle it?")
    
    def test_non_follow_up(self):
        """Regular questions should not be detected as follow-ups."""
        reformulator = QueryReformulator()
        assert not reformulator._is_follow_up("Tell me about yourself")
        assert not reformulator._is_follow_up("What is your greatest strength?")
        assert not reformulator._is_follow_up("Describe a challenging project")


class TestQueryReformulator:
    """Tests for QueryReformulator class."""
    
    @pytest.fixture
    def reformulator(self):
        """Create a reformulator instance."""
        return QueryReformulator()
    
    def test_initialization(self, reformulator):
        """Should initialize with default context turns."""
        assert reformulator.context_turns == 5
    
    def test_custom_context_turns(self):
        """Should accept custom context turns."""
        reformulator = QueryReformulator(context_turns=3)
        assert reformulator.context_turns == 3
    
    def test_what_about_expansion(self, reformulator):
        """'What about X' should expand with previous topic."""
        history = [
            {"question": "Tell me about your experience with databases", "answer": "I worked with PostgreSQL..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What about Python?",
            history
        )
        
        assert was_reformulated
        assert "Python" in result
        assert "database" in result.lower() or "previous" in result.lower()
    
    def test_how_about_expansion(self, reformulator):
        """'How about X' should expand with previous topic."""
        history = [
            {"question": "Describe your leadership experience", "answer": "I led a team of 5..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "How about conflict resolution?",
            history
        )
        
        assert was_reformulated
        assert "conflict resolution" in result.lower()
    
    def test_elaborate_expansion(self, reformulator):
        """'Can you elaborate' should include previous topic."""
        history = [
            {"question": "Tell me about your microservices project", "answer": "We built 12 services..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Can you elaborate?",
            history
        )
        
        assert was_reformulated
        assert "microservices" in result.lower() or "project" in result.lower()
    
    def test_tell_me_more_expansion(self, reformulator):
        """'Tell me more' should include previous topic."""
        history = [
            {"question": "What was your role in the startup?", "answer": "I was the tech lead..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Tell me more",
            history
        )
        
        assert was_reformulated
        assert "startup" in result.lower() or "role" in result.lower()
    
    def test_results_expansion(self, reformulator):
        """'What were the results' should include previous topic."""
        history = [
            {"question": "Describe the optimization project", "answer": "We rewrote the query engine..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What were the results?",
            history
        )
        
        assert was_reformulated
        assert "results" in result.lower()
        assert "optimization" in result.lower() or "project" in result.lower()
    
    def test_non_follow_up_unchanged(self, reformulator):
        """Non-follow-up questions should return unchanged."""
        history = [
            {"question": "Previous question", "answer": "Previous answer"}
        ]
        
        original = "Tell me about yourself"
        result, was_reformulated = reformulator.reformulate_if_needed(
            original,
            history
        )
        
        assert not was_reformulated
        assert result == original
    
    def test_no_history_returns_unchanged(self, reformulator):
        """Questions with no history should return unchanged."""
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What about Python?",
            []
        )
        
        assert not was_reformulated
        assert result == "What about Python?"
    
    def test_uses_most_recent_exchange(self, reformulator):
        """Should use most recent exchange for context."""
        history = [
            {"question": "Tell me about Java", "answer": "I used Java for..."},
            {"question": "Tell me about Python", "answer": "Python is my main language..."},
            {"question": "Describe your AWS experience", "answer": "I've deployed to AWS..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Can you elaborate?",
            history
        )
        
        assert was_reformulated
        # Should reference AWS (most recent), not Java or Python
        assert "AWS" in result or "experience" in result.lower()


class TestTopicExtraction:
    """Tests for topic extraction from conversation history."""
    
    @pytest.fixture
    def reformulator(self):
        """Create a reformulator instance."""
        return QueryReformulator()
    
    def test_extract_topic_about_pattern(self, reformulator):
        """Should extract topic after 'about'."""
        exchange = {"question": "Tell me about your database experience", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "database" in topic.lower()
    
    def test_extract_topic_describe_pattern(self, reformulator):
        """Should extract topic after 'describe'."""
        exchange = {"question": "Describe your leadership style", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "leadership" in topic.lower()
    
    def test_extract_topic_explain_pattern(self, reformulator):
        """Should extract topic after 'explain'."""
        exchange = {"question": "Explain your approach to testing", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "testing" in topic.lower() or "approach" in topic.lower()
    
    def test_extract_topic_fallback(self, reformulator):
        """Should fallback to 'your previous response' if no pattern matches."""
        exchange = {"question": "What?", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "previous" in topic.lower() or "response" in topic.lower()
    
    def test_extract_topic_empty_history(self, reformulator):
        """Should handle empty exchange gracefully."""
        exchange = {}
        topic = reformulator._extract_topic(exchange)
        
        assert topic  # Should return something, not crash


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def reformulator(self):
        """Create a reformulator instance."""
        return QueryReformulator()
    
    def test_empty_question(self, reformulator):
        """Empty question should return empty."""
        result, was_reformulated = reformulator.reformulate_if_needed("", [])
        
        assert result == ""
        assert not was_reformulated
    
    def test_whitespace_question(self, reformulator):
        """Whitespace-only question should handle gracefully."""
        result, was_reformulated = reformulator.reformulate_if_needed("   ", [])
        
        assert not was_reformulated
    
    def test_none_history(self, reformulator):
        """None history should be treated as empty."""
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What about X?",
            None
        )
        
        # Should handle gracefully without crashing
        assert result is not None
    
    def test_malformed_history_entry(self, reformulator):
        """Should handle malformed history entries."""
        history = [
            {"wrong_key": "value"},  # Missing 'question' key
            {"question": "Valid question", "answer": "Valid answer"}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Can you elaborate?",
            history
        )
        
        # Should not crash
        assert result is not None
    
    def test_case_insensitive_detection(self, reformulator):
        """Follow-up detection should be case insensitive."""
        history = [{"question": "Q", "answer": "A"}]
        
        assert reformulator._is_follow_up("WHAT ABOUT Python?")
        assert reformulator._is_follow_up("CAN YOU ELABORATE?")
        assert reformulator._is_follow_up("TELL ME MORE")
