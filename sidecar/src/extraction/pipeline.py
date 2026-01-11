"""
Extraction Pipeline - Orchestrates all document extractors.

Coordinates the full extraction workflow:
1. Document summarization
2. Fact extraction
3. STAR story extraction (for resumes)
4. Candidate profile generation

Part of Phase 4: Interview Coach Evolution (STORY-058)
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any, Callable, Awaitable, Dict

from .summarizer import DocumentSummarizer
from .fact_extractor import FactExtractor
from .story_extractor import StoryExtractor
from .profile_generator import ProfileGenerator

from ..memory.models import (
    DocumentSummary,
    ExtractedFacts,
    STARStory,
    CandidateProfile,
    DocumentType,
)


logger = logging.getLogger(__name__)


# Type alias for progress callback
ProgressCallback = Callable[[str, float, Optional[str]], Awaitable[None]]


@dataclass
class ExtractionResult:
    """Result of the extraction pipeline."""
    
    document_id: str
    document_type: DocumentType
    filename: str
    
    # Extracted data
    summary: Optional[DocumentSummary] = None
    facts: Optional[ExtractedFacts] = None
    stories: List[STARStory] = field(default_factory=list)
    profile: Optional[CandidateProfile] = None
    
    # Metadata
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0
    
    # Status
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value if isinstance(self.document_type, DocumentType) else self.document_type,
            "filename": self.filename,
            "has_summary": self.summary is not None,
            "has_facts": self.facts is not None,
            "story_count": len(self.stories),
            "has_profile": self.profile is not None,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass 
class PipelineStage:
    """Represents a stage in the extraction pipeline."""
    name: str
    display_name: str
    weight: float  # Relative weight for progress calculation


# Pipeline stages with weights
PIPELINE_STAGES = [
    PipelineStage("parsing", "Parsing document", 0.1),
    PipelineStage("summarizing", "Generating summary", 0.25),
    PipelineStage("extracting_facts", "Extracting facts", 0.25),
    PipelineStage("extracting_stories", "Extracting stories", 0.25),
    PipelineStage("generating_profile", "Generating profile", 0.1),
    PipelineStage("complete", "Complete", 0.05),
]


class ExtractionPipeline:
    """
    Orchestrates the full document extraction workflow.
    
    Coordinates summarization, fact extraction, story extraction,
    and profile generation in a unified pipeline with progress tracking.
    """
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None,
    ):
        """
        Initialize the extraction pipeline.
        
        Args:
            llm_provider: LLM provider for AI-powered extraction
            memory_store: Memory store for persisting results
        """
        self.llm_provider = llm_provider
        self.memory_store = memory_store
        
        # Initialize extractors
        self.summarizer = DocumentSummarizer(llm_provider, memory_store)
        self.fact_extractor = FactExtractor(llm_provider, memory_store)
        self.story_extractor = StoryExtractor(llm_provider, memory_store)
        self.profile_generator = ProfileGenerator(memory_store)
        
        # Track active extractions
        self._active_extractions: Dict[str, asyncio.Task] = {}
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set or update the LLM provider for all extractors."""
        self.llm_provider = provider
        self.summarizer.set_llm_provider(provider)
        self.fact_extractor.set_llm_provider(provider)
        self.story_extractor.set_llm_provider(provider)
    
    def set_memory_store(self, store: Any) -> None:
        """Set or update the memory store for all extractors."""
        self.memory_store = store
        self.summarizer.set_memory_store(store)
        self.fact_extractor.set_memory_store(store)
        self.story_extractor.set_memory_store(store)
        self.profile_generator.set_memory_store(store)
    
    async def process_document(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        filename: str = "",
        progress_callback: Optional[ProgressCallback] = None,
        force_regenerate: bool = False,
    ) -> ExtractionResult:
        """
        Process a document through the full extraction pipeline.
        
        Args:
            document_id: Unique identifier for the document
            text: Full text content of the document
            document_type: Type of document (resume, JD, etc.)
            filename: Original filename
            progress_callback: Async callback for progress updates
                               Signature: (stage: str, progress: float, message: str) -> None
            force_regenerate: If True, regenerate even if cached
            
        Returns:
            ExtractionResult with all extracted data
        """
        started_at = datetime.now()
        result = ExtractionResult(
            document_id=document_id,
            document_type=document_type,
            filename=filename,
            started_at=started_at,
        )
        
        async def report_progress(stage: str, progress: float, message: str = ""):
            """Helper to report progress."""
            if progress_callback:
                try:
                    await progress_callback(stage, progress, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        try:
            # Stage 1: Parsing (already done - text is provided)
            await report_progress("parsing", 0.1, f"Processing {filename}")
            logger.info(f"Starting extraction for {filename} ({document_type.value})")
            
            # Stage 2: Summarization
            await report_progress("summarizing", 0.15, "Generating document summary")
            try:
                result.summary = await self.summarizer.summarize(
                    document_id=document_id,
                    text=text,
                    document_type=document_type,
                    filename=filename,
                    force_regenerate=force_regenerate,
                )
                logger.info(f"Summary generated: {len(result.summary.key_points)} key points")
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                result.warnings.append(f"Summarization failed: {str(e)}")
            
            await report_progress("summarizing", 0.35, "Summary complete")
            
            # Stage 3: Fact Extraction
            await report_progress("extracting_facts", 0.4, "Extracting structured facts")
            try:
                result.facts = await self.fact_extractor.extract_facts(
                    document_id=document_id,
                    text=text,
                    document_type=document_type,
                    force_regenerate=force_regenerate,
                )
                logger.info(
                    f"Facts extracted: {len(result.facts.skills)} skills, "
                    f"{len(result.facts.achievements)} achievements"
                )
            except Exception as e:
                logger.error(f"Fact extraction failed: {e}")
                result.warnings.append(f"Fact extraction failed: {str(e)}")
            
            await report_progress("extracting_facts", 0.6, "Facts extracted")
            
            # Stage 4: Story Extraction (only for resumes)
            if document_type == DocumentType.RESUME and result.facts:
                await report_progress("extracting_stories", 0.65, "Extracting STAR stories")
                try:
                    result.stories = await self.story_extractor.extract_stories(
                        facts=result.facts,
                        force_regenerate=force_regenerate,
                    )
                    logger.info(f"Stories extracted: {len(result.stories)}")
                except Exception as e:
                    logger.error(f"Story extraction failed: {e}")
                    result.warnings.append(f"Story extraction failed: {str(e)}")
            else:
                await report_progress("extracting_stories", 0.65, "Skipping stories (not a resume)")
            
            await report_progress("extracting_stories", 0.85, "Stories complete")
            
            # Stage 5: Profile Generation
            await report_progress("generating_profile", 0.88, "Generating candidate profile")
            try:
                # Get all summaries for context
                all_summaries = [result.summary] if result.summary else []
                if self.memory_store:
                    existing_summaries = self.memory_store.get_all_document_summaries()
                    # Add existing summaries that aren't the current one
                    for s in existing_summaries:
                        if s.document_id != document_id:
                            all_summaries.append(s)
                
                # Get merged facts
                merged_facts = result.facts
                if self.memory_store and result.facts:
                    existing_facts = self.memory_store.get_all_facts()
                    if existing_facts:
                        merged_facts = result.facts.merge_with(existing_facts)
                
                if merged_facts:
                    result.profile = self.profile_generator.generate(
                        facts=merged_facts,
                        summaries=all_summaries,
                        stories=result.stories if result.stories else None,
                        force_regenerate=True,  # Always regenerate profile with new data
                    )
                    logger.info("Profile generated/updated")
            except Exception as e:
                logger.error(f"Profile generation failed: {e}")
                result.warnings.append(f"Profile generation failed: {str(e)}")
            
            await report_progress("generating_profile", 0.95, "Profile complete")
            
            # Complete
            await report_progress("complete", 1.0, "Extraction complete")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result.success = False
            result.errors.append(str(e))
            await report_progress("error", 0.0, f"Extraction failed: {str(e)}")
        
        finally:
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - started_at).total_seconds() * 1000
            logger.info(
                f"Extraction complete for {filename}: "
                f"{result.duration_ms:.0f}ms, success={result.success}"
            )
        
        return result
    
    async def process_document_background(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        filename: str = "",
        progress_callback: Optional[ProgressCallback] = None,
    ) -> str:
        """
        Start document processing in background, returning immediately.
        
        Args:
            document_id: Unique identifier for the document
            text: Full text content
            document_type: Type of document
            filename: Original filename
            progress_callback: Async callback for progress updates
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        
        async def run_extraction():
            try:
                result = await self.process_document(
                    document_id=document_id,
                    text=text,
                    document_type=document_type,
                    filename=filename,
                    progress_callback=progress_callback,
                )
                return result
            finally:
                # Clean up task reference
                if task_id in self._active_extractions:
                    del self._active_extractions[task_id]
        
        task = asyncio.create_task(run_extraction())
        self._active_extractions[task_id] = task
        
        logger.info(f"Started background extraction: {task_id}")
        return task_id
    
    def get_extraction_task(self, task_id: str) -> Optional[asyncio.Task]:
        """Get an active extraction task by ID."""
        return self._active_extractions.get(task_id)
    
    def cancel_extraction(self, task_id: str) -> bool:
        """Cancel an active extraction."""
        task = self._active_extractions.get(task_id)
        if task and not task.done():
            task.cancel()
            del self._active_extractions[task_id]
            return True
        return False
    
    def get_active_extraction_count(self) -> int:
        """Get the number of active extractions."""
        # Clean up completed tasks
        completed = [tid for tid, task in self._active_extractions.items() if task.done()]
        for tid in completed:
            del self._active_extractions[tid]
        return len(self._active_extractions)
    
    async def process_multiple_documents(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[ProgressCallback] = None,
    ) -> List[ExtractionResult]:
        """
        Process multiple documents, potentially in parallel.
        
        Args:
            documents: List of dicts with 'document_id', 'text', 'document_type', 'filename'
            progress_callback: Callback for overall progress
            
        Returns:
            List of ExtractionResults
        """
        results = []
        total = len(documents)
        
        for i, doc in enumerate(documents):
            # Calculate overall progress
            base_progress = i / total
            
            async def doc_progress(stage: str, progress: float, message: Optional[str] = ""):
                overall = base_progress + (progress / total)
                if progress_callback:
                    await progress_callback(
                        stage, 
                        overall,
                        f"[{i+1}/{total}] {message or ''}"
                    )
            
            result = await self.process_document(
                document_id=doc.get("document_id", str(uuid.uuid4())),
                text=doc.get("text", ""),
                document_type=doc.get("document_type", DocumentType.OTHER),
                filename=doc.get("filename", ""),
                progress_callback=doc_progress,
            )
            results.append(result)
        
        return results
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about the pipeline."""
        return {
            "active_extractions": self.get_active_extraction_count(),
            "has_llm_provider": self.llm_provider is not None,
            "has_memory_store": self.memory_store is not None,
            "stages": [
                {"name": s.name, "display": s.display_name, "weight": s.weight}
                for s in PIPELINE_STAGES
            ],
        }
