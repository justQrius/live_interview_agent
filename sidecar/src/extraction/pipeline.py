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

from src.memory.models import (
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
    status: str    # Status string for callback

class ExtractionPipeline:
    """
    Orchestrates the document extraction pipeline.
    
    Coordinates the execution of Summarizer, FactExtractor, StoryExtractor,
    and ProfileGenerator to extract intelligence from documents.
    """
    
    STAGES = [
        PipelineStage("summarize", "Summarizing Document", 0.2, "summarizing"),
        PipelineStage("facts", "Extracting Facts", 0.3, "extracting_facts"),
        PipelineStage("stories", "identifying STAR Stories", 0.3, "extracting_stories"),
        PipelineStage("profile", "Updating Candidate Profile", 0.2, "updating_profile"),
    ]
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None
    ):
        """
        Initialize the extraction pipeline.
        
        Args:
            llm_provider: LLM provider for all extractors
            memory_store: Memory store for saving results
        """
        self.llm_provider = llm_provider
        self.memory_store = memory_store
        
        # Initialize sub-extractors
        self.summarizer = DocumentSummarizer(llm_provider, memory_store)
        self.fact_extractor = FactExtractor(llm_provider, memory_store)
        self.story_extractor = StoryExtractor(llm_provider, memory_store)
        self.profile_generator = ProfileGenerator(memory_store)
        
        # Track background tasks
        self._background_tasks: Dict[str, asyncio.Task] = {}
        
    def set_llm_provider(self, provider: Any) -> None:
        """Update LLM provider for all components."""
        self.llm_provider = provider
        self.summarizer.set_llm_provider(provider)
        self.fact_extractor.set_llm_provider(provider)
        self.story_extractor.set_llm_provider(provider)
        
    def set_memory_store(self, store: Any) -> None:
        """Update memory store for all components."""
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
        filename: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ExtractionResult:
        """
        Run the full extraction pipeline.
        
        Args:
            document_id: Unique document ID
            text: Document content
            document_type: Type of document
            filename: Original filename
            progress_callback: Optional async callback for progress updates
            
        Returns:
            ExtractionResult object
        """
        start_time = datetime.now()
        logger.info(f"Starting extraction for {filename} ({document_type.value})")
        
        result = ExtractionResult(
            document_id=document_id,
            document_type=document_type,
            filename=filename,
            started_at=start_time
        )
        
        current_progress = 0.0
        
        async def update_progress(stage_idx: int, message: str = ""):
            """Helper to update progress based on stages."""
            if not progress_callback:
                return
                
            nonlocal current_progress
            
            # Calculate base progress from completed stages
            base_progress = sum(s.weight for s in self.STAGES[:stage_idx]) * 100
            
            # Add a bit of progress for the current stage start
            current_stage_weight = self.STAGES[stage_idx].weight * 100
            
            # Update global progress
            current_progress = base_progress + (current_stage_weight * 0.1)
            
            stage = self.STAGES[stage_idx]
            if message:
                full_message = f"{stage.display_name}: {message}"
            else:
                full_message = stage.display_name
                
            await progress_callback(stage.status, current_progress, full_message)

        try:
            # Initial status
            if progress_callback:
                await progress_callback("parsing", 0.0, "Parsing document...")

            # 1. Summarization
            await update_progress(0)
            try:
                result.summary = await self.summarizer.summarize(
                    document_id, text, document_type, filename
                )
            except Exception as e:
                logger.error(f"Summarization failed: {e}")
                result.errors.append(f"Summarization failed: {str(e)}")
            
            # 2. Fact Extraction
            await update_progress(1)
            try:
                result.facts = await self.fact_extractor.extract_facts(
                    document_id, text, document_type
                )
            except Exception as e:
                logger.error(f"Fact extraction failed: {e}")
                result.errors.append(f"Fact extraction failed: {str(e)}")
            
            # 3. Story Extraction (only for Resumes)
            await update_progress(2)
            if document_type == DocumentType.RESUME and result.facts:
                try:
                    result.stories = await self.story_extractor.extract_stories(
                        result.facts
                    )
                except Exception as e:
                    logger.error(f"Story extraction failed: {e}")
                    result.errors.append(f"Story extraction failed: {str(e)}")
            else:
                logger.info(f"Skipping story extraction for {document_type.value}")
            
            # 4. Profile Generation (only for Resumes or if we have new facts)
            await update_progress(3)
            if result.facts and (result.facts.skills or result.facts.timeline):
                try:
                    # Pass facts explicitly to handle cases where store update isn't visible (e.g. mocks)
                    result.profile = self.profile_generator.generate(
                        facts=result.facts,
                        summaries=[result.summary] if result.summary else [],
                        stories=result.stories,
                        force_regenerate=True
                    )
                except Exception as e:
                    logger.error(f"Profile generation failed: {e}")
                    result.errors.append(f"Profile generation failed: {str(e)}")
            
            # Complete
            result.completed_at = datetime.now()
            result.duration_ms = (result.completed_at - start_time).total_seconds() * 1000
            
            # Add warnings for partial failures
            if result.errors:
                result.warnings.extend([f"Partial failure: {e}" for e in result.errors])
                # We don't want to fail the whole pipeline for partial errors if some data was extracted
                if result.summary or result.facts:
                    result.errors = [] # Clear errors so success remains True if we recovered
                else:
                    result.success = False

            if progress_callback:
                await progress_callback(
                    "complete", 
                    100.0, 
                    f"Extraction complete ({len(result.stories)} stories found)"
                )
            
            logger.info(f"Extraction completed in {result.duration_ms:.2f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result.success = False
            result.errors.append(str(e))
            result.completed_at = datetime.now()
            
            if progress_callback:
                await progress_callback("error", 0, f"Extraction failed: {str(e)}")
                
            return result

    async def process_document_background(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        filename: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> str:
        """
        Run extraction in background.
        
        Args:
            document_id: Unique document ID
            text: Document content
            document_type: Type of document
            filename: Original filename
            progress_callback: Optional callback
            
        Returns:
            Task ID (str)
        """
        task_id = str(uuid.uuid4())
        
        async def _wrapper():
            try:
                await self.process_document(
                    document_id, text, document_type, filename, progress_callback
                )
            except Exception as e:
                logger.error(f"Background task failed: {e}")
            finally:
                if task_id in self._background_tasks:
                    del self._background_tasks[task_id]
        
        task = asyncio.create_task(_wrapper())
        self._background_tasks[task_id] = task
        return task_id
    
    def get_extraction_task(self, task_id: str) -> Optional[asyncio.Task]:
        """Get a background task by ID."""
        return self._background_tasks.get(task_id)
        
    def cancel_extraction(self, task_id: str) -> bool:
        """
        Cancel a running background extraction task.
        
        Args:
            task_id: Task ID returned from process_document_background
            
        Returns:
            True if cancelled, False if not found
        """
        if task_id in self._background_tasks:
            self._background_tasks[task_id].cancel()
            del self._background_tasks[task_id]
            return True
        return False
    
    def get_active_extraction_count(self) -> int:
        """Get number of active background extractions."""
        return len(self._background_tasks)
        
    async def process_multiple_documents(
        self,
        documents: List[Dict[str, Any]],
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[ExtractionResult]:
        """
        Process multiple documents in sequence.
        
        Args:
            documents: List of dicts with keys: document_id, text, document_type, filename
            progress_callback: Optional callback
            
        Returns:
            List of ExtractionResult
        """
        results = []
        total_docs = len(documents)
        
        for i, doc in enumerate(documents):
            # Wrap progress callback to reflect overall progress
            async def wrapped_callback(status, progress, message):
                if progress_callback:
                    # Scale progress: (doc_index * 100 + doc_progress) / total_docs
                    overall_progress = (i * 100 + progress) / total_docs
                    await progress_callback(status, overall_progress, f"[{i+1}/{total_docs}] {message}")
            
            result = await self.process_document(
                document_id=doc["document_id"],
                text=doc["text"],
                document_type=doc["document_type"],
                filename=doc["filename"],
                progress_callback=wrapped_callback if progress_callback else None
            )
            results.append(result)
            
        return results

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get statistics about the pipeline."""
        return {
            "active_tasks": len(self._background_tasks),
            "stages": [s.name for s in self.STAGES],
            "has_llm_provider": self.llm_provider is not None,
            "has_memory_store": self.memory_store is not None
        }
