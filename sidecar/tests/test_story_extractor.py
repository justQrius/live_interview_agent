"""
Tests for the STAR Story Extractor (STORY-056).

Tests cover:
- Story identification from achievements
- STAR structure completeness
- Tag assignment
- Opening line and short version generation
- Basic fallback extraction
- LLM integration (mocked)
"""

import pytest
import tempfile
import json
from datetime import datetime

from src.extraction import StoryExtractor
from src.memory import MemoryStore, ExtractedFacts, STARStory
from src.memory.models import Achievement, CareerEntry, SkillProficiency


# Sample extracted facts for testing
def create_sample_facts():
    """Create sample extracted facts with rich achievements."""
    return ExtractedFacts(
        skills=[],
        timeline=[
            CareerEntry(
                company="Google",
                role="Staff Software Engineer",
                start_date="2020",
                end_date=None,
                is_current=True,
                highlights=[
                    "Led migration of 50+ microservices to Kubernetes with zero downtime",
                    "Built ML inference platform serving 10M+ predictions/day",
                    "Managed team of 15 engineers across 3 time zones"
                ],
                metrics=["99.99% uptime", "$4.2M annual savings", "40% latency reduction"]
            ),
            CareerEntry(
                company="Meta",
                role="Senior Software Engineer",
                start_date="2017",
                end_date="2020",
                highlights=[
                    "Designed real-time messaging infrastructure handling 1B+ messages/day",
                    "Improved system throughput by 150%"
                ],
                metrics=["150% throughput improvement", "1B+ messages/day"]
            ),
        ],
        achievements=[
            Achievement(
                description="Led migration of 50+ microservices to Kubernetes, achieving 99.99% uptime",
                metrics=["99.99% uptime", "50+ services", "zero downtime"],
                context="Google",
                tags=["leadership", "technical", "scale"]
            ),
            Achievement(
                description="Built ML inference platform serving 10M+ predictions daily",
                metrics=["10M+ predictions/day"],
                context="Google",
                tags=["technical", "scale", "innovation"]
            ),
            Achievement(
                description="Reduced infrastructure costs by 35%, saving $4.2M annually",
                metrics=["35% reduction", "$4.2M savings"],
                context="Google",
                tags=["cost", "technical"]
            ),
            Achievement(
                description="Managed cross-functional team of 15 engineers across 3 time zones",
                metrics=["15 engineers", "3 time zones"],
                context="Google",
                tags=["leadership", "cross_functional"]
            ),
            Achievement(
                description="Designed and built real-time messaging infrastructure",
                metrics=["1B+ messages/day"],
                context="Meta",
                tags=["technical", "scale"]
            ),
            Achievement(
                description="Improved system throughput by 150% through architecture redesign",
                metrics=["150% improvement"],
                context="Meta",
                tags=["technical", "problem_solving"]
            ),
            Achievement(
                description="Mentored 8 junior engineers, with 5 receiving promotions",
                metrics=["8 engineers mentored", "5 promotions"],
                context="Meta",
                tags=["mentoring", "leadership"]
            ),
            Achievement(
                description="Resolved critical production incident affecting 10M users in under 2 hours",
                metrics=["10M users", "2 hours resolution"],
                context="Meta",
                tags=["problem_solving", "deadline"]
            ),
        ],
        total_experience_years=8,
        current_role="Staff Software Engineer",
        current_company="Google",
    )


def create_sparse_facts():
    """Create sparse facts with minimal achievements."""
    return ExtractedFacts(
        timeline=[
            CareerEntry(
                company="Startup Inc",
                role="Software Engineer",
                start_date="2022",
                highlights=["Built web application"]
            )
        ],
        achievements=[
            Achievement(description="Built web application", context="Startup Inc")
        ],
        total_experience_years=2,
        current_role="Software Engineer",
    )


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def generate_response(self, prompt: str, context: str, history: list):
        self.calls.append({"prompt": prompt, "context": context, "history": history})
        for chunk in self.response:
            yield chunk


class TestStoryIdentification:
    """Tests for story identification."""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response with stories."""
        return json.dumps([
            {
                "title": "The Kubernetes Migration",
                "situation": "At Google, our legacy infrastructure was causing deployment delays and reliability issues. We had 50+ microservices on traditional VMs.",
                "task": "As the tech lead, I was responsible for migrating our entire platform to Kubernetes without any customer impact.",
                "action": "I designed a phased migration strategy, implemented blue-green deployments, set up comprehensive monitoring, and led a team of 8 engineers through the 6-month project.",
                "result": "We achieved zero downtime migration, 99.99% uptime post-migration, and reduced deployment time from 2 hours to 10 minutes.",
                "metrics": ["99.99% uptime", "50+ services", "zero downtime", "6-month project"],
                "tags": ["leadership", "technical", "scale"],
                "source_company": "Google",
                "source_role": "Staff Software Engineer",
                "opening_line": "When I joined Google's platform team, I inherited a critical challenge: our deployment process was causing significant customer impact.",
                "twenty_second_version": "I led the migration of 50+ microservices to Kubernetes at Google, achieving zero downtime and 99.99% uptime through careful planning and blue-green deployments.",
                "confidence": 0.95
            },
            {
                "title": "The ML Platform",
                "situation": "Google needed a scalable ML inference platform to serve predictions for multiple products.",
                "task": "I was tasked with designing and building the platform from scratch.",
                "action": "I architected a distributed system using TensorFlow Serving, implemented auto-scaling, and optimized for latency.",
                "result": "The platform now serves 10M+ predictions daily with p99 latency under 50ms.",
                "metrics": ["10M+ predictions/day", "p99 < 50ms"],
                "tags": ["technical", "innovation", "scale"],
                "source_company": "Google",
                "source_role": "Staff Software Engineer",
                "opening_line": "Building ML infrastructure at Google scale taught me the importance of designing for failure.",
                "twenty_second_version": "I designed and built an ML inference platform at Google serving 10M+ predictions daily with under 50ms latency.",
                "confidence": 0.90
            },
            {
                "title": "The Cost Optimization",
                "situation": "Our cloud infrastructure costs were growing 40% year over year, threatening project budgets.",
                "task": "I was asked to find ways to reduce costs without impacting performance.",
                "action": "I analyzed usage patterns, implemented spot instances, optimized container resources, and negotiated reserved capacity.",
                "result": "Achieved 35% cost reduction, saving $4.2M annually while maintaining SLAs.",
                "metrics": ["35% reduction", "$4.2M savings"],
                "tags": ["technical", "cost"],
                "source_company": "Google",
                "opening_line": "When I was asked to cut $4M from our infrastructure budget, I knew I needed a data-driven approach.",
                "twenty_second_version": "I reduced Google's cloud costs by 35% ($4.2M annually) through usage optimization and strategic capacity planning.",
                "confidence": 0.85
            }
        ])

    @pytest.mark.asyncio
    async def test_extract_stories_with_llm(self, store, mock_llm_response):
        """Test story extraction with mocked LLM."""
        mock_llm = MockLLMProvider(mock_llm_response)
        extractor = StoryExtractor(llm_provider=mock_llm, memory_store=store)
        
        facts = create_sample_facts()
        stories = await extractor.extract_stories(facts)
        
        # Should extract 3 stories
        assert len(stories) == 3
        
        # Verify first story
        migration_story = stories[0]
        assert migration_story.title == "The Kubernetes Migration"
        assert len(migration_story.situation) > 20
        assert len(migration_story.task) > 10
        assert len(migration_story.action) > 20
        assert len(migration_story.result) > 10
        assert migration_story.confidence >= 0.85

    @pytest.mark.asyncio
    async def test_stories_saved_to_memory_store(self, store, mock_llm_response):
        """Test that stories are saved to memory store."""
        mock_llm = MockLLMProvider(mock_llm_response)
        extractor = StoryExtractor(llm_provider=mock_llm, memory_store=store)
        
        facts = create_sample_facts()
        await extractor.extract_stories(facts)
        
        # Verify stories in store
        saved_stories = store.get_all_stories()
        assert len(saved_stories) == 3


class TestStarCompleteness:
    """Tests for STAR structure completeness."""

    @pytest.fixture
    def extractor(self):
        return StoryExtractor()

    def test_star_components_present(self, extractor):
        """Test that all STAR components are present."""
        story_data = {
            "title": "Test Story",
            "situation": "The situation was challenging.",
            "task": "My task was clear.",
            "action": "I took specific actions to resolve the issue.",
            "result": "The result was positive with 50% improvement.",
            "metrics": ["50% improvement"],
            "tags": ["technical"],
            "confidence": 0.8
        }
        
        story = extractor._dict_to_story(story_data)
        
        assert story is not None
        assert story.situation != ""
        assert story.task != ""
        assert story.action != ""
        assert story.result != ""

    def test_full_version_built(self, extractor):
        """Test that full version is built correctly."""
        story_data = {
            "situation": "Context here.",
            "task": "Task here.",
            "action": "Actions taken.",
            "result": "Results achieved."
        }
        
        full_version = extractor._build_full_version(story_data)
        
        assert "Situation" in full_version
        assert "Task" in full_version
        assert "Action" in full_version
        assert "Result" in full_version


class TestTagAssignment:
    """Tests for story tag assignment."""

    @pytest.fixture
    def extractor(self):
        return StoryExtractor()

    def test_validate_tags(self, extractor):
        """Test tag validation."""
        tags = ["leadership", "TECHNICAL", "invalid_tag", "scale"]
        validated = extractor._validate_tags(tags)
        
        assert "leadership" in validated
        assert "technical" in validated
        assert "scale" in validated
        # Invalid tags are kept but normalized
        assert all(isinstance(t, str) for t in validated)

    def test_infer_tags_leadership(self, extractor):
        """Test inferring leadership tag."""
        text = "Led a team of 8 engineers to complete the project"
        tags = extractor._infer_tags(text)
        
        assert "leadership" in tags

    def test_infer_tags_technical(self, extractor):
        """Test inferring technical tag."""
        text = "Built and implemented a distributed caching system"
        tags = extractor._infer_tags(text)
        
        assert "technical" in tags

    def test_infer_tags_scale(self, extractor):
        """Test inferring scale tag."""
        text = "Scaled the system to handle 1 million users"
        tags = extractor._infer_tags(text)
        
        assert "scale" in tags


class TestOpeningLine:
    """Tests for opening line quality."""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.mark.asyncio
    async def test_opening_line_generated(self, store):
        """Test that opening lines are generated."""
        response = json.dumps([{
            "title": "Test",
            "situation": "Situation",
            "task": "Task",
            "action": "Action",
            "result": "Result",
            "opening_line": "Let me tell you about when I faced a major challenge...",
            "twenty_second_version": "Short version",
            "confidence": 0.8
        }])
        
        mock_llm = MockLLMProvider(response)
        extractor = StoryExtractor(llm_provider=mock_llm, memory_store=store)
        
        stories = await extractor.extract_stories(create_sample_facts())
        
        assert len(stories) >= 1
        assert len(stories[0].opening_line) > 10


class TestShortVersion:
    """Tests for 20-second version."""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.mark.asyncio
    async def test_twenty_second_version_generated(self, store):
        """Test that short version is generated."""
        response = json.dumps([{
            "title": "Test",
            "situation": "S",
            "task": "T",
            "action": "A",
            "result": "R",
            "twenty_second_version": "I led a team to migrate 50 services to Kubernetes with zero downtime, achieving 99.99% uptime.",
            "confidence": 0.8
        }])
        
        mock_llm = MockLLMProvider(response)
        extractor = StoryExtractor(llm_provider=mock_llm, memory_store=store)
        
        stories = await extractor.extract_stories(create_sample_facts())
        
        assert len(stories) >= 1
        assert len(stories[0].twenty_second_version) > 20


class TestSparseResume:
    """Tests for handling sparse resume data."""

    @pytest.fixture
    def extractor(self):
        return StoryExtractor()

    @pytest.mark.asyncio
    async def test_basic_extraction_without_llm(self, extractor):
        """Test basic story extraction without LLM."""
        facts = create_sample_facts()
        stories = await extractor.extract_stories(facts)
        
        # Should generate some stories even without LLM
        assert len(stories) >= 1

    @pytest.mark.asyncio
    async def test_sparse_facts_lower_confidence(self, extractor):
        """Test that sparse data produces lower confidence stories."""
        facts = create_sparse_facts()
        stories = await extractor.extract_stories(facts)
        
        # Stories from basic extraction should have lower confidence
        if stories:
            assert all(s.confidence <= 0.5 for s in stories)


class TestStoryRetrieval:
    """Tests for story retrieval and matching."""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.mark.asyncio
    async def test_get_stories_for_leadership_question(self, store):
        """Test retrieving stories for a leadership question."""
        # Save some stories
        store.save_story(STARStory(
            id="story-1",
            title="Leadership Story",
            tags=["leadership", "teamwork"],
            confidence=0.9
        ))
        store.save_story(STARStory(
            id="story-2",
            title="Technical Story",
            tags=["technical", "innovation"],
            confidence=0.8
        ))
        
        extractor = StoryExtractor(memory_store=store)
        
        stories = await extractor.get_stories_for_question(
            "Tell me about a time you led a team through a difficult project"
        )
        
        # Leadership story should be ranked higher
        assert len(stories) >= 1

    @pytest.mark.asyncio
    async def test_get_stories_for_conflict_question(self, store):
        """Test retrieving stories for a conflict question."""
        store.save_story(STARStory(
            id="story-1",
            title="Conflict Resolution",
            tags=["conflict", "communication"],
            confidence=0.85
        ))
        store.save_story(STARStory(
            id="story-2",
            title="Technical Achievement",
            tags=["technical"],
            confidence=0.9
        ))
        
        extractor = StoryExtractor(memory_store=store)
        
        stories = await extractor.get_stories_for_question(
            "Describe a situation where you had a conflict with a coworker"
        )
        
        assert len(stories) >= 1


class TestTitleGeneration:
    """Tests for story title generation."""

    @pytest.fixture
    def extractor(self):
        return StoryExtractor()

    def test_generate_leadership_title(self, extractor):
        """Test title generation for leadership achievement."""
        title = extractor._generate_title("Led a team of engineers to complete migration")
        assert "Leadership" in title or "Story" in title

    def test_generate_technical_title(self, extractor):
        """Test title generation for technical achievement."""
        title = extractor._generate_title("Built distributed caching system")
        assert len(title) > 5

    def test_generate_optimization_title(self, extractor):
        """Test title generation for optimization achievement."""
        title = extractor._generate_title("Reduced latency by 40%")
        assert "Optimization" in title or "Story" in title


class TestFormatting:
    """Tests for formatting methods."""

    @pytest.fixture
    def extractor(self):
        return StoryExtractor()

    def test_format_career_info(self, extractor):
        """Test career info formatting."""
        facts = create_sample_facts()
        career_info = extractor._format_career_info(facts)
        
        assert "Google" in career_info
        assert "Staff Software Engineer" in career_info

    def test_format_achievements(self, extractor):
        """Test achievements formatting."""
        facts = create_sample_facts()
        achievements_info = extractor._format_achievements(facts)
        
        assert "Kubernetes" in achievements_info or "migration" in achievements_info.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
