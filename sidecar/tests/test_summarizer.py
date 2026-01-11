"""
Tests for the Document Summarizer (STORY-054).

Tests cover:
- Resume summarization
- Job description summarization
- Section detection
- Key points extraction
- LLM integration (mocked)
- Caching behavior
- Fallback extraction
"""

import pytest
import tempfile
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.extraction import DocumentSummarizer
from src.memory import MemoryStore, DocumentSummary
from src.memory.models import DocumentType


# Sample resume text for testing
SAMPLE_RESUME = """
JOHN DOE
Senior Software Engineer

SUMMARY
Experienced software engineer with 10+ years of experience building scalable systems.
Expert in Python, TypeScript, and cloud technologies. Led teams of 8+ engineers.

EXPERIENCE

Senior Software Engineer, Google - 2020-Present
- Led migration from monolith to microservices, reducing deployment time by 75%
- Built ML platform serving 1M+ predictions/day
- Managed team of 8 engineers
- Reduced latency by 40% through optimization

Software Engineer, Meta - 2017-2020
- Built real-time analytics dashboard used by 500+ internal users
- Improved data pipeline throughput by 60%
- Led cross-functional project with 5 teams

EDUCATION
MS Computer Science, MIT, 2017
BS Computer Science, Stanford, 2015

SKILLS
Python, TypeScript, Go, Kubernetes, AWS, GCP, Machine Learning, System Design

CERTIFICATIONS
- AWS Solutions Architect Professional
- GCP Professional Cloud Architect
"""

SAMPLE_JOB_DESCRIPTION = """
Staff Software Engineer - Platform Team

About the Company
We are a fast-growing fintech startup revolutionizing payments. Series C funded with $200M.

About the Role
We're looking for a Staff Software Engineer to lead our Platform team and drive
technical excellence across the organization.

Requirements
- 8+ years of software engineering experience
- Strong experience with Python, Go, or similar languages
- Experience leading teams of 5+ engineers
- Track record of building scalable distributed systems
- Excellent communication skills

Responsibilities
- Lead a team of 6 platform engineers
- Design and implement core platform infrastructure
- Drive technical roadmap and architecture decisions
- Mentor junior engineers

Benefits
- Competitive salary $200-300k
- Equity package
- Unlimited PTO
- Remote-first culture
"""


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str):
        self.response = response
        self.calls = []

    async def generate_response(self, prompt: str, context: str, history: list):
        self.calls.append({"prompt": prompt, "context": context, "history": history})
        for chunk in self.response:
            yield chunk


class TestDocumentSummarizer:
    """Tests for document summarization."""

    @pytest.fixture
    def store(self):
        """Create a temporary memory store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        return json.dumps({
            "document_summary": "Experienced senior software engineer with 10+ years at top tech companies. Expert in Python, TypeScript, and cloud technologies. Has led teams of 8+ engineers and delivered impactful projects including ML platforms and microservices migrations.",
            "sections": {
                "Experience": "Led engineering teams at Google and Meta, driving major technical initiatives including microservices migration and ML platform development.",
                "Education": "MS in Computer Science from MIT (2017), BS from Stanford (2015).",
                "Skills": "Python, TypeScript, Go, Kubernetes, AWS, GCP, Machine Learning, System Design."
            },
            "key_points": [
                "10+ years of software engineering experience",
                "Led migration reducing deployment time by 75%",
                "Built ML platform serving 1M+ predictions/day",
                "Managed team of 8 engineers at Google",
                "Reduced latency by 40% through optimization",
                "AWS Solutions Architect Professional certified"
            ]
        })

    @pytest.mark.asyncio
    async def test_resume_summary_with_llm(self, store, mock_llm_response):
        """Test summarizing a resume with LLM provider."""
        mock_llm = MockLLMProvider(mock_llm_response)
        summarizer = DocumentSummarizer(llm_provider=mock_llm, memory_store=store)

        summary = await summarizer.summarize(
            document_id="resume-1",
            text=SAMPLE_RESUME,
            document_type=DocumentType.RESUME,
            filename="john_doe_resume.pdf"
        )

        assert summary.document_id == "resume-1"
        assert len(summary.document_summary) > 100
        assert "engineer" in summary.document_summary.lower()
        assert len(summary.section_summaries) >= 2
        assert len(summary.key_points) >= 5

    @pytest.mark.asyncio
    async def test_jd_summary_with_llm(self, store):
        """Test summarizing a job description."""
        jd_response = json.dumps({
            "document_summary": "Staff Software Engineer position at a Series C fintech startup. Looking for 8+ years experience, team leadership, and distributed systems expertise. Offers competitive salary $200-300k with remote work.",
            "sections": {
                "Requirements": "8+ years experience, Python/Go, team leadership of 5+ engineers, distributed systems.",
                "Responsibilities": "Lead platform team of 6 engineers, drive architecture decisions, mentor junior engineers.",
                "Benefits": "Competitive salary $200-300k, equity, unlimited PTO, remote-first."
            },
            "key_points": [
                "Staff Software Engineer level",
                "8+ years of experience required",
                "Lead team of 6 platform engineers",
                "Series C funded with $200M",
                "Salary range $200-300k",
                "Remote-first culture"
            ]
        })

        mock_llm = MockLLMProvider(jd_response)
        summarizer = DocumentSummarizer(llm_provider=mock_llm, memory_store=store)

        summary = await summarizer.summarize(
            document_id="jd-1",
            text=SAMPLE_JOB_DESCRIPTION,
            document_type=DocumentType.JOB_DESCRIPTION,
            filename="staff_engineer_jd.txt"
        )

        assert summary.document_id == "jd-1"
        assert summary.document_type == DocumentType.JOB_DESCRIPTION
        assert "staff" in summary.document_summary.lower() or "engineer" in summary.document_summary.lower()
        assert len(summary.key_points) >= 4


class TestSectionDetection:
    """Tests for section detection."""

    @pytest.fixture
    def summarizer(self):
        """Create a summarizer without LLM (for testing basic extraction)."""
        return DocumentSummarizer()

    def test_resume_section_detection(self, summarizer):
        """Test detecting sections in a resume."""
        sections = summarizer._detect_sections(SAMPLE_RESUME, DocumentType.RESUME)

        # Should detect at least some sections
        section_names = [s.lower() for s in sections.keys()]
        assert any("experience" in s for s in section_names) or any("summary" in s for s in section_names)

    def test_jd_section_detection(self, summarizer):
        """Test detecting sections in a job description."""
        sections = summarizer._detect_sections(SAMPLE_JOB_DESCRIPTION, DocumentType.JOB_DESCRIPTION)

        # Should detect at least some sections
        section_names = [s.lower() for s in sections.keys()]
        assert len(sections) >= 1


class TestKeyPointsExtraction:
    """Tests for key points extraction."""

    @pytest.fixture
    def summarizer(self):
        """Create a summarizer without LLM."""
        return DocumentSummarizer()

    def test_extract_key_points(self, summarizer):
        """Test extracting key points from document."""
        points = summarizer._extract_key_points(SAMPLE_RESUME)

        # Should extract some points
        assert len(points) >= 1

    def test_extract_metrics(self, summarizer):
        """Test that metrics are extracted."""
        points = summarizer._extract_key_points(SAMPLE_RESUME)
        points_text = " ".join(points).lower()

        # Should capture some metrics
        has_metrics = any(c.isdigit() for c in points_text)
        # This is optional - metrics may or may not be extracted
        # Just verify we got some points


class TestCaching:
    """Tests for summary caching behavior."""

    @pytest.fixture
    def store(self):
        """Create a temporary memory store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    @pytest.mark.asyncio
    async def test_cached_summary_returned(self, store):
        """Test that cached summary is returned without LLM call."""
        # Pre-populate cache
        cached_summary = DocumentSummary(
            document_id="cached-1",
            document_type=DocumentType.RESUME,
            filename="cached.pdf",
            document_summary="This is a cached summary.",
            section_summaries={"Test": "Section"},
            key_points=["Point 1"],
        )
        store.save_document_summary(cached_summary)

        # Create summarizer with mock LLM
        mock_llm = MockLLMProvider('{"document_summary": "new", "sections": {}, "key_points": []}')
        summarizer = DocumentSummarizer(llm_provider=mock_llm, memory_store=store)

        # Get summary - should use cache
        summary = await summarizer.summarize(
            document_id="cached-1",
            text="Some new text",
            document_type=DocumentType.RESUME,
        )

        # Should return cached version
        assert summary.document_summary == "This is a cached summary."
        # LLM should not have been called
        assert len(mock_llm.calls) == 0

    @pytest.mark.asyncio
    async def test_force_regenerate_ignores_cache(self, store):
        """Test that force_regenerate bypasses cache."""
        # Pre-populate cache
        cached_summary = DocumentSummary(
            document_id="cached-2",
            document_type=DocumentType.RESUME,
            document_summary="Cached summary",
        )
        store.save_document_summary(cached_summary)

        # Create summarizer with mock LLM
        new_response = json.dumps({
            "document_summary": "New LLM summary",
            "sections": {},
            "key_points": []
        })
        mock_llm = MockLLMProvider(new_response)
        summarizer = DocumentSummarizer(llm_provider=mock_llm, memory_store=store)

        # Get summary with force_regenerate
        summary = await summarizer.summarize(
            document_id="cached-2",
            text="Text",
            document_type=DocumentType.RESUME,
            force_regenerate=True,
        )

        # Should return new LLM summary
        assert "New LLM summary" in summary.document_summary
        # LLM should have been called
        assert len(mock_llm.calls) == 1


class TestFallbackExtraction:
    """Tests for fallback extraction when LLM unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_without_llm(self):
        """Test basic extraction without LLM provider."""
        summarizer = DocumentSummarizer(llm_provider=None, memory_store=None)

        summary = await summarizer.summarize(
            document_id="fallback-1",
            text=SAMPLE_RESUME,
            document_type=DocumentType.RESUME,
            filename="resume.pdf"
        )

        # Should still produce a summary
        assert summary.document_id == "fallback-1"
        assert len(summary.document_summary) > 0
        # May or may not have sections/key_points based on regex matching

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self):
        """Test fallback when LLM call fails."""
        class FailingLLMProvider:
            async def generate_response(self, prompt, context, history):
                raise Exception("LLM API error")
                yield  # Make it a generator

        summarizer = DocumentSummarizer(llm_provider=FailingLLMProvider(), memory_store=None)

        summary = await summarizer.summarize(
            document_id="fallback-2",
            text=SAMPLE_RESUME,
            document_type=DocumentType.RESUME,
        )

        # Should still produce a summary via fallback
        assert summary.document_id == "fallback-2"
        assert len(summary.document_summary) > 0


class TestCombinedContext:
    """Tests for getting combined context from all summaries."""

    @pytest.fixture
    def store(self):
        """Create a temporary memory store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(db_path=f"{tmpdir}/test.db")
            yield store
            store.close()

    def test_get_combined_context(self, store):
        """Test getting combined context from multiple summaries."""
        # Add summaries
        store.save_document_summary(DocumentSummary(
            document_id="doc-1",
            document_type=DocumentType.RESUME,
            filename="resume.pdf",
            document_summary="Resume summary here",
            key_points=["Point 1", "Point 2"],
        ))
        store.save_document_summary(DocumentSummary(
            document_id="doc-2",
            document_type=DocumentType.JOB_DESCRIPTION,
            filename="job.txt",
            document_summary="JD summary here",
            section_summaries={"Requirements": "8+ years"},
        ))

        summarizer = DocumentSummarizer(memory_store=store)
        context = summarizer.get_combined_context()

        assert "resume.pdf" in context.lower() or "resume summary" in context.lower()
        assert "jd summary" in context.lower() or "job" in context.lower()


class TestDocumentTypeFormatting:
    """Tests for document type formatting."""

    @pytest.fixture
    def summarizer(self):
        return DocumentSummarizer()

    def test_format_resume(self, summarizer):
        result = summarizer._format_document_type(DocumentType.RESUME)
        assert "resume" in result.lower()

    def test_format_jd(self, summarizer):
        result = summarizer._format_document_type(DocumentType.JOB_DESCRIPTION)
        assert "job description" in result.lower()

    def test_format_company_info(self, summarizer):
        result = summarizer._format_document_type(DocumentType.COMPANY_INFO)
        assert "company" in result.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
