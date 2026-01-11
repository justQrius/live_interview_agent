"""
Tests for CompetencyMapper (STORY-061).

Tests cover:
- Requirement extraction from JD
- Evidence matching from resume
- Gap identification
- Mitigation suggestions
- Match strength rating
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
import json

from src.playbook.competency_mapper import (
    CompetencyMapper,
    CompetencyMapping,
    CompetencyReport,
    RequirementType,
    MatchStrength,
    MITIGATION_STRATEGIES,
)
from src.memory.models import (
    ExtractedFacts,
    DocumentSummary,
    DocumentType,
    SkillEntry,
    Achievement,
    Education,
)


class TestCompetencyMapping:
    
    def test_mapping_creation(self):
        mapping = CompetencyMapping(
            requirement="5+ years Python experience",
            requirement_type=RequirementType.TECHNICAL_SKILL,
            is_required=True,
            evidence="Python (7 years)",
            match_strength=MatchStrength.STRONG,
        )
        
        assert mapping.requirement == "5+ years Python experience"
        assert mapping.is_required is True
        assert mapping.match_strength == MatchStrength.STRONG
    
    def test_mapping_to_dict(self):
        mapping = CompetencyMapping(
            requirement="Leadership skills",
            requirement_type=RequirementType.SOFT_SKILL,
            is_required=False,
            evidence="Led team of 5",
            metrics=["5 team members", "20% productivity increase"],
            match_strength=MatchStrength.MODERATE,
        )
        
        data = mapping.to_dict()
        
        assert data["requirement"] == "Leadership skills"
        assert data["requirement_type"] == "soft_skill"
        assert data["is_required"] is False
        assert len(data["metrics"]) == 2
    
    def test_mapping_from_dict(self):
        data = {
            "requirement": "AWS experience",
            "requirement_type": "technical_skill",
            "is_required": True,
            "evidence": "AWS (5 years)",
            "match_strength": "strong",
        }
        
        mapping = CompetencyMapping.from_dict(data)
        
        assert mapping.requirement == "AWS experience"
        assert mapping.requirement_type == RequirementType.TECHNICAL_SKILL
        assert mapping.match_strength == MatchStrength.STRONG


class TestCompetencyReport:
    
    def test_report_creation(self):
        mappings = [
            CompetencyMapping(
                requirement="Python",
                match_strength=MatchStrength.STRONG,
            ),
            CompetencyMapping(
                requirement="AWS",
                match_strength=MatchStrength.MODERATE,
            ),
            CompetencyMapping(
                requirement="Kubernetes",
                match_strength=MatchStrength.GAP,
                is_required=True,
            ),
        ]
        
        report = CompetencyReport(
            mappings=mappings,
            total_requirements=3,
            strong_matches=1,
            moderate_matches=1,
            gaps=1,
            critical_gaps=["Kubernetes"],
        )
        
        assert report.total_requirements == 3
        assert report.strong_matches == 1
        assert len(report.critical_gaps) == 1
    
    def test_report_to_dict(self):
        report = CompetencyReport(
            mappings=[
                CompetencyMapping(requirement="Test", match_strength=MatchStrength.STRONG)
            ],
            total_requirements=1,
            strong_matches=1,
        )
        
        data = report.to_dict()
        
        assert data["total_requirements"] == 1
        assert len(data["mappings"]) == 1
    
    def test_report_to_markdown_table(self):
        report = CompetencyReport(
            mappings=[
                CompetencyMapping(
                    requirement="Python programming",
                    requirement_type=RequirementType.TECHNICAL_SKILL,
                    is_required=True,
                    evidence="7 years experience",
                    match_strength=MatchStrength.STRONG,
                    emphasis_points=["Built production systems"],
                ),
            ],
        )
        
        table = report.to_markdown_table()
        
        assert "Python programming" in table
        assert "🟢" in table  # Strong match icon
        assert "|" in table  # Table format


class TestCompetencyMapperBasic:
    
    def test_init(self):
        mapper = CompetencyMapper()
        assert mapper.llm_provider is None
        assert mapper.memory_store is None
    
    def test_init_with_providers(self):
        mock_llm = MagicMock()
        mock_store = MagicMock()
        
        mapper = CompetencyMapper(
            llm_provider=mock_llm,
            memory_store=mock_store
        )
        
        assert mapper.llm_provider == mock_llm
        assert mapper.memory_store == mock_store
    
    def test_set_providers(self):
        mapper = CompetencyMapper()
        mock_llm = MagicMock()
        
        mapper.set_llm_provider(mock_llm)
        
        assert mapper.llm_provider == mock_llm


class TestRequirementExtraction:
    
    @pytest.fixture
    def sample_jd_summary(self):
        return DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            document_summary="Senior Software Engineer position",
            key_points=[
                "5+ years Python experience required",
                "AWS cloud platform experience required",
                "Leadership and mentoring skills preferred",
                "Bachelor's degree in Computer Science required",
                "Kubernetes experience is a plus",
                "Strong communication skills",
            ],
        )
    
    def test_extract_requirements(self, sample_jd_summary):
        mapper = CompetencyMapper()
        
        requirements = mapper._extract_requirements(sample_jd_summary)
        
        assert len(requirements) == 6
        
        # Check that requirements are tuples of (text, type, is_required)
        for req in requirements:
            assert len(req) == 3
            assert isinstance(req[0], str)
            assert isinstance(req[1], RequirementType)
            assert isinstance(req[2], bool)
    
    def test_identify_required_vs_preferred(self, sample_jd_summary):
        mapper = CompetencyMapper()
        
        requirements = mapper._extract_requirements(sample_jd_summary)
        
        # "required" should be is_required=True
        python_req = next(r for r in requirements if "Python" in r[0])
        assert python_req[2] is True
        
        # "preferred" should be is_required=False
        leadership_req = next(r for r in requirements if "Leadership" in r[0])
        assert leadership_req[2] is False
        
        # "plus" should be is_required=False
        k8s_req = next(r for r in requirements if "Kubernetes" in r[0])
        assert k8s_req[2] is False
    
    def test_categorize_requirement_types(self, sample_jd_summary):
        mapper = CompetencyMapper()
        
        requirements = mapper._extract_requirements(sample_jd_summary)
        
        # Python should be technical skill
        python_req = next(r for r in requirements if "Python" in r[0])
        assert python_req[1] == RequirementType.TECHNICAL_SKILL
        
        # Leadership should be soft skill
        leadership_req = next(r for r in requirements if "Leadership" in r[0])
        assert leadership_req[1] == RequirementType.SOFT_SKILL
        
        # Bachelor's degree should be education
        edu_req = next(r for r in requirements if "Bachelor" in r[0])
        assert edu_req[1] == RequirementType.EDUCATION
    
    def test_extract_from_empty_jd(self):
        mapper = CompetencyMapper()
        
        empty_jd = DocumentSummary(
            document_id="empty",
            document_type=DocumentType.JOB_DESCRIPTION,
        )
        
        requirements = mapper._extract_requirements(empty_jd)
        
        assert requirements == []


class TestEvidenceMatching:
    
    @pytest.fixture
    def sample_facts(self):
        return ExtractedFacts(
            current_role="Senior Engineer",
            current_company="TechCorp",
            total_experience_years=8,
            skills=[
                SkillEntry(name="Python", years=7),
                SkillEntry(name="AWS", years=5),
                SkillEntry(name="JavaScript", years=4),
                SkillEntry(name="Docker", years=3),
            ],
            achievements=[
                Achievement(
                    description="Led migration to microservices",
                    metrics=["40% latency reduction", "zero downtime"],
                    tags=["leadership", "technical"],
                ),
                Achievement(
                    description="Mentored 5 junior engineers",
                    metrics=["5 engineers"],
                    tags=["leadership", "mentoring"],
                ),
            ],
            education=[
                Education(
                    institution="MIT",
                    degree="Bachelor of Science",
                    field_of_study="Computer Science",
                ),
            ],
        )
    
    @pytest.fixture
    def sample_jd_summary(self):
        return DocumentSummary(
            document_id="jd-1",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=[
                "5+ years Python experience required",
                "AWS experience required",
                "Kubernetes experience required",
                "Leadership skills",
            ],
        )
    
    @pytest.mark.asyncio
    async def test_match_with_strong_evidence(self, sample_jd_summary, sample_facts):
        mapper = CompetencyMapper()
        
        report = await mapper.map_competencies(sample_jd_summary, sample_facts)
        
        # Python should be strong match (7 years >= required)
        python_mapping = next(
            m for m in report.mappings if "Python" in m.requirement
        )
        assert python_mapping.match_strength == MatchStrength.STRONG
        assert python_mapping.evidence is not None
    
    @pytest.mark.asyncio
    async def test_identify_gaps(self, sample_jd_summary, sample_facts):
        mapper = CompetencyMapper()
        
        report = await mapper.map_competencies(sample_jd_summary, sample_facts)
        
        # Kubernetes should be a gap (not in skills)
        k8s_mapping = next(
            m for m in report.mappings if "Kubernetes" in m.requirement
        )
        assert k8s_mapping.match_strength == MatchStrength.GAP
    
    @pytest.mark.asyncio
    async def test_report_statistics(self, sample_jd_summary, sample_facts):
        mapper = CompetencyMapper()
        
        report = await mapper.map_competencies(sample_jd_summary, sample_facts)
        
        assert report.total_requirements == 4
        assert report.strong_matches + report.moderate_matches + report.weak_matches + report.gaps == 4


class TestMitigationSuggestions:
    
    def test_generate_mitigation_for_gap(self):
        mapper = CompetencyMapper()
        
        mapping = CompetencyMapping(
            requirement="Kubernetes experience",
            requirement_type=RequirementType.TECHNICAL_SKILL,
            match_strength=MatchStrength.GAP,
        )
        
        mitigation = mapper._generate_mitigation(mapping)
        
        assert mitigation is not None
        assert len(mitigation) > 10
    
    def test_mitigation_strategies_exist(self):
        assert RequirementType.TECHNICAL_SKILL in MITIGATION_STRATEGIES
        assert RequirementType.SOFT_SKILL in MITIGATION_STRATEGIES
        assert RequirementType.EXPERIENCE in MITIGATION_STRATEGIES
        assert RequirementType.EDUCATION in MITIGATION_STRATEGIES
    
    @pytest.mark.asyncio
    async def test_gaps_have_mitigations(self):
        mapper = CompetencyMapper()
        
        jd = DocumentSummary(
            document_id="jd",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["Kubernetes experience required"],
        )
        
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Docker", years=3)],
        )
        
        report = await mapper.map_competencies(jd, facts)
        
        for mapping in report.mappings:
            if mapping.match_strength == MatchStrength.GAP:
                assert mapping.mitigation is not None


class TestLLMMapping:
    
    @pytest.fixture
    def mock_llm_response(self):
        return json.dumps([
            {
                "requirement": "5+ years Python",
                "requirement_type": "technical_skill",
                "is_required": True,
                "evidence": "Python (7 years) at TechCorp",
                "metrics": ["Built 5 production services"],
                "emphasis_points": ["Deep Python expertise", "Production experience"],
                "match_strength": "strong",
                "mitigation": None
            },
            {
                "requirement": "Kubernetes experience",
                "requirement_type": "technical_skill",
                "is_required": True,
                "evidence": None,
                "metrics": [],
                "emphasis_points": [],
                "match_strength": "gap",
                "mitigation": "Highlight Docker experience as foundation"
            },
        ])
    
    @pytest.mark.asyncio
    async def test_llm_mapping(self, mock_llm_response):
        mock_llm = MagicMock()
        
        async def mock_generate(*args, **kwargs):
            yield mock_llm_response
        
        mock_llm.generate_response = mock_generate
        
        mapper = CompetencyMapper(llm_provider=mock_llm)
        
        jd = DocumentSummary(
            document_id="jd",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["5+ years Python", "Kubernetes"],
        )
        
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=7)],
        )
        
        report = await mapper.map_competencies(jd, facts)
        
        assert len(report.mappings) == 2
        
        python_mapping = report.mappings[0]
        assert python_mapping.match_strength == MatchStrength.STRONG
    
    @pytest.mark.asyncio
    async def test_llm_fallback_on_error(self):
        mock_llm = MagicMock()
        
        async def mock_generate(*args, **kwargs):
            raise Exception("LLM error")
            yield ""
        
        mock_llm.generate_response = mock_generate
        
        mapper = CompetencyMapper(llm_provider=mock_llm)
        
        jd = DocumentSummary(
            document_id="jd",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["Python required"],
        )
        
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=5)],
        )
        
        # Should fall back to rule-based mapping
        report = await mapper.map_competencies(jd, facts)
        
        assert report is not None
        assert len(report.mappings) > 0


class TestGapsSummary:
    
    def test_gaps_summary_with_critical_gaps(self):
        mapper = CompetencyMapper()
        
        report = CompetencyReport(
            mappings=[
                CompetencyMapping(
                    requirement="Kubernetes",
                    match_strength=MatchStrength.GAP,
                    is_required=True,
                    mitigation="Learn Docker orchestration",
                ),
            ],
            critical_gaps=["Kubernetes"],
            gaps=1,
        )
        
        summary = mapper.get_gaps_summary(report)
        
        assert "Critical Gaps" in summary
        assert "Kubernetes" in summary
        assert "Mitigation" in summary
    
    def test_gaps_summary_no_gaps(self):
        mapper = CompetencyMapper()
        
        report = CompetencyReport(
            mappings=[
                CompetencyMapping(
                    requirement="Python",
                    match_strength=MatchStrength.STRONG,
                ),
            ],
            gaps=0,
            critical_gaps=[],
        )
        
        summary = mapper.get_gaps_summary(report)
        
        assert "No significant gaps" in summary


class TestSkillAndAchievementIndexing:
    
    def test_build_skill_index(self):
        mapper = CompetencyMapper()
        
        facts = ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=5),
                SkillEntry(name="Amazon Web Services", years=3),
            ]
        )
        
        index = mapper._build_skill_index(facts)
        
        assert "python" in index
        assert "amazon" in index
        assert "web" in index
        assert "services" in index
    
    def test_build_achievement_index(self):
        mapper = CompetencyMapper()
        
        facts = ExtractedFacts(
            achievements=[
                Achievement(
                    description="Led team migration project",
                    tags=["leadership", "migration"],
                ),
            ]
        )
        
        index = mapper._build_achievement_index(facts)
        
        assert "migration" in index
        assert "leadership" in index


class TestEdgeCases:
    
    @pytest.mark.asyncio
    async def test_empty_jd(self):
        mapper = CompetencyMapper()
        
        jd = DocumentSummary(
            document_id="empty",
            document_type=DocumentType.JOB_DESCRIPTION,
        )
        
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=5)],
        )
        
        report = await mapper.map_competencies(jd, facts)
        
        assert report.total_requirements == 0
        assert report.mappings == []
    
    @pytest.mark.asyncio
    async def test_empty_facts(self):
        mapper = CompetencyMapper()
        
        jd = DocumentSummary(
            document_id="jd",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["Python required"],
        )
        
        facts = ExtractedFacts()
        
        report = await mapper.map_competencies(jd, facts)
        
        assert report.total_requirements == 1
        assert report.gaps == 1
    
    @pytest.mark.asyncio
    async def test_all_requirements_matched(self):
        mapper = CompetencyMapper()
        
        jd = DocumentSummary(
            document_id="jd",
            document_type=DocumentType.JOB_DESCRIPTION,
            key_points=["Python experience", "AWS experience"],
        )
        
        facts = ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=10),
                SkillEntry(name="AWS", years=5),
            ],
        )
        
        report = await mapper.map_competencies(jd, facts)
        
        assert report.gaps == 0
        assert report.strong_matches + report.moderate_matches == 2
