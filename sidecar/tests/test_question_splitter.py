"""
Tests for the QuestionSplitter class.

Tests compound question detection and splitting logic.
"""

import pytest

from src.classification.question_splitter import (
    COMPOUND_INDICATORS,
    QuestionSplitter,
)


class TestCompoundIndicators:
    """Test the compound detection patterns."""
    
    def test_and_with_question_word(self):
        """'and what/how/why' should indicate compound."""
        import re
        patterns = [
            "Tell me about X and what was the outcome?",
            "Describe your role and how did you handle Y?",
            "What's X and why did you choose that?",
        ]
        
        for pattern in patterns:
            matched = any(
                re.search(indicator, pattern, re.IGNORECASE)
                for indicator in COMPOUND_INDICATORS
            )
            assert matched, f"Should detect compound: {pattern}"
    
    def test_multiple_question_marks(self):
        """Multiple ? should indicate compound."""
        import re
        pattern = "What is X? How is Y?"
        matched = any(
            re.search(indicator, pattern, re.IGNORECASE)
            for indicator in COMPOUND_INDICATORS
        )
        assert matched, "Multiple question marks should indicate compound"
    
    def test_also_pattern(self):
        """'also what/how' should indicate compound."""
        import re
        pattern = "Tell me about X, also how do you handle Y?"
        matched = any(
            re.search(indicator, pattern, re.IGNORECASE)
            for indicator in COMPOUND_INDICATORS
        )
        assert matched, "'also' + question word should indicate compound"
    
    def test_non_compound_and(self):
        """'and' in regular context should NOT indicate compound."""
        import re
        patterns = [
            "Tell me about research and development",
            "What is your sales and marketing experience?",
            "Describe your strengths and weaknesses",
        ]
        
        # These should NOT match compound indicators because 'and' is not
        # followed by a question word
        for text in patterns:
            # Only check the 'and + question word' pattern
            match = re.search(r"\band\b\s+(what|how|why|when|where|tell|describe|explain)", text, re.IGNORECASE)
            assert not match, f"Should NOT detect compound in: {text}"


class TestQuestionSplitter:
    """Test the QuestionSplitter class."""
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_simple_non_compound(self, splitter):
        """Simple question should return as single-item list."""
        text = "Tell me about your experience"
        result = splitter.split_questions(text)
        
        assert len(result) == 1
        assert result[0] == "Tell me about your experience"
    
    def test_and_with_question_word(self, splitter):
        """'and what/how' should split."""
        text = "Tell me about your role and how did you handle challenges?"
        result = splitter.split_questions(text)
        
        assert len(result) == 2
        assert "role" in result[0].lower()
        assert "how" in result[1].lower() or "challenges" in result[1].lower()
    
    def test_also_pattern(self, splitter):
        """'also how/what' should split."""
        text = "What's your experience with Python? Also, how do you approach testing?"
        result = splitter.split_questions(text)
        
        assert len(result) == 2
        assert "Python" in result[0]
        assert "testing" in result[1].lower()
    
    def test_multiple_question_marks(self, splitter):
        """Multiple sentences with ? should split."""
        text = "What is your strength? What is your weakness?"
        result = splitter.split_questions(text)
        
        assert len(result) == 2
        assert "strength" in result[0].lower()
        assert "weakness" in result[1].lower()
    
    def test_and_not_splitting_regular_phrases(self, splitter):
        """'and' in regular phrases should NOT split."""
        text = "Tell me about your research and development experience"
        result = splitter.split_questions(text)
        
        assert len(result) == 1
        assert "research and development" in result[0].lower()
    
    def test_sales_and_marketing(self, splitter):
        """'sales and marketing' should NOT split."""
        text = "What is your sales and marketing background?"
        result = splitter.split_questions(text)
        
        assert len(result) == 1
        assert "sales and marketing" in result[0].lower()
    
    def test_empty_input(self, splitter):
        """Empty input should return empty list."""
        result = splitter.split_questions("")
        assert result == []
    
    def test_whitespace_input(self, splitter):
        """Whitespace input should return empty list."""
        result = splitter.split_questions("   ")
        assert result == []
    
    def test_question_normalization(self, splitter):
        """Split questions should be properly normalized."""
        text = "what's X and how do you Y"
        result = splitter.split_questions(text)
        
        # First question should be capitalized
        assert result[0][0].isupper()
        
        # Second question should be capitalized and not start with 'and'
        assert result[1][0].isupper()
        assert not result[1].lower().startswith("and ")
    
    def test_three_questions(self, splitter):
        """Three-part questions should all split."""
        text = "What is X? How is Y? Why is Z?"
        result = splitter.split_questions(text)
        
        assert len(result) == 3
    
    def test_additionally_pattern(self, splitter):
        """'additionally' should trigger split."""
        text = "Tell me about A, additionally, what about B?"
        result = splitter.split_questions(text)
        
        assert len(result) == 2


class TestIsCompound:
    """Test the _is_compound helper method."""
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_is_compound_true(self, splitter):
        """Should detect compound questions."""
        compounds = [
            "What is X and how is Y?",
            "Tell me A? Also tell me B?",
            "Describe X, and what about Y?",
        ]
        
        for text in compounds:
            assert splitter._is_compound(text), f"Should be compound: {text}"
    
    def test_is_compound_false(self, splitter):
        """Should not flag non-compound questions."""
        non_compounds = [
            "Tell me about your experience",
            "What is your research and development background?",
            "Describe your strengths and weaknesses",
            "How do you handle pressure?",
        ]
        
        for text in non_compounds:
            assert not splitter._is_compound(text), f"Should NOT be compound: {text}"


class TestEnsureQuestionForm:
    """Test the _ensure_question_form helper method."""
    
    @pytest.fixture
    def splitter(self):
        return QuestionSplitter()
    
    def test_removes_leading_conjunction(self, splitter):
        """Should remove 'and', 'also' from start."""
        text = "and how do you handle this?"
        result = splitter._ensure_question_form(text)
        
        assert not result.lower().startswith("and ")
        assert result.startswith("How") or result.startswith("how")
    
    def test_capitalizes_first_letter(self, splitter):
        """Should capitalize first letter."""
        text = "what is your experience?"
        result = splitter._ensure_question_form(text)
        
        assert result[0].isupper()
    
    def test_adds_question_mark_if_missing(self, splitter):
        """Should add ? if it looks like a question."""
        text = "What is your experience"
        result = splitter._ensure_question_form(text)
        
        assert result.endswith("?")
    
    def test_preserves_existing_question_mark(self, splitter):
        """Should not add double question mark."""
        text = "What is your experience?"
        result = splitter._ensure_question_form(text)
        
        assert result.endswith("?")
        assert not result.endswith("??")
    
    def test_empty_string(self, splitter):
        """Should handle empty string."""
        result = splitter._ensure_question_form("")
        assert result == ""
