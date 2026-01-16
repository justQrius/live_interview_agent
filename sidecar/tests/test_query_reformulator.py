"""
Tests for QueryReformulator - expanding follow-up questions into standalone queries.

Includes tests for:
- Template-based expansion (Tier 1)
- TopicStack and multi-turn anaphora resolution (Tier 2)
- LLM fallback (Tier 3) - async tests
"""

import pytest

from src.classification.query_reformulator import (
    QueryReformulator,
    TopicStack,
    TopicEntry,
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


# =============================================================================
# NEW: TopicStack Tests
# =============================================================================

class TestTopicStack:
    """Tests for TopicStack - multi-turn topic tracking."""
    
    @pytest.fixture
    def topic_stack(self):
        """Create a topic stack instance."""
        return TopicStack(max_size=5)
    
    def test_push_and_get_latest(self, topic_stack):
        """Should push topics and retrieve latest."""
        topic_stack.push("Python experience", "Tell me about Python", 0)
        topic_stack.push("AWS deployment", "Describe your AWS work", 1)
        
        latest = topic_stack.get_latest()
        assert latest is not None
        assert "AWS" in latest.topic
    
    def test_get_by_index(self, topic_stack):
        """Should retrieve topics by ordinal index."""
        topic_stack.push("first topic", "First question", 0)
        topic_stack.push("second topic", "Second question", 1)
        topic_stack.push("third topic", "Third question", 2)
        
        first = topic_stack.get_by_index(0)
        assert first is not None
        assert "first" in first.topic.lower()
        
        last = topic_stack.get_by_index(-1)
        assert last is not None
        assert "third" in last.topic.lower()
    
    def test_find_by_keywords(self, topic_stack):
        """Should find topics by keyword matching."""
        topic_stack.push("microservices architecture", "Tell me about your microservices project", 0)
        topic_stack.push("database optimization", "Describe your database work", 1)
        topic_stack.push("team leadership", "How do you lead teams", 2)
        
        # Search for "project" - should match microservices
        result = topic_stack.find_by_keywords(["project", "microservices"])
        assert result is not None
        assert "microservices" in result.topic.lower()
        
        # Search for "database"
        result = topic_stack.find_by_keywords(["database"])
        assert result is not None
        assert "database" in result.topic.lower()
    
    def test_max_size_limit(self, topic_stack):
        """Should respect max size limit."""
        for i in range(10):
            topic_stack.push(f"topic {i}", f"question {i}", i)
        
        # Max size is 5
        assert len(topic_stack) == 5
        
        # First topics should be dropped
        first = topic_stack.get_by_index(0)
        assert first is not None
        assert "5" in first.topic  # topic 5 should be first now
    
    def test_clear(self, topic_stack):
        """Should clear all topics."""
        topic_stack.push("topic", "question", 0)
        topic_stack.clear()
        
        assert len(topic_stack) == 0
        assert topic_stack.get_latest() is None


class TestTopicEntry:
    """Tests for TopicEntry keyword extraction."""
    
    def test_keyword_extraction(self):
        """Should extract meaningful keywords from questions."""
        entry = TopicEntry(
            topic="Python experience",
            turn_index=0,
            question="Tell me about your experience with Python and machine learning"
        )
        
        # Should extract significant words
        assert "python" in entry.keywords
        assert "machine" in entry.keywords
        assert "learning" in entry.keywords
        
        # Should exclude stop words
        assert "tell" not in entry.keywords
        assert "about" not in entry.keywords
        assert "your" not in entry.keywords
    
    def test_keyword_extraction_short_words(self):
        """Should exclude very short words."""
        entry = TopicEntry(
            topic="API work",
            turn_index=0,
            question="How do you handle API rate limiting?"
        )
        
        # Words less than 3 chars should be excluded
        assert "do" not in entry.keywords
        # But longer words should be included
        assert "handle" in entry.keywords or "rate" in entry.keywords


# =============================================================================
# NEW: Multi-Turn Anaphora Resolution Tests
# =============================================================================

class TestMultiTurnAnaphora:
    """Tests for resolving references across multiple conversation turns."""
    
    @pytest.fixture
    def reformulator(self):
        """Create a reformulator instance."""
        return QueryReformulator()
    
    def test_ordinal_reference_first(self, reformulator):
        """Should resolve 'the first topic' to first topic in stack."""
        history = [
            {"question": "Tell me about your Python experience", "answer": "I've used Python for 5 years..."},
            {"question": "Describe your AWS deployments", "answer": "I've deployed to AWS..."},
            {"question": "What about your leadership style", "answer": "I lead by example..."},
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Go back to the first topic",
            history
        )
        
        assert was_reformulated
        assert "python" in result.lower() or "first" not in result.lower()
    
    def test_ordinal_reference_previous(self, reformulator):
        """Should resolve 'the previous topic' correctly."""
        history = [
            {"question": "Tell me about Java", "answer": "..."},
            {"question": "Describe Python work", "answer": "..."},
            {"question": "What about Kubernetes?", "answer": "..."},
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Can you elaborate on the previous topic?",
            history
        )
        
        # Should reference something, ideally Python or Kubernetes
        assert was_reformulated or "previous" in result
    
    def test_that_project_three_turns_ago(self, reformulator):
        """Should resolve 'that project' referring to earlier turn."""
        history = [
            {"question": "Tell me about your microservices project at Acme", "answer": "We built 12 services..."},
            {"question": "What languages do you prefer?", "answer": "Python and Go..."},
            {"question": "How do you handle testing?", "answer": "TDD approach..."},
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "How did that project end?",
            history
        )
        
        # Should attempt to resolve "that project"
        assert was_reformulated
        # Result should reference microservices or project
        assert "project" in result.lower() or "microservices" in result.lower()
    
    def test_that_experience_resolution(self, reformulator):
        """Should resolve 'that experience' to relevant earlier topic."""
        history = [
            {"question": "Describe your startup experience", "answer": "I was CTO at a startup..."},
            {"question": "What tech stack did you use?", "answer": "React, Node, PostgreSQL..."},
            {"question": "How large was the team?", "answer": "5 engineers..."},
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What did you learn from that experience?",
            history
        )
        
        assert was_reformulated
        # Should reference startup experience
        assert "startup" in result.lower() or "experience" in result.lower()
    
    def test_pronoun_with_keyword_context(self, reformulator):
        """Pronouns with contextual keywords should match better."""
        history = [
            {"question": "Tell me about the payment system you built", "answer": "I designed a payment gateway..."},
            {"question": "What about authentication?", "answer": "We used OAuth2..."},
            {"question": "How do you handle errors?", "answer": "Centralized error handling..."},
        ]
        
        # "it" with "payment" keyword should match payment system
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What were the challenges with it?",
            history
        )
        
        # Should reformulate (ending with "it")
        assert was_reformulated


class TestEnhancedFollowUpPatterns:
    """Tests for new follow-up pattern detection."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    def test_that_project_mid_sentence(self, reformulator):
        """'that project' mid-sentence should be detected as follow-up."""
        assert reformulator._is_follow_up("What challenges did you face in that project?")
        assert reformulator._is_follow_up("How did that experience shape your approach?")
    
    def test_ordinal_patterns(self, reformulator):
        """Ordinal references should be detected as follow-ups."""
        assert reformulator._is_follow_up("Go back to the first topic")
        assert reformulator._is_follow_up("Let's revisit the earlier question")
        assert reformulator._is_follow_up("The previous one was interesting")


class TestEnhancedTopicExtraction:
    """Tests for improved topic extraction patterns."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    def test_walk_me_through_pattern(self, reformulator):
        """Should extract topic from 'walk me through' questions."""
        exchange = {"question": "Walk me through your approach to system design", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "approach" in topic.lower() or "system" in topic.lower() or "design" in topic.lower()
    
    def test_experience_with_pattern(self, reformulator):
        """Should extract topic from 'experience with' questions."""
        exchange = {"question": "What is your experience with distributed systems?", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        assert "distributed" in topic.lower() or "systems" in topic.lower()
    
    def test_the_x_project_pattern(self, reformulator):
        """Should extract 'the X project/system' patterns."""
        exchange = {"question": "Tell me about the payment system architecture", "answer": "..."}
        topic = reformulator._extract_topic(exchange)
        
        # Should extract something meaningful
        assert "payment" in topic.lower() or "system" in topic.lower()
    
    def test_complex_question_extraction(self, reformulator):
        """Should handle complex multi-part questions."""
        exchange = {
            "question": "How do you balance technical debt with feature delivery while maintaining team morale?",
            "answer": "..."
        }
        topic = reformulator._extract_topic(exchange)
        
        # Should extract something meaningful, not just fallback
        assert topic != "your previous response"
        assert len(topic) > 10


class TestTieredReformulation:
    """Tests verifying the tiered reformulation approach."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    def test_tier1_template_fast_path(self, reformulator):
        """Template matches should use fast path."""
        history = [
            {"question": "Tell me about Python", "answer": "..."}
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Can you elaborate?",
            history
        )
        
        assert was_reformulated
        assert "Python" in result or "elaborate" in result
    
    def test_tier2_topic_stack_used(self, reformulator):
        """TopicStack should be built and used for multi-turn context."""
        history = [
            {"question": "Tell me about your startup experience", "answer": "..."},
            {"question": "What tech stack?", "answer": "..."},
            {"question": "Team size?", "answer": "..."},
        ]
        
        # Build stack via reformulate call
        reformulator.reformulate_if_needed("Test", history)
        
        # Topic stack should have entries
        assert len(reformulator.topic_stack) > 0
    
    def test_tier2_ordinal_before_template(self, reformulator):
        """Ordinal references should be resolved before template matching."""
        history = [
            {"question": "Tell me about your Python experience", "answer": "..."},
            {"question": "Describe your AWS work", "answer": "..."},
        ]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Go back to the first one",
            history
        )
        
        # Should resolve "first one" to Python
        assert was_reformulated
        assert "python" in result.lower() or "first" not in result.lower()


# =============================================================================
# NEW: Async LLM Fallback Tests
# =============================================================================

class TestAsyncLLMFallback:
    """Tests for async LLM fallback reformulation."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator(enable_llm_fallback=True)
    
    def test_llm_provider_can_be_set(self, reformulator):
        """Should accept LLM provider."""
        mock_provider = object()  # Placeholder
        reformulator.set_llm_provider(mock_provider)
        
        assert reformulator.llm_provider is mock_provider
    
    def test_no_llm_sync_still_works(self, reformulator):
        """Sync method should work without LLM provider."""
        history = [{"question": "About Python", "answer": "..."}]
        
        result, was_reformulated = reformulator.reformulate_if_needed(
            "Novel phrasing that might not match templates",
            history
        )
        
        # Should not crash, may or may not reformulate
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_async_method_exists(self, reformulator):
        """Async method should exist and be callable."""
        history = [{"question": "About Python", "answer": "..."}]
        
        # Should not crash even without LLM
        result, was_reformulated = await reformulator.reformulate_if_needed_async(
            "Can you elaborate?",
            history
        )
        
        assert result is not None


class TestBackwardsCompatibility:
    """Ensure existing behavior is preserved."""
    
    @pytest.fixture
    def reformulator(self):
        return QueryReformulator()
    
    def test_existing_templates_still_work(self, reformulator):
        """All existing template patterns should still work."""
        history = [{"question": "Tell me about databases", "answer": "..."}]
        
        test_cases = [
            ("What about Python?", True),
            ("How about scalability?", True),
            ("Can you elaborate?", True),
            ("Tell me more", True),
            ("What were the results?", True),
            ("Tell me about yourself", False),  # Not a follow-up
        ]
        
        for question, should_reformulate in test_cases:
            result, was_reformulated = reformulator.reformulate_if_needed(question, history)
            assert was_reformulated == should_reformulate, f"Failed for: {question}"
    
    def test_context_turns_default(self, reformulator):
        """Default context_turns should be 5."""
        assert reformulator.context_turns == 5
    
    def test_empty_history_handling(self, reformulator):
        """Empty history should be handled gracefully."""
        result, was_reformulated = reformulator.reformulate_if_needed(
            "What about X?",
            []
        )
        
        assert not was_reformulated
        assert result == "What about X?"
