"""
Tests for PlaybookAssembler - STORY-062.

Tests playbook assembly, positioning statements, cheat sheet generation,
and export formats (Markdown, JSON, HTML).
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.playbook.assembler import (
    PlaybookAssembler,
    Playbook,
    PositioningStatements,
    CheatSheet,
)
from src.playbook.question_generator import (
    PlaybookQuestion,
    QuestionCategory,
    AnswerFramework,
    QuestionDifficulty,
)
from src.playbook.competency_mapper import (
    CompetencyReport,
    CompetencyMapping,
    MatchStrength,
    RequirementType,
)
from src.memory.models import (
    CandidateProfile,
    STARStory,
    DraftedAnswer,
    DocumentSummary,
    DocumentType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_profile():
    """Sample candidate profile for testing."""
    return CandidateProfile(
        id="profile-1",
        profile_text="Experienced software engineer with 8 years in backend development.",
        current_role="Senior Software Engineer",
        total_experience_years=8,
        core_skills=["Python", "AWS", "Kubernetes", "PostgreSQL"],
        key_achievements=[
            "Reduced API latency by 40% serving 10M requests/day",
            "Led team of 5 engineers on $2M platform rebuild",
            "Designed event-driven architecture processing 500K events/sec",
        ],
        target_role="Staff Engineer",
        target_company="TechCorp",
        strengths=["Technical leadership", "System design", "Performance optimization"],
        gaps=["Machine learning", "Mobile development"],
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_questions():
    """Sample playbook questions."""
    return [
        PlaybookQuestion(
            id="q1",
            question_text="Tell me about a time you led a technical project.",
            category=QuestionCategory.BEHAVIORAL,
            why_likely="Tests leadership ability required for Staff role.",
            jd_requirement="Technical leadership",
            difficulty=QuestionDifficulty.STANDARD,
            answer_framework=AnswerFramework.STAR,
            tags=["leadership", "technical"],
        ),
        PlaybookQuestion(
            id="q2",
            question_text="How would you design a distributed caching system?",
            category=QuestionCategory.TECHNICAL,
            why_likely="Tests system design skills.",
            jd_requirement="System design",
            difficulty=QuestionDifficulty.CHALLENGING,
            answer_framework=AnswerFramework.CONCEPT_EXAMPLE,
            tags=["system_design", "distributed_systems"],
        ),
        PlaybookQuestion(
            id="q3",
            question_text="Why are you interested in this role?",
            category=QuestionCategory.MOTIVATION,
            why_likely="Standard motivation question.",
            jd_requirement="Cultural fit",
            difficulty=QuestionDifficulty.STANDARD,
            answer_framework=AnswerFramework.PASSION_FIT,
            tags=["motivation", "culture"],
        ),
    ]


@pytest.fixture
def sample_answers():
    """Sample drafted answers."""
    return [
        DraftedAnswer(
            id="a1",
            question_id="q1",
            suggested_answer="In my role as Senior Engineer, I led the platform rebuild project...",
            key_points=["Led team of 5", "Delivered on time", "40% latency reduction"],
            opening_line="Let me tell you about the platform rebuild project.",
            framework_used="STAR",
            word_count=150,
            estimated_duration_seconds=60,
            confidence=0.85,
        ),
        DraftedAnswer(
            id="a2",
            question_id="q2",
            suggested_answer="A distributed caching system needs to balance consistency...",
            key_points=["Cache invalidation strategy", "Consistency models", "Scaling approach"],
            framework_used="Concept-Example",
            word_count=180,
            confidence=0.75,
        ),
    ]


@pytest.fixture
def sample_competency_report():
    """Sample competency report."""
    return CompetencyReport(
        mappings=[
            CompetencyMapping(
                requirement="5+ years Python experience",
                requirement_type=RequirementType.TECHNICAL_SKILL,
                is_required=True,
                evidence="8 years Python experience",
                metrics=["8 years"],
                match_strength=MatchStrength.STRONG,
            ),
            CompetencyMapping(
                requirement="AWS certifications",
                requirement_type=RequirementType.CERTIFICATION,
                is_required=False,
                evidence=None,
                match_strength=MatchStrength.GAP,
                mitigation="Mention extensive hands-on AWS experience",
            ),
            CompetencyMapping(
                requirement="Leadership experience",
                requirement_type=RequirementType.SOFT_SKILL,
                is_required=True,
                evidence="Led team of 5 engineers",
                match_strength=MatchStrength.STRONG,
            ),
        ],
        total_requirements=3,
        strong_matches=2,
        moderate_matches=0,
        weak_matches=0,
        gaps=1,
        critical_gaps=[],
        generated_at=datetime.now(),
    )


@pytest.fixture
def sample_stories():
    """Sample STAR stories."""
    return [
        STARStory(
            id="story1",
            title="The Platform Rebuild",
            situation="Our legacy platform was causing performance issues.",
            task="Lead the rebuild effort with a team of 5.",
            action="Designed new architecture, implemented incrementally.",
            result="Reduced latency by 40%, improved reliability to 99.9%.",
            metrics=["40% latency reduction", "99.9% uptime"],
            tags=["leadership", "technical", "scale"],
            source_company="Previous Corp",
            confidence=0.9,
        ),
        STARStory(
            id="story2",
            title="Event System Migration",
            situation="Needed to migrate to event-driven architecture.",
            task="Design and implement new event processing system.",
            action="Implemented Kafka-based solution with careful testing.",
            result="Now processing 500K events/sec with zero downtime.",
            metrics=["500K events/sec", "zero downtime"],
            tags=["technical", "architecture", "migration"],
            source_company="Previous Corp",
            confidence=0.85,
        ),
    ]


@pytest.fixture
def sample_jd_summary():
    """Sample job description summary."""
    return DocumentSummary(
        document_id="jd-1",
        document_type=DocumentType.JOB_DESCRIPTION,
        filename="staff_engineer_jd.pdf",
        document_summary="Staff Engineer role focusing on technical leadership.",
        key_points=[
            "5+ years Python experience required",
            "System design expertise",
            "Technical leadership",
            "AWS experience preferred",
        ],
    )


# ============================================================================
# PositioningStatements Tests
# ============================================================================

class TestPositioningStatements:
    """Tests for PositioningStatements dataclass."""
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        positioning = PositioningStatements(
            pitch_20s="I'm a senior engineer with 8 years experience.",
            pitch_60s="Extended pitch with more details.",
            pitch_2min="Full pitch with complete story.",
        )
        
        data = positioning.to_dict()
        
        assert data["pitch_20s"] == "I'm a senior engineer with 8 years experience."
        assert "pitch_60s" in data
        assert "pitch_2min" in data
    
    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "pitch_20s": "Short pitch",
            "pitch_60s": "Medium pitch",
            "pitch_2min": "Long pitch",
        }
        
        positioning = PositioningStatements.from_dict(data)
        
        assert positioning.pitch_20s == "Short pitch"
        assert positioning.pitch_60s == "Medium pitch"
        assert positioning.pitch_2min == "Long pitch"


# ============================================================================
# CheatSheet Tests
# ============================================================================

class TestCheatSheet:
    """Tests for CheatSheet dataclass."""
    
    def test_to_dict(self):
        """Test serialization."""
        sheet = CheatSheet(
            key_talking_points=["Point 1", "Point 2"],
            top_stories=[{"title": "Story 1", "one_liner": "Quick summary"}],
            top_metrics=["40% reduction"],
            questions_to_ask=["What's the team like?"],
            pitfalls_to_avoid=["Don't oversell"],
        )
        
        data = sheet.to_dict()
        
        assert len(data["key_talking_points"]) == 2
        assert len(data["top_stories"]) == 1
        assert data["top_metrics"][0] == "40% reduction"
    
    def test_to_markdown(self):
        """Test markdown export."""
        sheet = CheatSheet(
            key_talking_points=["Point 1", "Point 2"],
            top_stories=[{"title": "Story 1", "one_liner": "Quick summary"}],
            top_metrics=["40% reduction"],
            questions_to_ask=["What's the team like?"],
            pitfalls_to_avoid=["Don't oversell"],
        )
        
        markdown = sheet.to_markdown()
        
        assert "# Interview Cheat Sheet" in markdown
        assert "## Key Talking Points" in markdown
        assert "- Point 1" in markdown
        assert "**Story 1**" in markdown
        assert "40% reduction" in markdown
        assert "⚠️ Don't oversell" in markdown
    
    def test_to_markdown_empty_sections(self):
        """Test markdown with empty sections doesn't crash."""
        sheet = CheatSheet()
        
        markdown = sheet.to_markdown()
        
        assert "# Interview Cheat Sheet" in markdown
        assert "## Key Talking Points" in markdown


# ============================================================================
# Playbook Tests
# ============================================================================

class TestPlaybook:
    """Tests for Playbook dataclass."""
    
    def test_to_dict(self, sample_questions, sample_answers, sample_profile):
        """Test full serialization."""
        playbook = Playbook(
            id="playbook-1",
            title="Interview Playbook: Staff Engineer at TechCorp",
            role="Staff Engineer",
            company="TechCorp",
            generated_at=datetime.now(),
            positioning=PositioningStatements(pitch_20s="Test"),
            questions=sample_questions,
            answers={a.question_id: a for a in sample_answers},
            profile=sample_profile,
            questions_to_ask=["Question 1?"],
            total_questions=3,
            coverage_score=0.85,
        )
        
        data = playbook.to_dict()
        
        assert data["id"] == "playbook-1"
        assert data["role"] == "Staff Engineer"
        assert data["company"] == "TechCorp"
        assert data["total_questions"] == 3
        assert data["coverage_score"] == 0.85
        assert len(data["questions"]) == 3
        assert len(data["answers"]) == 2
    
    def test_to_json(self, sample_questions, sample_profile):
        """Test JSON export."""
        playbook = Playbook(
            id="playbook-1",
            title="Test Playbook",
            role="Engineer",
            company="TestCo",
            questions=sample_questions,
            profile=sample_profile,
        )
        
        json_str = playbook.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["id"] == "playbook-1"
        assert parsed["title"] == "Test Playbook"
    
    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "id": "pb-1",
            "title": "Test",
            "role": "Engineer",
            "company": "TestCo",
            "generated_at": "2025-01-10T12:00:00",
            "questions": [],
            "answers": {},
            "questions_to_ask": ["Q1?"],
            "total_questions": 0,
            "coverage_score": 0.5,
        }
        
        playbook = Playbook.from_dict(data)
        
        assert playbook.id == "pb-1"
        assert playbook.role == "Engineer"
        assert playbook.coverage_score == 0.5


# ============================================================================
# PlaybookAssembler Tests - Template Mode
# ============================================================================

class TestPlaybookAssemblerTemplate:
    """Tests for PlaybookAssembler without LLM (template mode)."""
    
    @pytest.fixture
    def assembler(self):
        """Create assembler without LLM."""
        return PlaybookAssembler(llm_provider=None)
    
    @pytest.mark.asyncio
    async def test_assemble_minimal(self, assembler, sample_questions, sample_answers):
        """Test assembly with minimal inputs."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
        )
        
        assert playbook.id != ""
        assert playbook.generated_at is not None
        assert len(playbook.questions) == 3
        assert len(playbook.answers) == 2
    
    @pytest.mark.asyncio
    async def test_assemble_full(
        self, assembler, sample_questions, sample_answers,
        sample_competency_report, sample_stories, sample_profile, sample_jd_summary
    ):
        """Test full assembly with all components."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            competency_report=sample_competency_report,
            stories=sample_stories,
            profile=sample_profile,
            jd_summary=sample_jd_summary,
            role="Staff Engineer",
            company="TechCorp",
        )
        
        assert playbook.title == "Interview Playbook: Staff Engineer at TechCorp"
        assert playbook.role == "Staff Engineer"
        assert playbook.company == "TechCorp"
        assert playbook.total_questions == 3
        assert playbook.total_stories == 2
        assert playbook.positioning is not None
        assert playbook.cheat_sheet is not None
        assert len(playbook.questions_to_ask) >= 5
    
    @pytest.mark.asyncio
    async def test_assemble_infers_role_from_profile(
        self, assembler, sample_questions, sample_answers, sample_profile
    ):
        """Test that role/company are inferred from profile if not provided."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
        )
        
        assert "Staff Engineer" in playbook.title
        assert "TechCorp" in playbook.title
    
    @pytest.mark.asyncio
    async def test_positioning_generated(
        self, assembler, sample_questions, sample_answers, sample_profile
    ):
        """Test positioning statements are generated."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
            role="Staff Engineer",
            company="TechCorp",
        )
        
        assert playbook.positioning is not None
        assert len(playbook.positioning.pitch_20s) > 0
        assert len(playbook.positioning.pitch_60s) > 0
        assert len(playbook.positioning.pitch_2min) > 0
        assert "Staff Engineer" in playbook.positioning.pitch_20s or "8 years" in playbook.positioning.pitch_20s
    
    @pytest.mark.asyncio
    async def test_cheat_sheet_generated(
        self, assembler, sample_questions, sample_answers, sample_profile,
        sample_stories, sample_competency_report
    ):
        """Test cheat sheet is generated with all sections."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
            stories=sample_stories,
            competency_report=sample_competency_report,
        )
        
        sheet = playbook.cheat_sheet
        assert sheet is not None
        assert len(sheet.key_talking_points) > 0
        assert len(sheet.top_stories) > 0
        assert len(sheet.top_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_questions_to_ask_generated(
        self, assembler, sample_questions, sample_answers
    ):
        """Test questions for interviewer are generated."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            role="Engineer",
            company="TestCo",
        )
        
        assert len(playbook.questions_to_ask) >= 5
        assert any("success" in q.lower() or "team" in q.lower() for q in playbook.questions_to_ask)
    
    @pytest.mark.asyncio
    async def test_coverage_score_calculation(
        self, assembler, sample_questions, sample_answers, sample_competency_report
    ):
        """Test coverage score is calculated correctly."""
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            competency_report=sample_competency_report,
        )
        
        # 2 strong (required) + 1 gap (not required)
        # Strong required = 1.0 * 1.5 = 1.5 each, gap not required = 0 * 1.0 = 0
        # Score = (1.5 + 1.5) / (1.5 + 1.0 + 1.5) = 3.0 / 4.0 = 0.75
        assert 0.7 <= playbook.coverage_score <= 0.8


# ============================================================================
# PlaybookAssembler Tests - LLM Mode
# ============================================================================

class TestPlaybookAssemblerLLM:
    """Tests for PlaybookAssembler with mocked LLM."""
    
    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM provider."""
        mock = MagicMock()
        return mock
    
    @pytest.fixture
    def assembler_with_llm(self, mock_llm):
        """Create assembler with mocked LLM."""
        return PlaybookAssembler(llm_provider=mock_llm)
    
    @pytest.mark.asyncio
    async def test_positioning_with_llm(
        self, assembler_with_llm, mock_llm, sample_questions, sample_answers, sample_profile
    ):
        """Test positioning generation with LLM."""
        async def mock_generator(*args, **kwargs):
            yield '{"pitch_20s": "LLM pitch 20s", "pitch_60s": "LLM pitch 60s", "pitch_2min": "LLM pitch 2min"}'
        
        mock_llm.generate_response = mock_generator
        
        playbook = await assembler_with_llm.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
            role="Staff Engineer",
            company="TechCorp",
        )
        
        assert playbook.positioning.pitch_20s == "LLM pitch 20s"
        assert playbook.positioning.pitch_60s == "LLM pitch 60s"
    
    @pytest.mark.asyncio
    async def test_questions_to_ask_with_llm(
        self, assembler_with_llm, mock_llm, sample_questions, sample_answers
    ):
        """Test questions-to-ask generation with LLM."""
        async def mock_generator(*args, **kwargs):
            yield '["What is the team structure?", "How do you measure success?"]'
        
        mock_llm.generate_response = mock_generator
        
        playbook = await assembler_with_llm.assemble(
            questions=sample_questions,
            answers=sample_answers,
            role="Engineer",
            company="TestCo",
        )
        
        assert "What is the team structure?" in playbook.questions_to_ask
    
    @pytest.mark.asyncio
    async def test_llm_failure_fallback(
        self, assembler_with_llm, mock_llm, sample_questions, sample_answers, sample_profile
    ):
        """Test fallback to templates when LLM fails."""
        async def mock_generator(*args, **kwargs):
            raise Exception("LLM API error")
            yield ""  # Make it a generator
        
        mock_llm.generate_response = mock_generator
        
        # Should not raise, should fallback to templates
        playbook = await assembler_with_llm.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
            role="Engineer",
            company="TestCo",
        )
        
        assert playbook.positioning is not None
        assert len(playbook.questions_to_ask) >= 5


# ============================================================================
# Export Tests
# ============================================================================

class TestPlaybookExport:
    """Tests for playbook export formats."""
    
    @pytest.fixture
    def assembler(self):
        return PlaybookAssembler()
    
    @pytest.fixture
    def full_playbook(self, sample_questions, sample_answers, sample_profile, sample_stories, sample_competency_report):
        """Create a full playbook for export testing."""
        return Playbook(
            id="pb-1",
            title="Interview Playbook: Staff Engineer at TechCorp",
            role="Staff Engineer",
            company="TechCorp",
            generated_at=datetime.now(),
            positioning=PositioningStatements(
                pitch_20s="I'm a senior engineer with 8 years experience.",
                pitch_60s="Extended pitch with achievements.",
                pitch_2min="Full story of my career journey.",
            ),
            competency_report=sample_competency_report,
            questions=sample_questions,
            answers={a.question_id: a for a in sample_answers},
            stories=sample_stories,
            profile=sample_profile,
            questions_to_ask=["What's the team like?", "How do you measure success?"],
            cheat_sheet=CheatSheet(
                key_talking_points=["8 years experience", "Led platform rebuild"],
                top_stories=[{"title": "Platform Rebuild", "one_liner": "40% latency reduction"}],
                top_metrics=["40% reduction", "99.9% uptime"],
                questions_to_ask=["What's the team like?"],
                pitfalls_to_avoid=["Don't oversell ML experience"],
            ),
            total_questions=3,
            total_stories=2,
            coverage_score=0.85,
        )
    
    def test_export_markdown(self, assembler, full_playbook):
        """Test Markdown export contains all sections."""
        markdown = assembler.export_markdown(full_playbook)
        
        # Title and metadata
        assert "# Interview Playbook: Staff Engineer at TechCorp" in markdown
        
        # Positioning
        assert "## Executive Summary" in markdown
        assert "20-Second Pitch" in markdown
        assert "I'm a senior engineer" in markdown
        
        # Competency mapping
        assert "## Competency Mapping" in markdown
        assert "Coverage Score" in markdown
        
        # Question bank
        assert "## Question Bank" in markdown
        assert "Behavioral Questions" in markdown
        assert "Tell me about a time" in markdown
        
        # Stories
        assert "## STAR Story Bank" in markdown
        assert "Platform Rebuild" in markdown
        
        # Gap analysis
        assert "## Gap Analysis" in markdown
        
        # Questions to ask
        assert "## Questions to Ask" in markdown
        
        # Cheat sheet
        assert "# Interview Cheat Sheet" in markdown
    
    def test_export_markdown_empty_sections(self, assembler):
        """Test Markdown export handles empty playbook gracefully."""
        playbook = Playbook(
            id="pb-empty",
            title="Empty Playbook",
            role="Engineer",
            company="TestCo",
            generated_at=datetime.now(),
        )
        
        markdown = assembler.export_markdown(playbook)
        
        assert "# Empty Playbook" in markdown
        assert "## Question Bank" in markdown
    
    def test_export_json(self, assembler, full_playbook):
        """Test JSON export is valid and complete."""
        json_str = assembler.export_json(full_playbook)
        
        data = json.loads(json_str)
        
        assert data["id"] == "pb-1"
        assert data["role"] == "Staff Engineer"
        assert len(data["questions"]) == 3
        assert data["positioning"]["pitch_20s"] == "I'm a senior engineer with 8 years experience."
    
    def test_export_html(self, assembler, full_playbook):
        """Test HTML export is valid."""
        html = assembler.export_html(full_playbook)
        
        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "<title>Interview Playbook: Staff Engineer at TechCorp</title>" in html
        assert "font-family" in html  # Has styles
        assert "@media print" in html  # Has print styles
        
        # Content should be present
        assert "Executive Summary" in html
        assert "Question Bank" in html


# ============================================================================
# Integration Tests
# ============================================================================

class TestAssemblerIntegration:
    """Integration tests for the full assembly flow."""
    
    @pytest.mark.asyncio
    async def test_full_assembly_and_export_cycle(
        self, sample_questions, sample_answers, sample_profile,
        sample_stories, sample_competency_report, sample_jd_summary
    ):
        """Test complete assembly and all export formats."""
        assembler = PlaybookAssembler()
        
        # Assemble
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            competency_report=sample_competency_report,
            stories=sample_stories,
            profile=sample_profile,
            jd_summary=sample_jd_summary,
            role="Staff Engineer",
            company="TechCorp",
        )
        
        # Export to all formats
        markdown = assembler.export_markdown(playbook)
        json_str = assembler.export_json(playbook)
        html = assembler.export_html(playbook)
        
        # Verify all exports are non-empty
        assert len(markdown) > 1000
        assert len(json_str) > 500
        assert len(html) > 1000
        
        # Verify JSON can be parsed and re-loaded
        data = json.loads(json_str)
        reloaded = Playbook.from_dict(data)
        assert reloaded.id == playbook.id
        assert reloaded.role == playbook.role
    
    @pytest.mark.asyncio
    async def test_cheat_sheet_fits_one_page(
        self, sample_questions, sample_answers, sample_profile,
        sample_stories, sample_competency_report
    ):
        """Test cheat sheet is concise (fits on one page)."""
        assembler = PlaybookAssembler()
        
        playbook = await assembler.assemble(
            questions=sample_questions,
            answers=sample_answers,
            profile=sample_profile,
            stories=sample_stories,
            competency_report=sample_competency_report,
        )
        
        cheat_sheet_md = playbook.cheat_sheet.to_markdown()
        
        # Rough estimate: one page is ~3000 characters
        assert len(cheat_sheet_md) < 3000
        
        # Should have limited items
        assert len(playbook.cheat_sheet.key_talking_points) <= 7
        assert len(playbook.cheat_sheet.top_stories) <= 3
        assert len(playbook.cheat_sheet.top_metrics) <= 5
        assert len(playbook.cheat_sheet.questions_to_ask) <= 5
