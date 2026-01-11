"""
Tests for the Memory Store module (STORY-053).

Tests cover:
- Database creation and schema
- Document summary CRUD
- Facts extraction CRUD
- STAR story CRUD
- Candidate profile operations
- Session claim management
- Concurrent access safety
"""

import pytest
import tempfile
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from src.memory import (
    MemoryStore,
    ExtractedFacts,
    SkillEntry,
    CareerEntry,
    Achievement,
    Education,
    STARStory,
    CandidateProfile,
    SessionClaim,
    DocumentSummary,
)
from src.memory.models import DocumentType, SkillProficiency, ClaimType


class TestMemoryStoreCreation:
    """Tests for database creation and initialization."""

    def test_database_creation_default_path(self):
        """Verify database is created at default path."""
        store = MemoryStore()
        try:
            assert os.path.exists(store.db_path)
            assert store.db_path.endswith("memory.db")
        finally:
            store.close()

    def test_database_creation_custom_path(self):
        """Verify database is created at custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            try:
                assert os.path.exists(db_path)
            finally:
                store.close()

    def test_schema_tables_exist(self):
        """Verify all required tables are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            try:
                stats = store.get_stats()
                expected_tables = ["documents", "facts", "stories", "candidate_profile", "session_claims"]
                for table in expected_tables:
                    assert table in stats, f"Missing table: {table}"
                    assert stats[table] == 0  # Initially empty
            finally:
                store.close()


class TestDocumentSummaryOperations:
    """Tests for document summary CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    def test_save_and_get_document_summary(self, store):
        """Test saving and retrieving a document summary."""
        summary = DocumentSummary(
            document_id="doc-1",
            document_type=DocumentType.RESUME,
            filename="resume.pdf",
            document_summary="Experienced software engineer with 10 years...",
            section_summaries={
                "experience": "Worked at Google, Meta, startup...",
                "skills": "Python, TypeScript, Rust...",
            },
            key_points=[
                "10 years experience",
                "Full-stack expertise",
                "Led teams of 8+",
            ],
            uploaded_at=datetime.now(),
        )

        # Save
        doc_id = store.save_document_summary(summary)
        assert doc_id == "doc-1"

        # Retrieve
        retrieved = store.get_document_summary("doc-1")
        assert retrieved is not None
        assert retrieved.document_id == "doc-1"
        assert retrieved.document_type == DocumentType.RESUME
        assert retrieved.filename == "resume.pdf"
        assert "software engineer" in retrieved.document_summary
        assert "experience" in retrieved.section_summaries
        assert len(retrieved.key_points) == 3

    def test_get_all_document_summaries(self, store):
        """Test retrieving all document summaries."""
        # Save multiple documents
        for i in range(3):
            summary = DocumentSummary(
                document_id=f"doc-{i}",
                document_type=DocumentType.RESUME if i == 0 else DocumentType.JOB_DESCRIPTION,
                filename=f"document_{i}.pdf",
                document_summary=f"Summary for document {i}",
            )
            store.save_document_summary(summary)

        # Retrieve all
        all_summaries = store.get_all_document_summaries()
        assert len(all_summaries) == 3

    def test_delete_document(self, store):
        """Test deleting a document."""
        summary = DocumentSummary(
            document_id="doc-to-delete",
            document_type=DocumentType.OTHER,
            filename="delete_me.pdf",
        )
        store.save_document_summary(summary)

        # Verify exists
        assert store.get_document_summary("doc-to-delete") is not None

        # Delete
        deleted = store.delete_document("doc-to-delete")
        assert deleted is True

        # Verify gone
        assert store.get_document_summary("doc-to-delete") is None


class TestFactsOperations:
    """Tests for extracted facts CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    @pytest.fixture
    def sample_facts(self):
        """Create sample extracted facts."""
        return ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8, proficiency=SkillProficiency.EXPERT),
                SkillEntry(name="TypeScript", years=5, proficiency=SkillProficiency.PROFICIENT),
                SkillEntry(name="Rust", years=2, proficiency=SkillProficiency.FAMILIAR),
            ],
            timeline=[
                CareerEntry(
                    company="Google",
                    role="Senior Software Engineer",
                    start_date="2020-01",
                    end_date=None,
                    highlights=["Led ML platform team", "Reduced latency by 40%"],
                    metrics=["40% latency reduction", "$2M cost savings"],
                    is_current=True,
                ),
                CareerEntry(
                    company="Meta",
                    role="Software Engineer",
                    start_date="2017-06",
                    end_date="2019-12",
                    highlights=["Built real-time analytics"],
                ),
            ],
            achievements=[
                Achievement(
                    description="Led migration to microservices",
                    metrics=["Zero downtime", "40% latency improvement"],
                    context="Google",
                    tags=["leadership", "architecture"],
                ),
            ],
            education=[
                Education(
                    institution="MIT",
                    degree="MS Computer Science",
                    year=2017,
                ),
            ],
            certifications=["AWS Solutions Architect", "GCP Professional"],
            total_experience_years=8,
            current_role="Senior Software Engineer",
            current_company="Google",
            industries=["Tech", "Cloud"],
        )

    def test_save_and_retrieve_facts(self, store, sample_facts):
        """Test saving and retrieving extracted facts."""
        # First save a document
        summary = DocumentSummary(document_id="doc-facts", document_type=DocumentType.RESUME)
        store.save_document_summary(summary)

        # Save facts
        store.save_facts("doc-facts", sample_facts)

        # Retrieve
        retrieved = store.get_facts_for_document("doc-facts")
        assert retrieved is not None
        assert len(retrieved.skills) == 3
        assert len(retrieved.timeline) == 2
        assert len(retrieved.achievements) == 1
        assert len(retrieved.education) == 1
        assert retrieved.total_experience_years == 8
        assert retrieved.current_role == "Senior Software Engineer"

    def test_get_all_facts_merged(self, store):
        """Test merging facts from multiple documents."""
        # Save first document with facts
        summary1 = DocumentSummary(document_id="doc-1", document_type=DocumentType.RESUME)
        store.save_document_summary(summary1)
        facts1 = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=8)],
            total_experience_years=8,
        )
        store.save_facts("doc-1", facts1)

        # Save second document with additional facts
        summary2 = DocumentSummary(document_id="doc-2", document_type=DocumentType.JOB_DESCRIPTION)
        store.save_document_summary(summary2)
        facts2 = ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8),  # Duplicate
                SkillEntry(name="Go", years=3),  # New
            ],
            total_experience_years=8,
        )
        store.save_facts("doc-2", facts2)

        # Get merged facts
        merged = store.get_all_facts()
        skill_names = [s.name for s in merged.skills]
        assert "Python" in skill_names
        assert "Go" in skill_names
        # Should deduplicate Python
        assert skill_names.count("Python") == 1


class TestStoryOperations:
    """Tests for STAR story CRUD operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    @pytest.fixture
    def sample_story(self):
        """Create a sample STAR story."""
        return STARStory(
            id="story-1",
            title="The Migration Crisis",
            situation="Our legacy monolith was causing 2-hour deployments and frequent outages.",
            task="As tech lead, I needed to migrate to microservices with zero customer impact.",
            action="I led an 8-person team through a phased migration over 6 weeks. We used feature flags, implemented comprehensive monitoring, and ran parallel systems during transition.",
            result="Achieved zero-downtime migration, reduced deployment time from 2 hours to 10 minutes, and improved system reliability by 99.9%.",
            metrics=["Zero downtime", "2 hours -> 10 minutes deployment", "99.9% reliability"],
            tags=["leadership", "architecture", "migration", "crisis"],
            source_company="Google",
            source_role="Tech Lead",
            opening_line="When I was at Google, our deployment process was causing significant pain...",
            twenty_second_version="Led 8-person team to migrate legacy monolith to microservices in 6 weeks with zero downtime, reducing deployments from 2 hours to 10 minutes.",
            confidence=0.95,
        )

    def test_save_and_retrieve_story(self, store, sample_story):
        """Test saving and retrieving a STAR story."""
        story_id = store.save_story(sample_story)
        assert story_id == "story-1"

        retrieved = store.get_story("story-1")
        assert retrieved is not None
        assert retrieved.title == "The Migration Crisis"
        assert retrieved.source_company == "Google"
        assert len(retrieved.tags) == 4
        assert "leadership" in retrieved.tags

    def test_get_all_stories(self, store, sample_story):
        """Test retrieving all stories."""
        # Save multiple stories
        store.save_story(sample_story)

        story2 = STARStory(
            id="story-2",
            title="The Performance Crisis",
            tags=["performance", "optimization"],
            confidence=0.8,
        )
        store.save_story(story2)

        all_stories = store.get_all_stories()
        assert len(all_stories) == 2

    def test_get_stories_by_tag(self, store, sample_story):
        """Test filtering stories by tag."""
        store.save_story(sample_story)

        story2 = STARStory(
            id="story-2",
            title="The Performance Issue",
            tags=["performance", "debugging"],
        )
        store.save_story(story2)

        # Find leadership stories
        leadership_stories = store.get_stories_by_tag("leadership")
        assert len(leadership_stories) == 1
        assert leadership_stories[0].title == "The Migration Crisis"

        # Find stories with no matches
        no_match = store.get_stories_by_tag("nonexistent")
        assert len(no_match) == 0

    def test_delete_story(self, store, sample_story):
        """Test deleting a story."""
        store.save_story(sample_story)
        assert store.get_story("story-1") is not None

        deleted = store.delete_story("story-1")
        assert deleted is True
        assert store.get_story("story-1") is None

    def test_update_story(self, store, sample_story):
        """Test updating an existing story."""
        store.save_story(sample_story)

        # Update
        sample_story.confidence = 0.99
        sample_story.tags.append("updated")
        store.save_story(sample_story)

        retrieved = store.get_story("story-1")
        assert retrieved.confidence == 0.99
        assert "updated" in retrieved.tags


class TestProfileOperations:
    """Tests for candidate profile operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    @pytest.fixture
    def sample_profile(self):
        """Create a sample candidate profile."""
        return CandidateProfile(
            id="profile-1",
            profile_text="## Candidate: John Doe\nSenior Engineer with 10 years...",
            current_role="Senior Software Engineer",
            total_experience_years=10,
            core_skills=["Python", "TypeScript", "System Design"],
            key_achievements=["Led migration", "Built ML platform", "Scaled to 1M users"],
            target_role="Staff Engineer",
            target_company="OpenAI",
            strengths=["Technical leadership", "System architecture"],
            gaps=["Limited AI/ML experience"],
        )

    def test_save_and_get_profile(self, store, sample_profile):
        """Test saving and retrieving candidate profile."""
        profile_id = store.save_profile(sample_profile)
        assert profile_id == "profile-1"

        retrieved = store.get_profile()
        assert retrieved is not None
        assert retrieved.current_role == "Senior Software Engineer"
        assert retrieved.total_experience_years == 10
        assert len(retrieved.core_skills) == 3
        assert retrieved.target_company == "OpenAI"

    def test_profile_singleton(self, store, sample_profile):
        """Test that only one profile is maintained (singleton)."""
        store.save_profile(sample_profile)

        # Save another profile
        new_profile = CandidateProfile(
            id="profile-2",
            current_role="Staff Engineer",
            total_experience_years=12,
        )
        store.save_profile(new_profile)

        # Should only have one profile (the new one)
        retrieved = store.get_profile()
        assert retrieved is not None
        assert retrieved.id == "profile-2"
        assert retrieved.current_role == "Staff Engineer"

    def test_profile_prompt_injection(self, store, sample_profile):
        """Test profile text generation for prompt injection."""
        store.save_profile(sample_profile)

        retrieved = store.get_profile()
        prompt_text = retrieved.get_prompt_injection()

        # Should return profile_text if set
        assert "Candidate" in prompt_text or "John Doe" in prompt_text
        assert len(prompt_text) > 50  # Should be non-trivial

    def test_profile_prompt_injection_generated(self, store):
        """Test profile text generation when no profile_text is set."""
        # Create profile without explicit profile_text
        profile = CandidateProfile(
            current_role="Staff Engineer",
            total_experience_years=12,
            core_skills=["Python", "Go", "Kubernetes"],
            key_achievements=["Built ML platform", "Led team of 15"],
            strengths=["System design", "Leadership"],
        )
        store.save_profile(profile)

        retrieved = store.get_profile()
        prompt_text = retrieved.get_prompt_injection()

        # Should generate from structured data
        assert "Staff Engineer" in prompt_text
        assert "12" in prompt_text
        assert len(prompt_text) > 100

    def test_delete_profile(self, store, sample_profile):
        """Test deleting the profile."""
        store.save_profile(sample_profile)
        assert store.get_profile() is not None

        deleted = store.delete_profile()
        assert deleted is True
        assert store.get_profile() is None


class TestSessionClaimOperations:
    """Tests for session claim tracking."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    def test_add_and_get_claims(self, store):
        """Test adding and retrieving session claims."""
        session_id = "session-1"

        # Add claims
        store.add_claim(
            session_id=session_id,
            claim_text="I have 8 years of experience",
            claim_value="8 years",
            claim_type=ClaimType.EXPERIENCE_YEARS,
            context="Answering experience question",
        )
        store.add_claim(
            session_id=session_id,
            claim_text="I led a team of 12 engineers",
            claim_value="12",
            claim_type=ClaimType.TEAM_SIZE,
        )

        # Retrieve
        claims = store.get_session_claims(session_id)
        assert len(claims) == 2
        assert claims[0].claim_value == "8 years"
        assert claims[1].claim_type == ClaimType.TEAM_SIZE

    def test_claims_isolated_by_session(self, store):
        """Test that claims are isolated by session."""
        store.add_claim("session-1", "Claim 1", "value1", ClaimType.OTHER)
        store.add_claim("session-2", "Claim 2", "value2", ClaimType.OTHER)

        session1_claims = store.get_session_claims("session-1")
        session2_claims = store.get_session_claims("session-2")

        assert len(session1_claims) == 1
        assert len(session2_claims) == 1
        assert session1_claims[0].claim_text == "Claim 1"
        assert session2_claims[0].claim_text == "Claim 2"

    def test_clear_session_claims(self, store):
        """Test clearing claims for a session."""
        session_id = "session-clear"

        # Add claims
        store.add_claim(session_id, "Claim 1", "v1", ClaimType.OTHER)
        store.add_claim(session_id, "Claim 2", "v2", ClaimType.OTHER)
        store.add_claim(session_id, "Claim 3", "v3", ClaimType.OTHER)

        # Verify 3 claims
        assert len(store.get_session_claims(session_id)) == 3

        # Clear
        count = store.clear_session_claims(session_id)
        assert count == 3
        assert len(store.get_session_claims(session_id)) == 0

    def test_get_claims_by_type(self, store):
        """Test filtering claims by type."""
        session_id = "session-typed"

        store.add_claim(session_id, "8 years exp", "8", ClaimType.EXPERIENCE_YEARS)
        store.add_claim(session_id, "Team of 5", "5", ClaimType.TEAM_SIZE)
        store.add_claim(session_id, "10 years exp", "10", ClaimType.EXPERIENCE_YEARS)

        exp_claims = store.get_claims_by_type(session_id, ClaimType.EXPERIENCE_YEARS)
        assert len(exp_claims) == 2

        team_claims = store.get_claims_by_type(session_id, ClaimType.TEAM_SIZE)
        assert len(team_claims) == 1


class TestConcurrentAccess:
    """Tests for concurrent database access."""

    def test_concurrent_writes(self):
        """Test that concurrent writes don't cause issues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_concurrent.db")
            store = MemoryStore(db_path=db_path, pool_size=5)

            errors = []
            success_count = [0]

            def write_story(i):
                try:
                    story = STARStory(
                        id=f"story-{i}",
                        title=f"Story {i}",
                        tags=["concurrent"],
                    )
                    store.save_story(story)
                    success_count[0] += 1
                except Exception as e:
                    errors.append(str(e))

            # Launch multiple threads
            threads = []
            for i in range(10):
                t = threading.Thread(target=write_story, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all to complete
            for t in threads:
                t.join()

            store.close()

            # All writes should succeed
            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert success_count[0] == 10

    def test_concurrent_reads_writes(self):
        """Test concurrent reads and writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_mixed.db")
            store = MemoryStore(db_path=db_path, pool_size=5)

            # Pre-populate some data
            for i in range(5):
                story = STARStory(id=f"pre-{i}", title=f"Pre Story {i}")
                store.save_story(story)

            errors = []
            read_counts = []
            write_success = [0]

            def read_stories():
                try:
                    stories = store.get_all_stories()
                    read_counts.append(len(stories))
                except Exception as e:
                    errors.append(f"Read error: {e}")

            def write_story(i):
                try:
                    story = STARStory(id=f"new-{i}", title=f"New Story {i}")
                    store.save_story(story)
                    write_success[0] += 1
                except Exception as e:
                    errors.append(f"Write error: {e}")

            # Launch mixed threads
            threads = []
            for i in range(10):
                if i % 2 == 0:
                    t = threading.Thread(target=read_stories)
                else:
                    t = threading.Thread(target=write_story, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            store.close()

            assert len(errors) == 0, f"Errors: {errors}"
            assert write_success[0] == 5  # 5 write threads
            assert len(read_counts) == 5  # 5 read threads


class TestDataModelSerialization:
    """Tests for data model serialization/deserialization."""

    def test_extracted_facts_json_roundtrip(self):
        """Test ExtractedFacts JSON serialization."""
        facts = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=8, proficiency=SkillProficiency.EXPERT)],
            total_experience_years=8,
            current_role="Engineer",
        )

        json_str = facts.to_json()
        restored = ExtractedFacts.from_json(json_str)

        assert restored.total_experience_years == 8
        assert restored.current_role == "Engineer"
        assert len(restored.skills) == 1
        assert restored.skills[0].name == "Python"

    def test_star_story_json_roundtrip(self):
        """Test STARStory JSON serialization."""
        story = STARStory(
            id="test-story",
            title="Test Title",
            situation="Test situation",
            tags=["test", "json"],
            metrics=["100%", "$1M"],
            confidence=0.95,
        )

        json_str = story.to_json()
        restored = STARStory.from_json(json_str)

        assert restored.id == "test-story"
        assert restored.title == "Test Title"
        assert restored.tags == ["test", "json"]
        assert restored.confidence == 0.95

    def test_candidate_profile_json_roundtrip(self):
        """Test CandidateProfile JSON serialization."""
        profile = CandidateProfile(
            profile_text="Test profile",
            core_skills=["A", "B", "C"],
            strengths=["X", "Y"],
        )

        json_str = profile.to_json()
        restored = CandidateProfile.from_json(json_str)

        assert restored.profile_text == "Test profile"
        assert restored.core_skills == ["A", "B", "C"]
        assert restored.strengths == ["X", "Y"]

    def test_facts_merge(self):
        """Test merging ExtractedFacts."""
        facts1 = ExtractedFacts(
            skills=[SkillEntry(name="Python", years=5)],
            industries=["Tech"],
            total_experience_years=5,
        )
        facts2 = ExtractedFacts(
            skills=[
                SkillEntry(name="Python", years=8),  # Duplicate
                SkillEntry(name="Go", years=2),  # New
            ],
            industries=["Finance"],
            total_experience_years=8,
        )

        merged = facts1.merge_with(facts2)

        # Should have 2 unique skills (Python deduplicated)
        skill_names = [s.name for s in merged.skills]
        assert "Python" in skill_names
        assert "Go" in skill_names
        assert len([n for n in skill_names if n == "Python"]) == 1

        # Industries merged
        assert "Tech" in merged.industries
        assert "Finance" in merged.industries

        # Max experience kept
        assert merged.total_experience_years == 8


class TestUtilityMethods:
    """Tests for utility methods."""

    @pytest.fixture
    def store(self):
        """Create a temporary store for each test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_memory.db")
            store = MemoryStore(db_path=db_path)
            yield store
            store.close()

    def test_get_stats(self, store):
        """Test statistics retrieval."""
        # Add some data
        store.save_story(STARStory(id="s1", title="Story 1"))
        store.save_story(STARStory(id="s2", title="Story 2"))
        store.save_profile(CandidateProfile(current_role="Engineer"))
        store.add_claim("session", "claim", "value", ClaimType.OTHER)

        stats = store.get_stats()
        assert stats["stories"] == 2
        assert stats["candidate_profile"] == 1
        assert stats["session_claims"] == 1

    def test_clear_all(self, store):
        """Test clearing all data."""
        # Add data
        store.save_story(STARStory(id="s1", title="Story"))
        store.save_profile(CandidateProfile())
        store.add_claim("session", "claim", "value", ClaimType.OTHER)

        # Verify data exists
        stats_before = store.get_stats()
        assert stats_before["stories"] == 1

        # Clear
        store.clear_all()

        # Verify empty
        stats_after = store.get_stats()
        for table, count in stats_after.items():
            assert count == 0, f"{table} should be empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
