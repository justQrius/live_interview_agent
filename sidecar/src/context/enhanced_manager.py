"""
Enhanced Context Manager with multi-type document support.

Extends ContextManager to support document type tagging, section detection,
and type-filtered retrieval for intelligent context management.
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .manager import ContextManager
from .chunker import Chunk

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents that can be processed."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    CUSTOM = "custom"


@dataclass
class EnhancedChunk:
    """
    An enhanced chunk with rich metadata for intelligent retrieval.
    
    Attributes:
        id: Unique identifier for this chunk
        text: The actual text content
        document_type: Type of document this chunk came from
        section: Auto-detected section (e.g., "experience", "requirements")
        relevance_tags: Keywords for relevance matching
        parent_chunk_id: ID of parent chunk for hierarchical relationships
        start_char: Starting character position in original document
        end_char: Ending character position in original document
        metadata: Additional metadata (source file, timestamps, etc.)
    """
    id: str
    text: str
    document_type: DocumentType
    section: str
    relevance_tags: List[str]
    parent_chunk_id: Optional[str]
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# Section detection patterns for different document types
SECTION_PATTERNS: Dict[DocumentType, Dict[str, str]] = {
    DocumentType.RESUME: {
        "experience": r"(?i)(experience|work history|employment|professional background)",
        "education": r"(?i)(education|academic|degree|university|college|school)",
        "skills": r"(?i)(skills|technologies|competencies|technical skills|proficiencies)",
        "summary": r"(?i)(summary|objective|profile|about me|introduction)",
        "projects": r"(?i)(projects|portfolio|work samples)",
        "certifications": r"(?i)(certifications|certificates|licenses)",
    },
    DocumentType.JOB_DESCRIPTION: {
        "requirements": r"(?i)(requirements|qualifications|must have|required skills|what you need)",
        "responsibilities": r"(?i)(responsibilities|duties|role|what you.ll do|you will)",
        "benefits": r"(?i)(benefits|perks|compensation|what we offer|why join)",
        "about": r"(?i)(about us|company|who we are|our mission|our team)",
        "nice_to_have": r"(?i)(nice to have|preferred|bonus|plus)",
    },
}


class EnhancedContextManager(ContextManager):
    """
    Enhanced context manager with multi-type document support.
    
    Extends ContextManager to:
    - Tag documents by type (resume, job description, etc.)
    - Detect sections within documents
    - Support type-filtered retrieval
    - Maintain backward compatibility with existing API
    """
    
    def __init__(self):
        """Initialize enhanced context manager."""
        super().__init__()
        self.documents_by_type: Dict[DocumentType, List[EnhancedChunk]] = {}
        self._enhanced_chunks: List[EnhancedChunk] = []
    
    async def process_file(
        self,
        filename: str,
        content_b64: str,
        document_type: DocumentType = DocumentType.CUSTOM
    ) -> List[EnhancedChunk]:
        """
        Process a file with document type tagging.
        
        Args:
            filename: Name of the file
            content_b64: Base64 encoded file content
            document_type: Type of document (defaults to CUSTOM)
            
        Returns:
            List of EnhancedChunk objects
        """
        # Use parent class to do the basic processing
        base_chunks = await super().process_file(filename, content_b64)
        
        # Convert to enhanced chunks
        enhanced_chunks = []
        for chunk in base_chunks:
            enhanced = self._convert_to_enhanced(chunk, document_type, filename)
            enhanced_chunks.append(enhanced)
        
        # Store by type
        if document_type not in self.documents_by_type:
            self.documents_by_type[document_type] = []
        self.documents_by_type[document_type].extend(enhanced_chunks)
        
        # Also store in flat list
        self._enhanced_chunks.extend(enhanced_chunks)
        
        logger.info(
            f"Processed {filename} as {document_type.value}: "
            f"{len(enhanced_chunks)} enhanced chunks"
        )
        
        return enhanced_chunks
    
    def _convert_to_enhanced(
        self,
        chunk: Chunk,
        document_type: DocumentType,
        filename: str
    ) -> EnhancedChunk:
        """
        Convert a basic Chunk to an EnhancedChunk.
        
        Args:
            chunk: The basic chunk to convert
            document_type: Type of document
            filename: Source filename
            
        Returns:
            EnhancedChunk with detected section and metadata
        """
        # Detect section from chunk text
        section = self._detect_section(chunk.text, document_type)
        
        # Extract relevance tags (simple keyword extraction)
        relevance_tags = self._extract_relevance_tags(chunk.text)
        
        # Build enhanced metadata
        metadata = dict(chunk.metadata) if chunk.metadata else {}
        metadata["document_type"] = document_type.value
        metadata["source"] = filename
        
        return EnhancedChunk(
            id=str(uuid.uuid4()),
            text=chunk.text,
            document_type=document_type,
            section=section,
            relevance_tags=relevance_tags,
            parent_chunk_id=None,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            metadata=metadata
        )
    
    def _detect_section(self, text: str, document_type: DocumentType) -> str:
        """
        Detect which section a chunk belongs to.
        
        Args:
            text: The chunk text
            document_type: Type of document
            
        Returns:
            Section name or "unknown" if not detected
        """
        patterns = SECTION_PATTERNS.get(document_type, {})
        
        # Check each pattern
        for section_name, pattern in patterns.items():
            if re.search(pattern, text):
                return section_name
        
        return "unknown"
    
    def _extract_relevance_tags(self, text: str) -> List[str]:
        """
        Extract simple relevance tags from text.
        
        For now, this does basic keyword extraction. Could be enhanced
        with NLP in the future.
        
        Args:
            text: The chunk text
            
        Returns:
            List of relevance tags
        """
        # Common tech keywords to look for
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|C#)\b',
            r'\b(React|Vue|Angular|Node\.js|Django|Flask|FastAPI)\b',
            r'\b(AWS|GCP|Azure|Docker|Kubernetes|K8s)\b',
            r'\b(SQL|PostgreSQL|MySQL|MongoDB|Redis)\b',
            r'\b(API|REST|GraphQL|gRPC)\b',
            r'\b(Machine Learning|ML|AI|NLP|Deep Learning)\b',
        ]
        
        tags = set()
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            tags.update(match.lower() if isinstance(match, str) else match[0].lower() 
                       for match in matches)
        
        return list(tags)
    
    def get_chunks_by_type(self, doc_type: DocumentType) -> List[EnhancedChunk]:
        """
        Get all chunks of a specific document type.
        
        Args:
            doc_type: The document type to filter by
            
        Returns:
            List of chunks matching the type, empty list if none
        """
        return self.documents_by_type.get(doc_type, [])
    
    def get_all_enhanced_chunks(self) -> List[EnhancedChunk]:
        """
        Get all enhanced chunks across all document types.
        
        Returns:
            List of all EnhancedChunk objects
        """
        return self._enhanced_chunks.copy()
    
    def clear_context(self) -> None:
        """Clear all context including enhanced chunks."""
        super().clear_context()
        self.documents_by_type.clear()
        self._enhanced_chunks.clear()
        logger.info("Enhanced context cleared")
