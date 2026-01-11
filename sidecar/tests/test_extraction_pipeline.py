"""
Tests for ExtractionPipeline (STORY-058).

Tests cover:
- Full pipeline execution
- Progress callbacks
- Error handling and partial recovery
- Incremental updates
- Background task management
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
import uuid

from src.extraction import ExtractionPipeline, ExtractionResult
from src.memory.models import (
    DocumentType,
    ExtractedFacts,
    DocumentSummary,
    STARStory,
    CandidateProfile,
    SkillEntry,
    Achievement,
)


class TestExtractionPipelineBasic:
    """Basic pipeline tests."""
    
    def test_init(self):
        """Test pipeline initialization."""
        pipeline = ExtractionPipeline()
        assert pipeline.llm_provider is None
        assert pipeline.memory_store is None
        assert pipeline.summarizer is not None
        assert pipeline.fact_extractor is not None
        assert pipeline.story_extractor is not None
        assert pipeline.profile_generator is not None
    
    def test_init_with_providers(self):
        """Test pipeline with LLM and memory store."""
        mock_llm = MagicMock()
        mock_store = MagicMock()
        
        pipeline = ExtractionPipeline(
            llm_provider=mock_llm,
            memory_store=mock_store
        )
        
        assert pipeline.llm_provider == mock_llm
        assert pipeline.memory_store == mock_store
    
    def test_set_llm_provider(self):
        """Test setting LLM provider propagates to extractors."""
        pipeline = ExtractionPipeline()
        mock_llm = MagicMock()
        
        pipeline.set_llm_provider(mock_llm)
        
        assert pipeline.llm_provider == mock_llm
    
    def test_set_memory_store(self):
        """Test setting memory store propagates to extractors."""
        pipeline = ExtractionPipeline()
        mock_store = MagicMock()
        
        pipeline.set_memory_store(mock_store)
        
        assert pipeline.memory_store == mock_store


class TestExtractionResult:
    """Test ExtractionResult dataclass."""
    
    def test_result_creation(self):
        """Test creating an extraction result."""
        result = ExtractionResult(
            document_id="doc-123",
            document_type=DocumentType.RESUME,
            filename="resume.pdf"
        )
        
        assert result.document_id == "doc-123"
        assert result.document_type == DocumentType.RESUME
        assert result.success is True
        assert result.summary is None
        assert result.facts is None
        assert len(result.stories) == 0
    
    def test_result_to_dict(self):
        """Test result serialization."""
        result = ExtractionResult(
            document_id="doc-123",
            document_type=DocumentType.RESUME,
            filename="resume.pdf",
            success=True,
            duration_ms=1500.0
        )
        
        data = result.to_dict()
        
        assert data["document_id"] == "doc-123"
        assert data["document_type"] == "resume"
        assert data["success"] is True
        assert data["duration_ms"] == 1500.0


class TestPipelineProcessing:
    """Test document processing through pipeline."""
    
    @pytest.fixture
    def mock_extractors(self):
        """Create mock extractors."""
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = AsyncMock(return_value=DocumentSummary(
            document_id="doc-1",
            document_type=DocumentType.RESUME,
            filename="test.pdf",
            document_summary="Test summary",
            key_points=["Point 1", "Point 2"]
        ))
        
        mock_fact_extractor = MagicMock()
        mock_fact_extractor.extract_facts = AsyncMock(return_value=ExtractedFacts(
            skills=[SkillEntry(name="Python", years=5)],
            achievements=[Achievement(description="Built system")],
            total_experience_years=5,
            current_role="Engineer"
        ))
        
        mock_story_extractor = MagicMock()
        mock_story_extractor.extract_stories = AsyncMock(return_value=[
            STARStory(id="story-1", title="Test Story", situation="Test", task="Test", action="Test", result="Test")
        ])
        
        return mock_summarizer, mock_fact_extractor, mock_story_extractor
    
    @pytest.mark.asyncio
    async def test_process_document_basic(self, mock_extractors):
        """Test basic document processing."""
        mock_summarizer, mock_fact_extractor, mock_story_extractor = mock_extractors
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        pipeline.story_extractor = mock_story_extractor
        
        result = await pipeline.process_document(
            document_id="doc-1",
            text="Sample resume text",
            document_type=DocumentType.RESUME,
            filename="resume.pdf"
        )
        
        assert result.success is True
        assert result.document_id == "doc-1"
        assert result.summary is not None
        assert result.facts is not None
        assert len(result.stories) == 1
        assert result.duration_ms >= 0  # May be 0 on fast systems
    
    @pytest.mark.asyncio
    async def test_process_document_with_progress(self, mock_extractors):
        """Test progress callbacks are called."""
        mock_summarizer, mock_fact_extractor, mock_story_extractor = mock_extractors
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        pipeline.story_extractor = mock_story_extractor
        
        progress_calls = []
        
        async def track_progress(stage: str, progress: float, message: str = ""):
            progress_calls.append((stage, progress, message))
        
        await pipeline.process_document(
            document_id="doc-1",
            text="Sample text",
            document_type=DocumentType.RESUME,
            filename="test.pdf",
            progress_callback=track_progress
        )
        
        # Verify progress was reported
        assert len(progress_calls) > 0
        
        # Check key stages were reported
        stages = [p[0] for p in progress_calls]
        assert "parsing" in stages
        assert "summarizing" in stages
        assert "extracting_facts" in stages
        assert "complete" in stages
        
        # Progress should increase
        progress_values = [p[1] for p in progress_calls]
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i-1]
    
    @pytest.mark.asyncio
    async def test_process_jd_skips_stories(self, mock_extractors):
        """Test that JD processing skips story extraction."""
        mock_summarizer, mock_fact_extractor, mock_story_extractor = mock_extractors
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        pipeline.story_extractor = mock_story_extractor
        
        result = await pipeline.process_document(
            document_id="doc-1",
            text="Job description text",
            document_type=DocumentType.JOB_DESCRIPTION,
            filename="job.pdf"
        )
        
        assert result.success is True
        assert len(result.stories) == 0
        mock_story_extractor.extract_stories.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_partial_failure_continues(self):
        """Test that pipeline continues after partial failures."""
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = AsyncMock(side_effect=Exception("Summarization failed"))
        
        mock_fact_extractor = MagicMock()
        mock_fact_extractor.extract_facts = AsyncMock(return_value=ExtractedFacts(
            current_role="Engineer"
        ))
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        
        result = await pipeline.process_document(
            document_id="doc-1",
            text="Sample text",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        )
        
        # Should still succeed overall
        assert result.success is True
        assert result.summary is None  # Failed
        assert result.facts is not None  # Succeeded
        assert len(result.warnings) > 0


class TestBackgroundProcessing:
    """Test background task management."""
    
    @pytest.mark.asyncio
    async def test_background_processing(self):
        """Test starting extraction in background."""
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = AsyncMock(return_value=DocumentSummary(
            document_id="doc-1",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        ))
        
        mock_fact_extractor = MagicMock()
        mock_fact_extractor.extract_facts = AsyncMock(return_value=ExtractedFacts())
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        
        task_id = await pipeline.process_document_background(
            document_id="doc-1",
            text="Sample text",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        )
        
        assert task_id is not None
        assert pipeline.get_active_extraction_count() >= 0
        
        # Wait for completion
        task = pipeline.get_extraction_task(task_id)
        if task:
            await task
    
    @pytest.mark.asyncio
    async def test_cancel_extraction(self):
        """Test canceling an extraction."""
        async def slow_summarize(*args, **kwargs):
            await asyncio.sleep(10)
            return DocumentSummary(document_id="doc-1")
        
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = slow_summarize
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        
        task_id = await pipeline.process_document_background(
            document_id="doc-1",
            text="Sample text",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        )
        
        # Cancel immediately
        await asyncio.sleep(0.01)
        cancelled = pipeline.cancel_extraction(task_id)
        
        assert cancelled is True
        assert pipeline.get_extraction_task(task_id) is None


class TestPipelineWithMemoryStore:
    """Test pipeline integration with MemoryStore."""
    
    @pytest.mark.asyncio
    async def test_saves_to_memory_store(self):
        """Test that results are saved to memory store."""
        mock_store = MagicMock()
        mock_store.get_all_document_summaries.return_value = []
        mock_store.get_all_facts.return_value = None
        mock_store.get_profile.return_value = None
        
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = AsyncMock(return_value=DocumentSummary(
            document_id="doc-1",
            document_type=DocumentType.RESUME,
            filename="test.pdf",
            key_points=["Point 1"]
        ))
        mock_summarizer.set_memory_store = MagicMock()
        mock_summarizer.set_llm_provider = MagicMock()
        
        mock_fact_extractor = MagicMock()
        mock_fact_extractor.extract_facts = AsyncMock(return_value=ExtractedFacts(
            current_role="Engineer",
            skills=[SkillEntry(name="Python")]
        ))
        mock_fact_extractor.set_memory_store = MagicMock()
        mock_fact_extractor.set_llm_provider = MagicMock()
        
        pipeline = ExtractionPipeline(memory_store=mock_store)
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        
        await pipeline.process_document(
            document_id="doc-1",
            text="Sample text",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        )
        
        # Profile should be generated and saved
        mock_store.save_profile.assert_called()


class TestPipelineStats:
    """Test pipeline statistics."""
    
    def test_get_stats(self):
        """Test getting pipeline stats."""
        mock_llm = MagicMock()
        mock_store = MagicMock()
        
        pipeline = ExtractionPipeline(
            llm_provider=mock_llm,
            memory_store=mock_store
        )
        
        stats = pipeline.get_pipeline_stats()
        
        assert stats["has_llm_provider"] is True
        assert stats["has_memory_store"] is True
        assert "stages" in stats
        assert len(stats["stages"]) > 0


class TestMultipleDocuments:
    """Test processing multiple documents."""
    
    @pytest.mark.asyncio
    async def test_process_multiple(self):
        """Test processing multiple documents."""
        mock_summarizer = MagicMock()
        mock_summarizer.summarize = AsyncMock(return_value=DocumentSummary(
            document_id="doc",
            document_type=DocumentType.RESUME,
            filename="test.pdf"
        ))
        
        mock_fact_extractor = MagicMock()
        mock_fact_extractor.extract_facts = AsyncMock(return_value=ExtractedFacts())
        
        pipeline = ExtractionPipeline()
        pipeline.summarizer = mock_summarizer
        pipeline.fact_extractor = mock_fact_extractor
        
        documents = [
            {"document_id": "doc-1", "text": "Resume 1", "document_type": DocumentType.RESUME, "filename": "resume1.pdf"},
            {"document_id": "doc-2", "text": "JD 1", "document_type": DocumentType.JOB_DESCRIPTION, "filename": "jd.pdf"},
        ]
        
        progress_calls = []
        async def track_progress(stage, progress, msg=None):
            progress_calls.append((stage, progress))
        
        results = await pipeline.process_multiple_documents(
            documents=documents,
            progress_callback=track_progress
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
