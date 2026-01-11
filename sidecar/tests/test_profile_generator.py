"""
Tests for ProfileGenerator (STORY-057).

Tests cover:
- Profile generation from facts
- Token limit enforcement
- Skills and achievements prioritization
- Profile caching and regeneration
- LLM prompt injection
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
import uuid

from src.extraction import ProfileGenerator
from src.extraction.profile_generator import TOKENS_PER_CHAR
from src.memory import MemoryStore, ExtractedFacts, CandidateProfile, STARStory
from src.memory.models import (
    SkillEntry,
    CareerEntry,
    Achievement,
    Education,
    DocumentSummary,
    SkillProficiency,
    DocumentType,
)


class TestProfileGeneratorBasic:
    """Basic ProfileGenerator tests."""
    
    def test_init(self):
        """Test ProfileGenerator initialization."""
        generator = ProfileGenerator()
        assert generator.memory_store is None
        assert generator.MAX_TOKENS == 1000
        
    def test_init_with_memory_store(self):
        """Test ProfileGenerator with memory store."""
        mock_store = MagicMock()
        generator = ProfileGenerator(memory_store=mock_store)
        assert generator.memory_store == mock_store
    
    def test_set_memory_store(self):
        """Test setting memory store after init."""
        generator = ProfileGenerator()
        mock_store = MagicMock()
        generator.set_memory_store(mock_store)
        assert generator.memory_store == mock_store
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        generator = ProfileGenerator()
        
        # 100 chars should be about 25 tokens
        text = "x" * 100
        tokens = generator.estimate_tokens(text)
        assert tokens == int(100 * TOKENS_PER_CHAR)
        
        # 1000 chars should be about 250 tokens
        text = "x" * 1000
        tokens = generator.estimate_tokens(text)
        assert tokens == 250


class TestProfileGeneration:
    """Test profile generation."""
    
    @pytest.fixture
    def sample_facts(self):
        """Create sample extracted facts."""
        return ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8, proficiency=SkillProficiency.EXPERT),
                SkillEntry(name="JavaScript", years=5, proficiency=SkillProficiency.PROFICIENT),
                SkillEntry(name="AWS", years=4, proficiency=SkillProficiency.PROFICIENT),
                SkillEntry(name="Docker", years=3, proficiency=SkillProficiency.PROFICIENT),
                SkillEntry(name="Kubernetes", years=2, proficiency=SkillProficiency.FAMILIAR),
                SkillEntry(name="Go", years=1, proficiency=SkillProficiency.FAMILIAR),
            ],
            timeline=[
                CareerEntry(
                    company="TechCorp",
                    role="Senior Engineer",
                    start_date="2020",
                    is_current=True,
                    highlights=["Led platform migration", "Built ML pipeline"],
                    metrics=["50% latency reduction"]
                ),
                CareerEntry(
                    company="StartupXYZ",
                    role="Software Engineer",
                    start_date="2016",
                    end_date="2020",
                    highlights=["Developed core API"],
                ),
            ],
            achievements=[
                Achievement(
                    description="Led migration of 100+ microservices to Kubernetes",
                    metrics=["50% cost reduction", "$500K annual savings"],
                    tags=["leadership", "scale"],
                    impact_level="high"
                ),
                Achievement(
                    description="Built ML pipeline processing 10M events/day",
                    metrics=["10M events/day", "99.9% uptime"],
                    tags=["technical", "scale"],
                ),
                Achievement(
                    description="Mentored 5 junior engineers to senior level",
                    tags=["leadership", "mentoring"],
                ),
            ],
            education=[
                Education(
                    institution="MIT",
                    degree="BS",
                    field_of_study="Computer Science",
                    year=2015
                )
            ],
            certifications=["AWS Solutions Architect"],
            total_experience_years=9,
            current_role="Senior Engineer",
            current_company="TechCorp",
            industries=["Technology", "FinTech"],
            languages=["Python", "JavaScript", "SQL"],
            document_id="test-doc-1"
        )
    
    def test_generate_basic_profile(self, sample_facts):
        """Test generating a basic profile."""
        generator = ProfileGenerator()
        
        profile = generator.generate(sample_facts)
        
        assert isinstance(profile, CandidateProfile)
        assert profile.current_role == "Senior Engineer"
        assert profile.total_experience_years == 9
        assert len(profile.core_skills) > 0
        assert len(profile.key_achievements) > 0
        assert profile.profile_text
        assert len(profile.profile_text) > 100
    
    def test_profile_contains_key_sections(self, sample_facts):
        """Test that profile contains all expected sections."""
        generator = ProfileGenerator()
        
        profile = generator.generate(sample_facts)
        
        # Check for key sections in profile text
        assert "## Candidate Profile" in profile.profile_text
        assert "Current Role" in profile.profile_text
        assert "Core Competencies" in profile.profile_text
        assert "Career Trajectory" in profile.profile_text
        assert "Key Achievements" in profile.profile_text
        assert "Positioning" in profile.profile_text
    
    def test_profile_includes_skills(self, sample_facts):
        """Test that profile includes skills."""
        generator = ProfileGenerator()
        
        profile = generator.generate(sample_facts)
        
        # Top skills should be in profile
        assert "Python" in profile.profile_text
        assert "Python" in profile.core_skills
    
    def test_profile_includes_achievements(self, sample_facts):
        """Test that profile includes achievements."""
        generator = ProfileGenerator()
        
        profile = generator.generate(sample_facts)
        
        # Should include achievement descriptions or truncated versions
        assert len(profile.key_achievements) > 0
        assert any("migration" in a.lower() for a in profile.key_achievements)
    
    def test_generate_with_target_role(self, sample_facts):
        """Test generating profile with target role."""
        generator = ProfileGenerator()
        
        profile = generator.generate(
            sample_facts,
            target_role="Staff Engineer",
            target_company="BigTech Inc"
        )
        
        assert profile.target_role == "Staff Engineer"
        assert profile.target_company == "BigTech Inc"
        assert "Staff Engineer" in profile.profile_text
        assert "BigTech Inc" in profile.profile_text
    
    def test_generate_with_memory_store(self, sample_facts):
        """Test that profile is saved to memory store."""
        mock_store = MagicMock()
        mock_store.get_profile.return_value = None
        
        generator = ProfileGenerator(memory_store=mock_store)
        profile = generator.generate(sample_facts)
        
        # Should save profile
        mock_store.save_profile.assert_called_once()
        saved_profile = mock_store.save_profile.call_args[0][0]
        assert saved_profile.id == profile.id
    
    def test_uses_cached_profile(self, sample_facts):
        """Test that cached profile is used when available."""
        cached_profile = CandidateProfile(
            id="cached-123",
            profile_text="Cached profile text",
            current_role="Cached Role"
        )
        
        mock_store = MagicMock()
        mock_store.get_profile.return_value = cached_profile
        
        generator = ProfileGenerator(memory_store=mock_store)
        profile = generator.generate(sample_facts)
        
        assert profile.id == "cached-123"
        assert profile.profile_text == "Cached profile text"
        # Should not save when using cached
        mock_store.save_profile.assert_not_called()
    
    def test_force_regenerate_ignores_cache(self, sample_facts):
        """Test that force_regenerate ignores cache."""
        cached_profile = CandidateProfile(
            id="cached-123",
            profile_text="Cached profile text"
        )
        
        mock_store = MagicMock()
        mock_store.get_profile.return_value = cached_profile
        
        generator = ProfileGenerator(memory_store=mock_store)
        profile = generator.generate(sample_facts, force_regenerate=True)
        
        # Should generate new profile, not use cached
        assert profile.id != "cached-123"
        assert profile.current_role == "Senior Engineer"
        mock_store.save_profile.assert_called_once()


class TestPrioritization:
    """Test skill and achievement prioritization."""
    
    def test_prioritize_skills_by_proficiency(self):
        """Test that expert skills are prioritized."""
        generator = ProfileGenerator()
        
        skills = [
            SkillEntry(name="Familiar Skill", proficiency=SkillProficiency.FAMILIAR),
            SkillEntry(name="Expert Skill", proficiency=SkillProficiency.EXPERT),
            SkillEntry(name="Proficient Skill", proficiency=SkillProficiency.PROFICIENT),
        ]
        
        prioritized = generator._prioritize_skills(skills, limit=3)
        
        # Expert should be first
        assert prioritized[0].name == "Expert Skill"
        assert prioritized[1].name == "Proficient Skill"
        assert prioritized[2].name == "Familiar Skill"
    
    def test_prioritize_skills_by_years(self):
        """Test that skills with more years are prioritized."""
        generator = ProfileGenerator()
        
        skills = [
            SkillEntry(name="Skill A", years=2, proficiency=SkillProficiency.PROFICIENT),
            SkillEntry(name="Skill B", years=10, proficiency=SkillProficiency.PROFICIENT),
            SkillEntry(name="Skill C", years=5, proficiency=SkillProficiency.PROFICIENT),
        ]
        
        prioritized = generator._prioritize_skills(skills, limit=3)
        
        # More years should rank higher
        assert prioritized[0].name == "Skill B"
    
    def test_prioritize_skills_respects_limit(self):
        """Test that skill limit is respected."""
        generator = ProfileGenerator()
        
        skills = [SkillEntry(name=f"Skill {i}") for i in range(20)]
        
        prioritized = generator._prioritize_skills(skills, limit=5)
        
        assert len(prioritized) == 5
    
    def test_prioritize_achievements_by_metrics(self):
        """Test that achievements with metrics are prioritized."""
        generator = ProfileGenerator()
        
        achievements = [
            Achievement(description="No metrics achievement"),
            Achievement(
                description="Rich metrics achievement",
                metrics=["50%", "$1M", "100 users"],
                tags=["scale"]
            ),
            Achievement(description="One metric", metrics=["20%"]),
        ]
        
        prioritized = generator._prioritize_achievements(achievements, limit=3)
        
        # Rich metrics should be first
        assert "Rich metrics" in prioritized[0].description
    
    def test_prioritize_achievements_by_tags(self):
        """Test that high-value tags boost priority."""
        generator = ProfileGenerator()
        
        achievements = [
            Achievement(description="Basic", tags=["other"]),
            Achievement(description="Leadership", tags=["leadership", "scale"]),
            Achievement(description="Technical", tags=["technical"]),
        ]
        
        prioritized = generator._prioritize_achievements(achievements, limit=3)
        
        # Leadership + scale tags should rank high
        assert "Leadership" in prioritized[0].description


class TestTokenLimits:
    """Test token limit enforcement."""
    
    def test_profile_under_limit(self):
        """Test that profile stays under token limit."""
        generator = ProfileGenerator()
        
        # Create facts that would generate a large profile
        facts = ExtractedFacts(
            skills=[SkillEntry(name=f"Skill {i}", years=i) for i in range(20)],
            achievements=[
                Achievement(
                    description=f"Achievement {i} with lots of details and metrics",
                    metrics=[f"{i}%", f"${i}M"]
                ) for i in range(20)
            ],
            timeline=[
                CareerEntry(
                    company=f"Company {i}",
                    role=f"Role {i}",
                    start_date=f"{2010+i}",
                    highlights=[f"Highlight {j}" for j in range(5)]
                ) for i in range(10)
            ],
            total_experience_years=15,
            current_role="Very Senior Distinguished Principal Staff Engineer",
            current_company="Enormous Technology Corporation International"
        )
        
        profile = generator.generate(facts)
        
        # Check token estimate is reasonable
        estimated_tokens = generator.estimate_tokens(profile.profile_text)
        assert estimated_tokens <= generator.MAX_TOKENS + 100  # Small buffer
    
    def test_truncation_preserves_structure(self):
        """Test that truncation preserves profile structure."""
        generator = ProfileGenerator()
        
        # Create very long text
        long_text = "## Candidate Profile\n\n" + "x" * 5000 + "\n\n## Section 2"
        
        truncated = generator._truncate_to_limit(long_text)
        
        # Should start with header
        assert truncated.startswith("## Candidate Profile")
        # Should have truncation indicator
        assert "*[Profile truncated" in truncated or len(truncated) < len(long_text)


class TestStrengthsAndGaps:
    """Test strength and gap identification."""
    
    def test_identify_experience_strength(self):
        """Test that experience years translate to strengths."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(total_experience_years=12)
        
        strengths = generator._identify_strengths(facts)
        
        assert any("experience" in s.lower() for s in strengths)
    
    def test_identify_expert_skills_strength(self):
        """Test that expert skills become strengths."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8, proficiency=SkillProficiency.EXPERT),
                SkillEntry(name="AWS", years=6, proficiency=SkillProficiency.EXPERT),
                SkillEntry(name="Docker", years=5, proficiency=SkillProficiency.EXPERT),
            ]
        )
        
        strengths = generator._identify_strengths(facts)
        
        assert any("expert" in s.lower() for s in strengths)
    
    def test_identify_leadership_strength(self):
        """Test that leadership achievements become strengths."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(
            achievements=[
                Achievement(
                    description="Led team of 10 engineers",
                    tags=["leadership"]
                )
            ]
        )
        
        strengths = generator._identify_strengths(facts)
        
        assert any("leadership" in s.lower() for s in strengths)
    
    def test_identify_gaps_for_senior_role(self):
        """Test gap identification for senior roles."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(total_experience_years=3)
        
        gaps = generator._identify_gaps(facts, "Senior Staff Engineer")
        
        # Should identify experience gap for senior role
        assert len(gaps) > 0


class TestProfileForPrompt:
    """Test get_profile_for_prompt method."""
    
    def test_get_profile_for_prompt_with_store(self):
        """Test getting profile for prompt injection."""
        cached_profile = CandidateProfile(
            profile_text="## Candidate Profile\n\nTest profile content"
        )
        
        mock_store = MagicMock()
        mock_store.get_profile.return_value = cached_profile
        
        generator = ProfileGenerator(memory_store=mock_store)
        prompt_text = generator.get_profile_for_prompt()
        
        assert "## Candidate Profile" in prompt_text
        assert "Test profile content" in prompt_text
    
    def test_get_profile_for_prompt_no_store(self):
        """Test getting profile without store."""
        generator = ProfileGenerator()
        prompt_text = generator.get_profile_for_prompt()
        
        assert prompt_text == ""
    
    def test_get_profile_for_prompt_no_profile(self):
        """Test getting profile when none exists."""
        mock_store = MagicMock()
        mock_store.get_profile.return_value = None
        
        generator = ProfileGenerator(memory_store=mock_store)
        prompt_text = generator.get_profile_for_prompt()
        
        assert prompt_text == ""


class TestRegenerateProfile:
    """Test profile regeneration."""
    
    def test_regenerate_profile(self):
        """Test regenerating profile from stored facts."""
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=5)],
            timeline=[CareerEntry(company="TechCo", role="Engineer", start_date="2020")],
            total_experience_years=5,
            current_role="Engineer"
        )
        
        mock_store = MagicMock()
        mock_store.get_all_facts.return_value = facts
        mock_store.get_all_document_summaries.return_value = []
        mock_store.get_all_stories.return_value = []
        mock_store.get_profile.return_value = None
        
        generator = ProfileGenerator(memory_store=mock_store)
        profile = generator.regenerate_profile(
            target_role="Senior Engineer",
            target_company="BigTech"
        )
        
        assert profile is not None
        assert profile.target_role == "Senior Engineer"
        assert profile.target_company == "BigTech"
        mock_store.save_profile.assert_called_once()
    
    def test_regenerate_without_facts(self):
        """Test regeneration returns None when no facts."""
        mock_store = MagicMock()
        mock_store.get_all_facts.return_value = ExtractedFacts()
        
        generator = ProfileGenerator(memory_store=mock_store)
        profile = generator.regenerate_profile()
        
        assert profile is None


class TestProfileStats:
    """Test profile statistics."""
    
    def test_get_profile_stats(self):
        """Test getting profile statistics."""
        cached_profile = CandidateProfile(
            id="test-123",
            profile_text="Test profile " * 100,  # ~1200 chars
            current_role="Engineer",
            total_experience_years=5,
            core_skills=["Python", "AWS"],
            key_achievements=["Led migration"],
            strengths=["Technical"],
            gaps=[],
            generated_at=datetime.now(),
            source_documents=["doc-1"]
        )
        
        mock_store = MagicMock()
        mock_store.get_profile.return_value = cached_profile
        
        generator = ProfileGenerator(memory_store=mock_store)
        stats = generator.get_profile_stats()
        
        assert stats["id"] == "test-123"
        assert stats["current_role"] == "Engineer"
        assert stats["experience_years"] == 5
        assert stats["num_skills"] == 2
        assert stats["num_achievements"] == 1
        assert stats["num_strengths"] == 1
        assert stats["profile_chars"] > 0
        assert stats["estimated_tokens"] > 0
        assert stats["source_documents"] == 1
    
    def test_get_profile_stats_no_profile(self):
        """Test stats when no profile exists."""
        mock_store = MagicMock()
        mock_store.get_profile.return_value = None
        
        generator = ProfileGenerator(memory_store=mock_store)
        stats = generator.get_profile_stats()
        
        assert "error" in stats


class TestEdgeCases:
    """Test edge cases."""
    
    def test_empty_facts(self):
        """Test generating profile from empty facts."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts()
        profile = generator.generate(facts)
        
        assert profile is not None
        assert "Not specified" in profile.profile_text or "not available" in profile.profile_text.lower()
    
    def test_minimal_facts(self):
        """Test generating profile from minimal facts."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(
            current_role="Developer",
            total_experience_years=2
        )
        
        profile = generator.generate(facts)
        
        assert profile.current_role == "Developer"
        assert profile.total_experience_years == 2
        assert "Developer" in profile.profile_text
    
    def test_special_characters_in_facts(self):
        """Test handling special characters."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(
            skills=[SkillEntry(name="C++", years=3)],
            achievements=[
                Achievement(description="Improved performance by 50% using <algorithm>")
            ],
            current_role="C/C++ Developer"
        )
        
        profile = generator.generate(facts)
        
        assert "C++" in profile.profile_text or "C/C++" in profile.profile_text
    
    def test_very_long_achievement_descriptions(self):
        """Test truncation of long achievement descriptions."""
        generator = ProfileGenerator()
        
        long_desc = "This is a very long achievement description " * 10
        facts = ExtractedFacts(
            achievements=[Achievement(description=long_desc)]
        )
        
        profile = generator.generate(facts)
        
        # Achievement should be truncated in key_achievements
        assert len(profile.key_achievements[0]) <= 100 + 3  # +3 for "..."


class TestDocumentSummaryIntegration:
    """Test integration with document summaries."""
    
    def test_jd_summary_included(self):
        """Test that JD summary info is included in target section."""
        generator = ProfileGenerator()
        
        facts = ExtractedFacts(
            current_role="Engineer",
            total_experience_years=5
        )
        
        jd_summary = DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            filename="job.pdf",
            document_summary="Senior role at tech company",
            key_points=["5+ years Python", "Leadership experience", "AWS expertise"]
        )
        
        profile = generator.generate(
            facts,
            summaries=[jd_summary],
            target_role="Senior Engineer"
        )
        
        # JD key points should be referenced
        assert "requirements to address" in profile.profile_text.lower() or "Senior Engineer" in profile.profile_text


class TestIntegrationWithMemoryStore:
    """Integration tests with MemoryStore."""
    
    def test_full_workflow(self):
        """Test full generate and retrieve workflow."""
        # Use a mock that maintains state
        stored_profile = None
        
        def mock_save(profile):
            nonlocal stored_profile
            stored_profile = profile
            return profile.id
        
        def mock_get():
            return stored_profile
        
        mock_store = MagicMock()
        mock_store.save_profile = mock_save
        mock_store.get_profile = mock_get
        
        generator = ProfileGenerator(memory_store=mock_store)
        
        # Initial generation
        facts = ExtractedFacts(
            current_role="Engineer",
            total_experience_years=5,
            skills=[SkillEntry(name="Python", years=5)]
        )
        
        # First generate should create profile
        profile1 = generator.generate(facts, force_regenerate=True)
        assert stored_profile is not None
        
        # Second call should use cached
        profile2 = generator.generate(facts)
        assert profile2.id == profile1.id
