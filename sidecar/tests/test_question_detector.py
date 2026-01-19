"""
Tests for QuestionDetector (Tier 1 - Rule-Based).

Tests the pattern matching logic for classifying interview utterances
as questions vs statements with <2ms latency requirement.
"""

import time
import pytest
from typing import List, Dict

# Will be implemented in STORY-034
from src.classification.question_detector import QuestionDetector


class TestQuestionDetectorBasic:
    """Basic functionality tests for QuestionDetector."""

    @pytest.fixture
    def detector(self) -> QuestionDetector:
        """Create a fresh detector instance for each test."""
        return QuestionDetector()

    # =========================================================================
    # INTERVIEW QUESTIONS - Should return (True, high_confidence, type)
    # =========================================================================

    def test_wh_question_with_question_mark(self, detector: QuestionDetector):
        """WH-questions with ? should be detected with high confidence."""
        text = "What is your experience with Python?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.90
        assert classification == "interview_question"

    def test_how_question(self, detector: QuestionDetector):
        """How questions should be detected."""
        text = "How do you handle tight deadlines?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_why_question(self, detector: QuestionDetector):
        """Why questions should be detected."""
        text = "Why did you leave your last job?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_tell_me_about_pattern(self, detector: QuestionDetector):
        """Behavioral question starters should be detected."""
        text = "Tell me about a time you faced a challenge"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.90
        assert classification == "interview_question"

    def test_describe_pattern(self, detector: QuestionDetector):
        """Describe pattern should be detected."""
        text = "Describe your experience with distributed systems"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_explain_pattern(self, detector: QuestionDetector):
        """Explain pattern should be detected."""
        text = "Explain how you would design a scalable API"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_walk_me_through_pattern(self, detector: QuestionDetector):
        """Walk me through pattern should be detected."""
        text = "Walk me through your background"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.90
        assert classification == "interview_question"

    def test_can_you_pattern(self, detector: QuestionDetector):
        """Can you + action verb should be detected."""
        text = "Can you tell me about your leadership experience?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_have_you_ever_pattern(self, detector: QuestionDetector):
        """Have you ever pattern should be detected."""
        text = "Have you ever had to deal with a difficult team member?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "interview_question"

    def test_give_me_an_example_pattern(self, detector: QuestionDetector):
        """Give me an example pattern should be detected."""
        text = "Give me an example of when you showed initiative"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.90
        assert classification == "interview_question"

    # =========================================================================
    # STATEMENTS - Should return (False, high_confidence, type)
    # =========================================================================

    def test_interviewer_statement_let_me(self, detector: QuestionDetector):
        """Interviewer statements starting with 'let me' should not be questions."""
        text = "Let me tell you about the role"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.85
        assert classification == "statement"

    def test_interviewer_statement_so_basically(self, detector: QuestionDetector):
        """Summary statements should not be questions."""
        text = "So basically what you're saying is you prefer agile"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.80
        assert classification == "statement"

    def test_interviewer_statement_moving_on(self, detector: QuestionDetector):
        """Transition statements should not be questions."""
        text = "Moving on to the next topic"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.85
        assert classification == "statement"

    def test_interviewer_statement_next(self, detector: QuestionDetector):
        """'Next' statements should not be questions."""
        text = "Next, I want to discuss your technical skills"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.80
        assert classification == "statement"

    # =========================================================================
    # ACKNOWLEDGMENTS - Should return (False, high_confidence, "acknowledgment")
    # =========================================================================

    def test_acknowledgment_okay(self, detector: QuestionDetector):
        """Simple acknowledgments should be detected."""
        text = "Okay, that makes sense"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.90
        assert classification == "acknowledgment"

    def test_acknowledgment_great(self, detector: QuestionDetector):
        """Positive acknowledgments should be detected."""
        text = "Great, thanks for sharing that"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.85
        assert classification == "acknowledgment"

    def test_acknowledgment_i_see(self, detector: QuestionDetector):
        """Understanding acknowledgments should be detected."""
        text = "I see, that's interesting"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.90
        assert classification == "acknowledgment"

    def test_acknowledgment_got_it(self, detector: QuestionDetector):
        """Informal acknowledgments should be detected."""
        text = "Got it, that's helpful"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.90
        assert classification == "acknowledgment"

    def test_acknowledgment_makes_sense(self, detector: QuestionDetector):
        """'Makes sense' acknowledgments should be detected."""
        text = "Makes sense"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.90
        assert classification == "acknowledgment"

    def test_acknowledgment_thats_good(self, detector: QuestionDetector):
        """'That's good' acknowledgments should be detected."""
        text = "That's good to hear"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.85
        assert classification == "acknowledgment"

    # =========================================================================
    # SMALL TALK - Should return (False, medium_confidence, "small_talk")
    # =========================================================================

    def test_small_talk_thanks(self, detector: QuestionDetector):
        """Thank you statements should be small talk."""
        text = "Thanks for coming in today"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence >= 0.85
        assert classification == "small_talk"

    def test_small_talk_weather(self, detector: QuestionDetector):
        """Weather-related small talk should be detected."""
        text = "Nice weather we're having"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        # Lower confidence for ambiguous small talk
        assert classification == "small_talk"

    def test_small_talk_how_was_commute(self, detector: QuestionDetector):
        """Commute questions are small talk, not interview questions."""
        text = "How was your commute today?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert classification == "small_talk"

    # =========================================================================
    # FOLLOW-UP QUESTIONS - Should be classified as "follow_up"
    # =========================================================================

    def test_follow_up_what_about(self, detector: QuestionDetector):
        """'What about' is a follow-up question."""
        text = "What about testing?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        # Follow-ups ARE questions, but need context
        assert is_question is True
        assert classification == "follow_up"

    def test_follow_up_can_you_elaborate(self, detector: QuestionDetector):
        """'Can you elaborate' is a follow-up question."""
        text = "Can you elaborate on that?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "follow_up"

    def test_follow_up_and_what_happened(self, detector: QuestionDetector):
        """'And what happened' is a follow-up question."""
        text = "And what happened next?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "follow_up"

    def test_follow_up_tell_me_more(self, detector: QuestionDetector):
        """'Tell me more' is a follow-up question."""
        text = "Tell me more about that"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "follow_up"

    # =========================================================================
    # CLARIFICATION REQUESTS - Should be classified as "clarification"
    # =========================================================================

    def test_clarification_what_do_you_mean(self, detector: QuestionDetector):
        """'What do you mean' is a clarification request."""
        text = "What do you mean by that?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "clarification"

    def test_clarification_could_you_repeat(self, detector: QuestionDetector):
        """'Could you repeat' is a clarification request."""
        text = "Could you repeat the question?"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "clarification"

    def test_clarification_sorry_didnt_catch(self, detector: QuestionDetector):
        """'Didn't catch that' is a clarification request."""
        text = "Sorry, I didn't catch that"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        # Not a question, but a clarification signal
        assert classification == "clarification"

    # =========================================================================
    # AMBIGUOUS CASES - Should return lower confidence
    # =========================================================================

    def test_ambiguous_interesting_background(self, detector: QuestionDetector):
        """Ambiguous statements should have low confidence."""
        text = "Interesting background"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence < 0.70  # Low confidence - ambiguous
        assert classification == "statement"

    def test_ambiguous_single_word(self, detector: QuestionDetector):
        """Single words should have low confidence."""
        text = "Python"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence < 0.70

    def test_ambiguous_hmm(self, detector: QuestionDetector):
        """Filler sounds should have low confidence."""
        text = "Hmm"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence < 0.60

    # =========================================================================
    # EDGE CASES
    # =========================================================================

    def test_empty_string(self, detector: QuestionDetector):
        """Empty string should return False with low confidence."""
        text = ""
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence < 0.50

    def test_whitespace_only(self, detector: QuestionDetector):
        """Whitespace-only string should return False."""
        text = "   \n\t  "
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False
        assert confidence < 0.50

    def test_none_input(self, detector: QuestionDetector):
        """None input should be handled gracefully."""
        is_question, confidence, classification = detector.is_actionable_question(None)
        
        assert is_question is False
        assert confidence < 0.50

    def test_case_insensitivity(self, detector: QuestionDetector):
        """Pattern matching should be case insensitive."""
        text = "TELL ME ABOUT YOUR EXPERIENCE"
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert classification == "interview_question"

    def test_leading_trailing_whitespace(self, detector: QuestionDetector):
        """Leading/trailing whitespace should be handled."""
        text = "  What is your biggest strength?  "
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True
        assert confidence >= 0.85


class TestQuestionDetectorPerformance:
    """Performance tests for QuestionDetector - must meet <2ms P99 requirement."""

    @pytest.fixture
    def detector(self) -> QuestionDetector:
        """Create detector instance."""
        return QuestionDetector()

    def test_latency_under_2ms_simple(self, detector: QuestionDetector):
        """Simple question classification should be <2ms."""
        text = "What is your experience with Python?"
        
        # Warm up
        detector.is_actionable_question(text)
        
        # Measure
        start = time.perf_counter()
        detector.is_actionable_question(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 2.0, f"Latency {elapsed_ms:.3f}ms exceeds 2ms limit"

    def test_latency_under_2ms_long_text(self, detector: QuestionDetector):
        """Long text classification should still be <2ms."""
        text = """Tell me about a time when you had to lead a cross-functional team 
        through a challenging project with tight deadlines and multiple stakeholders 
        with conflicting priorities and how you managed to deliver successful results."""
        
        # Warm up
        detector.is_actionable_question(text)
        
        # Measure
        start = time.perf_counter()
        detector.is_actionable_question(text)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 2.0, f"Latency {elapsed_ms:.3f}ms exceeds 2ms limit"

    def test_latency_p99_under_2ms(self, detector: QuestionDetector):
        """P99 latency across 100 calls should be <2ms."""
        test_texts = [
            "What is your experience with Python?",
            "Tell me about yourself",
            "Okay, that makes sense",
            "How do you handle conflict?",
            "Thanks for sharing",
            "Walk me through your background",
            "Let me explain the role",
            "Why are you interested in this position?",
            "Great, moving on",
            "Have you ever led a team?",
        ]
        
        # Warm up
        for text in test_texts:
            detector.is_actionable_question(text)
        
        # Measure 100 iterations
        latencies = []
        for _ in range(100):
            for text in test_texts:
                start = time.perf_counter()
                detector.is_actionable_question(text)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)
        
        # Calculate P99
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        
        assert p99_latency < 2.0, f"P99 latency {p99_latency:.3f}ms exceeds 2ms limit"


class TestQuestionDetectorWithHistory:
    """Tests for context-aware classification using conversation history."""

    @pytest.fixture
    def detector(self) -> QuestionDetector:
        """Create detector instance."""
        return QuestionDetector()

    def test_no_history_provided(self, detector: QuestionDetector):
        """Detector should work without history."""
        text = "What is your experience?"
        is_question, confidence, classification = detector.is_actionable_question(text, None)
        
        assert is_question is True

    def test_empty_history(self, detector: QuestionDetector):
        """Empty history should work same as no history."""
        text = "What is your experience?"
        is_question, confidence, classification = detector.is_actionable_question(text, [])
        
        assert is_question is True

    def test_history_passed_but_not_used_in_tier1(self, detector: QuestionDetector):
        """Tier 1 doesn't use history, but should accept it for interface compatibility."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your background"},
            {"speaker": "Candidate", "text": "I have 5 years of experience..."},
        ]
        text = "What else?"
        
        # Should work without error, even though Tier 1 doesn't use history
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        # This is a follow-up
        assert is_question is True
        assert classification == "follow_up"


class TestPatternCoverage:
    """Tests to ensure all documented patterns work correctly."""

    @pytest.fixture
    def detector(self) -> QuestionDetector:
        return QuestionDetector()

    # Interview question patterns from story spec
    @pytest.mark.parametrize("text,expected_type", [
        ("Tell me about your experience", "interview_question"),
        ("Describe a situation where you...", "interview_question"),
        ("Explain how you would approach...", "interview_question"),
        ("What is your biggest strength?", "interview_question"),
        ("What are your career goals?", "interview_question"),
        ("What was your role?", "interview_question"),
        ("What were you responsible for?", "interview_question"),
        ("What do you know about our company?", "interview_question"),
        ("What did you learn from that?", "interview_question"),
        ("What would you do differently?", "interview_question"),
        ("What have you accomplished?", "interview_question"),
        ("How do you prioritize tasks?", "interview_question"),
        ("How did you handle that situation?", "interview_question"),
        ("How would you approach this problem?", "interview_question"),
        ("How have you grown as a professional?", "interview_question"),
        ("How can you contribute to our team?", "interview_question"),
        ("How could you improve this process?", "interview_question"),
        ("Why do you want to work here?", "interview_question"),
        ("Why did you choose this career?", "interview_question"),
        ("Why would you be a good fit?", "interview_question"),
        ("Why have you stayed in this field?", "interview_question"),
        ("Can you tell me about a time...?", "interview_question"),
        ("Can you describe your experience?", "interview_question"),
        ("Can you explain your approach?", "interview_question"),
        ("Can you walk me through your process?", "interview_question"),
        ("Walk me through your resume", "interview_question"),
        ("Give me an example of leadership", "interview_question"),
        ("Have you ever managed a team?", "interview_question"),
        ("Have you had experience with...?", "interview_question"),
    ])
    def test_interview_question_patterns(self, detector: QuestionDetector, text: str, expected_type: str):
        """Test all documented interview question patterns."""
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is True, f"'{text}' should be detected as a question"
        assert classification == expected_type, f"'{text}' should be '{expected_type}', got '{classification}'"

    # Statement patterns from story spec
    @pytest.mark.parametrize("text,expected_type", [
        ("Okay, let's move on", "acknowledgment"),
        ("Ok, I understand", "acknowledgment"),
        ("Alright, that's clear", "acknowledgment"),
        ("Sure, that makes sense", "acknowledgment"),
        ("Great answer", "acknowledgment"),
        ("Perfect, thank you", "acknowledgment"),
        ("Excellent point", "acknowledgment"),
        ("Good to know", "acknowledgment"),
        ("Nice background", "acknowledgment"),
        ("Thank you for sharing", "small_talk"),
        ("Thanks for that explanation", "small_talk"),
        ("I see what you mean", "acknowledgment"),
        ("I understand your point", "acknowledgment"),
        ("Got it", "acknowledgment"),
        ("Makes sense to me", "acknowledgment"),
        ("Let me explain the next steps", "statement"),
        ("Let's talk about compensation", "statement"),
        ("We'll be in touch soon", "statement"),
        ("We will send you the details", "statement"),
        ("That's a great point", "acknowledgment"),
        ("That is very helpful", "acknowledgment"),
        ("Moving on to technical questions", "statement"),
        ("Next we'll discuss your skills", "statement"),
        ("Now let's talk about the project", "statement"),
        ("So basically you're saying...", "statement"),
        ("In other words, you prefer...", "statement"),
    ])
    def test_statement_patterns(self, detector: QuestionDetector, text: str, expected_type: str):
        """Test all documented statement patterns."""
        is_question, confidence, classification = detector.is_actionable_question(text)
        
        assert is_question is False, f"'{text}' should NOT be detected as a question"
        assert classification == expected_type, f"'{text}' should be '{expected_type}', got '{classification}'"


class TestQuestionDetectorInstantiation:
    """Tests for QuestionDetector initialization."""

    def test_instantiation(self):
        """Detector should instantiate without errors."""
        detector = QuestionDetector()
        assert detector is not None

    def test_patterns_compiled(self):
        """Patterns should be pre-compiled for performance."""
        detector = QuestionDetector()
        # Should have compiled patterns (implementation detail)
        assert hasattr(detector, '_compiled_patterns') or hasattr(detector, '_interview_patterns')

    def test_multiple_instances_independent(self):
        """Multiple detector instances should be independent."""
        detector1 = QuestionDetector()
        detector2 = QuestionDetector()
        
        result1 = detector1.is_actionable_question("What is your experience?")
        result2 = detector2.is_actionable_question("What is your experience?")
        
        assert result1 == result2


# =============================================================================
# TIER 2 - CONTEXT-AWARE CLASSIFICATION TESTS (STORY-035)
# =============================================================================

class TestContextAwareClassification:
    """Tests for Tier 2 context-aware classification using conversation history."""

    @pytest.fixture
    def detector(self) -> QuestionDetector:
        """Create detector instance."""
        return QuestionDetector()

    # =========================================================================
    # FOLLOW-UP DETECTION WITH HISTORY
    # =========================================================================

    def test_follow_up_after_answer(self, detector: QuestionDetector):
        """Follow-up question after candidate's answer should be detected."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your experience with React"},
            {"speaker": "Candidate", "text": "I've used React for 3 years, primarily building SPAs..."},
        ]
        text = "What about testing?"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
        assert confidence >= 0.80
        assert classification == "follow_up"

    def test_elaboration_request_after_answer(self, detector: QuestionDetector):
        """Elaboration request after candidate's answer should be follow-up."""
        history = [
            {"speaker": "Interviewer", "text": "Describe a challenging situation"},
            {"speaker": "Candidate", "text": "We had a tight deadline and the requirements changed..."},
        ]
        text = "Can you elaborate on that?"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
        assert confidence >= 0.85
        assert classification == "follow_up"

    def test_tell_me_more_after_answer(self, detector: QuestionDetector):
        """'Tell me more' after candidate's answer should be follow-up."""
        history = [
            {"speaker": "Interviewer", "text": "How do you handle conflict?"},
            {"speaker": "Candidate", "text": "I try to understand both perspectives first..."},
        ]
        text = "Tell me more about that approach"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
        assert classification == "follow_up"

    def test_pronoun_reference_after_answer(self, detector: QuestionDetector):
        """Questions with pronoun references should be detected as follow-ups."""
        history = [
            {"speaker": "Interviewer", "text": "What technologies did you use?"},
            {"speaker": "Candidate", "text": "We used Python, Django, and PostgreSQL..."},
        ]
        text = "Why did you choose that?"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        # This should be recognized as a question (has "why did")
        assert is_question is True
        # Could be interview_question or follow_up - both are valid

    def test_and_what_after_answer(self, detector: QuestionDetector):
        """'And what...' after answer should be follow-up."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your last project"},
            {"speaker": "Candidate", "text": "I led the development of a real-time dashboard..."},
        ]
        text = "And what was the outcome?"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
        assert classification == "follow_up"

    # =========================================================================
    # ACKNOWLEDGMENT WITH CONTEXT
    # =========================================================================

    def test_acknowledgment_after_candidate_answer(self, detector: QuestionDetector):
        """Acknowledgment after candidate's answer should be detected."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about yourself"},
            {"speaker": "Candidate", "text": "I'm a software engineer with 5 years of experience..."},
        ]
        text = "That's great, thanks for sharing"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is False
        # Could be acknowledgment or small_talk - both indicate non-question

    def test_okay_after_answer(self, detector: QuestionDetector):
        """'Okay' after candidate's answer is acknowledgment."""
        history = [
            {"speaker": "Interviewer", "text": "What's your biggest weakness?"},
            {"speaker": "Candidate", "text": "I sometimes focus too much on details..."},
        ]
        text = "Okay, I understand"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is False
        assert classification == "acknowledgment"

    # =========================================================================
    # TOPIC TRANSITIONS
    # =========================================================================

    def test_topic_transition_with_new_question(self, detector: QuestionDetector):
        """Topic transition followed by new question - the question wins because it's actionable."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your experience"},
            {"speaker": "Candidate", "text": "I've worked in fintech for 3 years..."},
        ]
        text = "Moving on, tell me about your technical skills"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        # "tell me about your..." is an actionable question even after a transition phrase
        # The interviewer is asking the candidate to share information
        # This is the CORRECT behavior for interview coaching
        assert is_question is True
        assert classification == "interview_question"

    def test_next_question_transition(self, detector: QuestionDetector):
        """'Next question' pattern should be detected appropriately."""
        history = [
            {"speaker": "Interviewer", "text": "Describe your leadership style"},
            {"speaker": "Candidate", "text": "I believe in servant leadership..."},
        ]
        text = "Next, let's discuss your technical background"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        # This is a statement/transition
        assert is_question is False

    # =========================================================================
    # AMBIGUOUS CASES RESOLVED BY CONTEXT
    # =========================================================================

    def test_ambiguous_resolved_by_context(self, detector: QuestionDetector):
        """Ambiguous text should be classified using context when needed."""
        history = [
            {"speaker": "Interviewer", "text": "What's your experience with databases?"},
            {"speaker": "Candidate", "text": "I've worked extensively with PostgreSQL and MongoDB..."},
        ]
        text = "Interesting"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        # After a candidate's answer, "Interesting" is acknowledgment
        assert is_question is False

    def test_hmm_after_answer_is_acknowledgment(self, detector: QuestionDetector):
        """Filler sounds after answer are acknowledgments, not requiring response."""
        history = [
            {"speaker": "Interviewer", "text": "Why should we hire you?"},
            {"speaker": "Candidate", "text": "I bring unique skills and experience..."},
        ]
        text = "Hmm"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is False

    # =========================================================================
    # PERFORMANCE WITH HISTORY
    # =========================================================================

    def test_latency_with_history_under_10ms(self, detector: QuestionDetector):
        """Classification with history should be <10ms."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your experience with Python"},
            {"speaker": "Candidate", "text": "I've used Python for 5 years..."},
            {"speaker": "Interviewer", "text": "What projects have you worked on?"},
            {"speaker": "Candidate", "text": "I built a real-time data pipeline..."},
        ]
        text = "Can you elaborate on the data pipeline?"
        
        # Warm up
        detector.is_actionable_question(text, history)
        
        # Measure
        start = time.perf_counter()
        detector.is_actionable_question(text, history)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 10.0, f"Context-aware latency {elapsed_ms:.3f}ms exceeds 10ms limit"

    def test_latency_p99_with_history_under_10ms(self, detector: QuestionDetector):
        """P99 latency with history should be <10ms."""
        history = [
            {"speaker": "Interviewer", "text": "Tell me about your experience"},
            {"speaker": "Candidate", "text": "I have 5 years of experience..."},
            {"speaker": "Interviewer", "text": "What technologies do you use?"},
            {"speaker": "Candidate", "text": "Python, TypeScript, React..."},
            {"speaker": "Interviewer", "text": "Describe a challenging project"},
            {"speaker": "Candidate", "text": "We had to rebuild the entire system..."},
        ]
        
        test_texts = [
            "What about testing?",
            "Can you elaborate?",
            "Okay, that makes sense",
            "Tell me more",
            "And then what happened?",
        ]
        
        # Warm up
        for text in test_texts:
            detector.is_actionable_question(text, history)
        
        # Measure
        latencies = []
        for _ in range(100):
            for text in test_texts:
                start = time.perf_counter()
                detector.is_actionable_question(text, history)
                elapsed_ms = (time.perf_counter() - start) * 1000
                latencies.append(elapsed_ms)
        
        latencies.sort()
        p99_latency = latencies[int(len(latencies) * 0.99)]
        
        assert p99_latency < 10.0, f"P99 latency {p99_latency:.3f}ms exceeds 10ms limit"

    # =========================================================================
    # HISTORY EDGE CASES
    # =========================================================================

    def test_very_long_history_still_performant(self, detector: QuestionDetector):
        """Long history should not degrade performance beyond 10ms."""
        # Create a long history (20 turns)
        history = []
        for i in range(10):
            history.append({"speaker": "Interviewer", "text": f"Question {i} about your experience?"})
            history.append({"speaker": "Candidate", "text": f"Answer {i} with detailed explanation..."})
        
        text = "Can you elaborate on that last point?"
        
        start = time.perf_counter()
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        elapsed_ms = (time.perf_counter() - start) * 1000
        
        assert elapsed_ms < 10.0, f"Long history latency {elapsed_ms:.3f}ms exceeds 10ms limit"
        assert is_question is True

    def test_history_with_only_interviewer_turns(self, detector: QuestionDetector):
        """History with only interviewer turns should still work."""
        history = [
            {"speaker": "Interviewer", "text": "Welcome to the interview"},
            {"speaker": "Interviewer", "text": "Let me tell you about the company"},
        ]
        # Use a clearer interview question that starts with recognized pattern
        text = "Tell me about yourself"
        
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
        assert classification == "interview_question"

    def test_history_with_missing_speaker_field(self, detector: QuestionDetector):
        """History with missing speaker field should be handled gracefully."""
        history = [
            {"text": "Tell me about your experience"},
            {"speaker": "Candidate", "text": "I've been working..."},
        ]
        text = "What about Python?"
        
        # Should not crash
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True

    def test_history_with_missing_text_field(self, detector: QuestionDetector):
        """History with missing text field should be handled gracefully."""
        history = [
            {"speaker": "Interviewer"},
            {"speaker": "Candidate", "text": "I've been working..."},
        ]
        text = "What about testing?"
        
        # Should not crash
        is_question, confidence, classification = detector.is_actionable_question(text, history)
        
        assert is_question is True
