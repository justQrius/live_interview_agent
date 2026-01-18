"""
Tests for QuestionGenerator (STORY-059).

Tests cover:
- Question count requirements (20+ minimum)
- Category distribution
- JD grounding
- Deduplication
- Seniority adaptation
- Gap targeting
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
import json

from src.playbook import QuestionGenerator, PlaybookQuestion, QuestionCategory
from src.playbook.question_generator import (
    QuestionDifficulty,
    AnswerFramework,
    SeniorityLevel,
    CATEGORY_COUNTS,
)
from src.memory.models import (
    ExtractedFacts,
    CandidateProfile,
    DocumentSummary,
    DocumentType,
    SkillEntry,
)


class TestPlaybookQuestion:
    
    def test_question_creation(self):
        q = PlaybookQuestion(
            question_text="Tell me about a time you led a team.",
            category=QuestionCategory.BEHAVIORAL,
            why_likely="Tests leadership skills.",
            jd_requirement="Leadership experience",
        )
        
        assert q.question_text == "Tell me about a time you led a team."
        assert q.category == QuestionCategory.BEHAVIORAL
        assert q.id is not None
    
    def test_question_to_dict(self):
        q = PlaybookQuestion(
            question_text="Test question",
            category=QuestionCategory.TECHNICAL,
            difficulty=QuestionDifficulty.CHALLENGING,
        )
        
        data = q.to_dict()
        
        assert data["question_text"] == "Test question"
        assert data["category"] == "technical"
        assert data["difficulty"] == "challenging"
    
    def test_question_from_dict(self):
        data = {
            "question_text": "Why this company?",
            "category": "motivation",
            "difficulty": "standard",
            "answer_framework": "Passion-Fit",
        }
        
        q = PlaybookQuestion.from_dict(data)
        
        assert q.question_text == "Why this company?"
        assert q.category == QuestionCategory.MOTIVATION
        assert q.answer_framework == AnswerFramework.PASSION_FIT


class TestQuestionGeneratorBasic:
    
    def test_init(self):
        generator = QuestionGenerator()
        assert generator.llm_provider is None
        assert generator.memory_store is None
    
    def test_init_with_providers(self):
        mock_llm = MagicMock()
        mock_store = MagicMock()
        
        generator = QuestionGenerator(
            llm_provider=mock_llm,
            memory_store=mock_store
        )
        
        assert generator.llm_provider == mock_llm
        assert generator.memory_store == mock_store
    
    def test_set_providers(self):
        generator = QuestionGenerator()
        mock_llm = MagicMock()
        mock_store = MagicMock()
        
        generator.set_llm_provider(mock_llm)
        generator.set_memory_store(mock_store)
        
        assert generator.llm_provider == mock_llm
        assert generator.memory_store == mock_store


class TestTemplateBasedGeneration:
    
    @pytest.fixture
    def sample_profile(self):
        return CandidateProfile(
            current_role="Senior Engineer",
            total_experience_years=8,
            core_skills=["Python", "AWS", "Kubernetes"],
            strengths=["Technical leadership", "System design"],
            gaps=["Machine learning experience"],
        )
    
    @pytest.fixture
    def sample_facts(self):
        return ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8),
                SkillEntry(name="AWS", years=5),
                SkillEntry(name="Kubernetes", years=3),
                SkillEntry(name="PostgreSQL", years=5),
            ],
            total_experience_years=8,
            current_role="Senior Engineer",
        )
    
    @pytest.fixture
    def sample_jd_summary(self):
        return DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            filename="job.pdf",
            document_summary="Senior Software Engineer role at tech company",
            key_points=[
                "5+ years Python experience",
                "Leadership and mentoring skills",
                "Experience with cloud platforms (AWS/GCP)",
                "Strong problem-solving abilities",
                "Excellent communication skills",
            ],
        )
    
    @pytest.mark.asyncio
    async def test_generate_minimum_questions(self, sample_profile, sample_facts, sample_jd_summary):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            profile=sample_profile,
            facts=sample_facts,
            jd_summary=sample_jd_summary,
        )
        
        assert len(questions) >= generator.MIN_QUESTIONS
    
    @pytest.mark.asyncio
    async def test_generate_without_context(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate()
        
        assert len(questions) >= generator.MIN_QUESTIONS
    
    @pytest.mark.asyncio
    async def test_category_distribution(self, sample_profile, sample_facts, sample_jd_summary):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            profile=sample_profile,
            facts=sample_facts,
            jd_summary=sample_jd_summary,
        )
        
        by_category = {}
        for q in questions:
            cat = q.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        assert by_category.get("behavioral", 0) >= 1
        assert by_category.get("technical", 0) >= 1
        assert by_category.get("motivation", 0) >= 1
    
    @pytest.mark.asyncio
    async def test_no_duplicate_questions(self, sample_profile, sample_facts, sample_jd_summary):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            profile=sample_profile,
            facts=sample_facts,
            jd_summary=sample_jd_summary,
        )
        
        question_texts = [q.question_text.lower().strip() for q in questions]
        unique_texts = set(question_texts)
        
        assert len(question_texts) == len(unique_texts)
    
    @pytest.mark.asyncio
    async def test_questions_have_metadata(self, sample_profile, sample_facts, sample_jd_summary):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            profile=sample_profile,
            facts=sample_facts,
            jd_summary=sample_jd_summary,
        )
        
        for q in questions:
            assert q.question_text
            assert q.category
            assert q.difficulty
            assert q.answer_framework


class TestSeniorityAdaptation:
    
    @pytest.mark.asyncio
    async def test_junior_questions(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            role_level=SeniorityLevel.JUNIOR
        )
        
        situational = [q for q in questions if q.category == QuestionCategory.SITUATIONAL]
        
        for q in situational:
            assert "junior" in q.tags or "situational" in q.tags
    
    @pytest.mark.asyncio
    async def test_senior_questions(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            role_level=SeniorityLevel.SENIOR
        )
        
        situational = [q for q in questions if q.category == QuestionCategory.SITUATIONAL]
        
        assert len(situational) > 0
    
    @pytest.mark.asyncio
    async def test_manager_questions(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            role_level=SeniorityLevel.MANAGER
        )
        
        situational = [q for q in questions if q.category == QuestionCategory.SITUATIONAL]
        
        for q in situational:
            assert "manager" in q.tags or "situational" in q.tags


class TestGapTargeting:
    
    @pytest.mark.asyncio
    async def test_curveball_targets_gaps(self):
        profile = CandidateProfile(
            current_role="Engineer",
            gaps=["Machine learning", "Distributed systems"],
        )
        
        generator = QuestionGenerator()
        
        questions = await generator.generate(profile=profile)
        
        curveballs = [q for q in questions if q.category == QuestionCategory.CURVEBALL]
        
        assert len(curveballs) >= 2
        
        gap_related = [
            q for q in curveballs 
            if any(gap.lower() in q.question_text.lower() or gap in q.jd_requirement 
                   for gap in profile.gaps)
        ]
        assert len(gap_related) >= 1
    
    @pytest.mark.asyncio
    async def test_curveball_without_gaps(self):
        profile = CandidateProfile(
            current_role="Engineer",
            gaps=[],
        )
        
        generator = QuestionGenerator()
        
        questions = await generator.generate(profile=profile)
        
        curveballs = [q for q in questions if q.category == QuestionCategory.CURVEBALL]
        
        assert len(curveballs) >= 2


class TestLLMGeneration:
    
    @pytest.fixture
    def mock_llm_response(self):
        return json.dumps([
            {
                "question_text": "Tell me about a time you led a complex migration project.",
                "category": "behavioral",
                "why_likely": "Tests technical leadership and project management.",
                "jd_requirement": "5+ years experience",
                "difficulty": "challenging",
                "answer_framework": "STAR",
                "tags": ["leadership", "technical"]
            },
            {
                "question_text": "How would you design a distributed cache system?",
                "category": "technical",
                "why_likely": "Tests system design skills.",
                "jd_requirement": "System design",
                "difficulty": "challenging",
                "answer_framework": "Concept-Example",
                "tags": ["technical", "design"]
            },
            {
                "question_text": "Why are you interested in our company?",
                "category": "motivation",
                "why_likely": "Assesses cultural fit.",
                "jd_requirement": "Cultural fit",
                "difficulty": "standard",
                "answer_framework": "Passion-Fit",
                "tags": ["motivation"]
            },
        ])
    
    @pytest.mark.asyncio
    async def test_llm_generation(self, mock_llm_response):
        mock_llm = MagicMock()
        
        async def mock_generate(*args, **kwargs):
            yield mock_llm_response
        
        mock_llm.generate_response = mock_generate
        
        generator = QuestionGenerator(llm_provider=mock_llm)
        
        questions = await generator.generate()
        
        llm_questions = [q for q in questions if "migration" in q.question_text.lower() or "cache" in q.question_text.lower()]
        assert len(llm_questions) >= 1
    
    @pytest.mark.asyncio
    async def test_llm_fallback_on_error(self):
        mock_llm = MagicMock()
        
        async def mock_generate(*args, **kwargs):
            raise Exception("LLM error")
            yield ""
        
        mock_llm.generate_response = mock_generate
        
        generator = QuestionGenerator(llm_provider=mock_llm)
        
        questions = await generator.generate()
        
        assert len(questions) >= generator.MIN_QUESTIONS


class TestQuestionStats:
    
    @pytest.mark.asyncio
    async def test_get_question_stats(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate()
        
        stats = generator.get_question_stats(questions)
        
        assert stats["total"] >= generator.MIN_QUESTIONS
        assert "by_category" in stats
        assert "by_difficulty" in stats
    
    @pytest.mark.asyncio
    async def test_get_questions_by_category(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate()
        
        behavioral = generator.get_questions_by_category(
            questions, QuestionCategory.BEHAVIORAL
        )
        
        assert all(q.category == QuestionCategory.BEHAVIORAL for q in behavioral)


class TestCompetencyExtraction:
    
    def test_extract_competencies_from_jd(self):
        jd_summary = DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=[
                "Strong leadership skills required",
                "Problem-solving abilities",
                "Experience mentoring junior engineers",
                "Excellent communication",
            ],
        )
        
        generator = QuestionGenerator()
        competencies = generator._extract_competencies(jd_summary)
        
        assert len(competencies) > 0
        assert any("led" in c or "leadership" in c for c in competencies)
    
    def test_extract_competencies_fallback(self):
        generator = QuestionGenerator()
        competencies = generator._extract_competencies(None)
        
        assert len(competencies) >= 8


class TestTechnologyExtraction:
    
    def test_extract_technologies(self):
        facts = ExtractedFacts(
            skills=[
                SkillEntry(name="Python"),
                SkillEntry(name="React"),
                SkillEntry(name="AWS"),
            ]
        )
        
        jd_summary = DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["Experience with Kubernetes and Docker required"],
        )
        
        generator = QuestionGenerator()
        technologies = generator._extract_technologies(facts, jd_summary)
        
        assert "Python" in technologies
        assert "React" in technologies
        assert "AWS" in technologies


class TestAnswerFramework:
    
    def test_infer_framework_behavioral(self):
        generator = QuestionGenerator()
        framework = generator._infer_framework(QuestionCategory.BEHAVIORAL)
        assert framework == AnswerFramework.STAR
    
    def test_infer_framework_technical(self):
        generator = QuestionGenerator()
        framework = generator._infer_framework(QuestionCategory.TECHNICAL)
        assert framework == AnswerFramework.CONCEPT_EXAMPLE
    
    def test_infer_framework_motivation(self):
        generator = QuestionGenerator()
        framework = generator._infer_framework(QuestionCategory.MOTIVATION)
        assert framework == AnswerFramework.PASSION_FIT


class TestEdgeCases:
    
    @pytest.mark.asyncio
    async def test_empty_profile(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            profile=CandidateProfile()
        )
        
        assert len(questions) >= generator.MIN_QUESTIONS
    
    @pytest.mark.asyncio
    async def test_empty_facts(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate(
            facts=ExtractedFacts()
        )
        
        assert len(questions) >= generator.MIN_QUESTIONS
    
    @pytest.mark.asyncio
    async def test_max_questions_cap(self):
        generator = QuestionGenerator()
        
        questions = await generator.generate()
        
        assert len(questions) <= generator.MAX_QUESTIONS
