"""
Document Summarizer - Hierarchical LLM-based document summarization.

Generates:
- Document-level summary (~200 words)
- Section-level summaries (~50 words each)
- Key points extraction (5-10 bullet points)

Part of Phase 4: Interview Coach Evolution (STORY-054)
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Protocol, AsyncGenerator

from src.memory.models import DocumentSummary, DocumentType


logger = logging.getLogger(__name__)


# Summarization prompt template
SUMMARIZER_PROMPT = """You are analyzing a {document_type} document for interview preparation.

Provide a structured analysis with:

1. **DOCUMENT_SUMMARY**: A comprehensive 150-200 word summary capturing the key themes, qualifications, and notable aspects.

2. **SECTIONS**: Identify and summarize each major section (50 words each). For resumes, look for: Experience, Education, Skills, Projects, Certifications. For job descriptions: Requirements, Responsibilities, Qualifications, About Company.

3. **KEY_POINTS**: Extract 5-10 factual bullet points that would be important in an interview. Include specific metrics, achievements, years of experience, and notable skills.

Document content:
---
{document_text}
---

Respond ONLY with valid JSON in this exact format:
{{
  "document_summary": "...",
  "sections": {{"section_name": "section summary", ...}},
  "key_points": ["point 1", "point 2", ...]
}}"""


# Fallback prompt for when structured output fails
FALLBACK_SUMMARIZER_PROMPT = """Summarize this {document_type} document in 3 parts:

1. Overall summary (150-200 words)
2. Key sections found
3. Important bullet points for interview prep

Document:
{document_text}

Provide a clear, structured response."""


class LLMProviderProtocol(Protocol):
    """Protocol for LLM providers - used for type hinting."""
    
    async def generate_response(
        self, 
        prompt: str, 
        context: str, 
        history: List[Dict]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        ...


class DocumentSummarizer:
    """
    Hierarchical document summarizer using LLM.
    
    Generates structured summaries at document and section levels,
    plus extracting key points for interview preparation.
    """
    
    # Maximum characters to send to LLM (roughly 50k tokens)
    # Gemini supports 2M tokens, so this is very safe
    MAX_DOCUMENT_LENGTH = 200000
    
    def __init__(
        self, 
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None
    ):
        """
        Initialize the document summarizer.
        
        Args:
            llm_provider: LLM provider for generating summaries (optional - can be set later)
            memory_store: Memory store for caching summaries (optional)
        """
        self.llm_provider = llm_provider
        self.memory_store = memory_store
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set or update the LLM provider."""
        self.llm_provider = provider
    
    def set_memory_store(self, store: Any) -> None:
        """Set or update the memory store."""
        self.memory_store = store
    
    async def summarize(
        self, 
        document_id: str, 
        text: str, 
        document_type: DocumentType,
        filename: str = "",
        force_regenerate: bool = False
    ) -> DocumentSummary:
        """
        Generate a hierarchical summary of a document.
        
        Args:
            document_id: Unique identifier for the document
            text: Full text content of the document
            document_type: Type of document (resume, JD, etc.)
            filename: Original filename
            force_regenerate: If True, regenerate even if cached
            
        Returns:
            DocumentSummary with document-level, section-level, and key points
        """
        # Check cache first
        if not force_regenerate and self.memory_store:
            cached = self.memory_store.get_document_summary(document_id)
            if cached and cached.document_summary:
                logger.info(f"Using cached summary for document {document_id}")
                return cached
        
        # Truncate text if too long
        truncated_text = text[:self.MAX_DOCUMENT_LENGTH]
        if len(text) > self.MAX_DOCUMENT_LENGTH:
            logger.warning(f"Document truncated from {len(text)} to {self.MAX_DOCUMENT_LENGTH} chars")
        
        # Generate summary
        if self.llm_provider:
            summary = await self._summarize_with_llm(
                document_id, truncated_text, document_type, filename
            )
        else:
            logger.warning("No LLM provider available, using basic extraction")
            summary = self._basic_extraction(
                document_id, truncated_text, document_type, filename
            )
        
        # Cache result
        if self.memory_store:
            self.memory_store.save_document_summary(summary)
            logger.info(f"Saved summary for document {document_id}")
        
        return summary
    
    async def _summarize_with_llm(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        filename: str
    ) -> DocumentSummary:
        """Generate summary using LLM provider."""
        prompt = SUMMARIZER_PROMPT.format(
            document_type=self._format_document_type(document_type),
            document_text=text
        )
        
        # Collect streaming response
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            # Parse JSON response
            summary = self._parse_llm_response(
                full_response, document_id, document_type, filename
            )
            return summary
            
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            # Fallback to basic extraction
            return self._basic_extraction(document_id, text, document_type, filename)
    
    def _parse_llm_response(
        self,
        response: str,
        document_id: str,
        document_type: DocumentType,
        filename: str
    ) -> DocumentSummary:
        """Parse the LLM response into a DocumentSummary."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                return DocumentSummary(
                    document_id=document_id,
                    document_type=document_type,
                    filename=filename,
                    document_summary=data.get("document_summary", ""),
                    section_summaries=data.get("sections", {}),
                    key_points=data.get("key_points", []),
                    uploaded_at=datetime.now(),
                    generated_at=datetime.now(),
                )
            else:
                # JSON not found, treat as plain text
                return DocumentSummary(
                    document_id=document_id,
                    document_type=document_type,
                    filename=filename,
                    document_summary=response[:500],  # First 500 chars as summary
                    section_summaries={},
                    key_points=self._extract_bullet_points(response),
                    uploaded_at=datetime.now(),
                    generated_at=datetime.now(),
                )
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return DocumentSummary(
                document_id=document_id,
                document_type=document_type,
                filename=filename,
                document_summary=response[:500],
                section_summaries={},
                key_points=self._extract_bullet_points(response),
                uploaded_at=datetime.now(),
                generated_at=datetime.now(),
            )
    
    def _basic_extraction(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        filename: str
    ) -> DocumentSummary:
        """Basic extraction without LLM - fallback method."""
        # Extract sections based on common patterns
        sections = self._detect_sections(text, document_type)
        
        # Extract key points (first sentences of paragraphs, metrics)
        key_points = self._extract_key_points(text)
        
        # Create basic summary from first 500 chars
        summary = text[:500].strip()
        if len(text) > 500:
            summary += "..."
        
        return DocumentSummary(
            document_id=document_id,
            document_type=document_type,
            filename=filename,
            document_summary=summary,
            section_summaries=sections,
            key_points=key_points,
            uploaded_at=datetime.now(),
            generated_at=datetime.now(),
        )
    
    def _detect_sections(
        self, 
        text: str, 
        document_type: DocumentType
    ) -> Dict[str, str]:
        """Detect and summarize sections in document."""
        sections = {}
        
        # Common section headers by document type
        if document_type == DocumentType.RESUME:
            patterns = [
                r"(?:professional\s+)?experience",
                r"education",
                r"skills",
                r"projects?",
                r"certifications?",
                r"summary|profile|objective",
                r"achievements?|accomplishments?",
            ]
        elif document_type == DocumentType.JOB_DESCRIPTION:
            patterns = [
                r"requirements?|qualifications?",
                r"responsibilities|duties",
                r"about\s+(?:the\s+)?company|about\s+us",
                r"benefits?|perks?",
                r"what\s+you.?ll\s+do",
                r"what\s+we.?re\s+looking\s+for",
            ]
        else:
            patterns = [
                r"overview|introduction",
                r"mission|vision",
                r"products?|services?",
                r"team|culture",
            ]
        
        # Find sections
        for pattern in patterns:
            match = re.search(
                rf"(?:^|\n)[\s*#]*({pattern})[:\s*\n]+(.{{50,300}})",
                text,
                re.IGNORECASE | re.MULTILINE
            )
            if match:
                section_name = match.group(1).strip().title()
                section_content = match.group(2).strip()
                # Truncate to ~50 words
                words = section_content.split()[:50]
                sections[section_name] = " ".join(words)
        
        return sections
    
    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from document text."""
        points = []
        
        # Look for bullet points
        bullet_matches = re.findall(
            r"^[\s]*[•\-\*]\s*(.{20,200})$",
            text,
            re.MULTILINE
        )
        for match in bullet_matches[:10]:
            point = match.strip()
            if len(point) > 20:
                points.append(point)
        
        # Look for metrics (numbers with context)
        metric_matches = re.findall(
            r"(.{10,50}(?:\d+%|\$[\d,]+[KMB]?|\d+\s+years?|\d+\+\s+\w+).{10,50})",
            text,
            re.IGNORECASE
        )
        for match in metric_matches[:5]:
            point = match.strip()
            if point not in points:
                points.append(point)
        
        return points[:10]  # Max 10 points
    
    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from LLM response."""
        points = []
        
        # Match numbered or bulleted items
        matches = re.findall(
            r"(?:^\s*[\d\-•*]+[.\)]\s*)(.{20,200})",
            text,
            re.MULTILINE
        )
        
        for match in matches[:10]:
            points.append(match.strip())
        
        return points
    
    def _format_document_type(self, doc_type: DocumentType) -> str:
        """Format document type for prompt."""
        type_names = {
            DocumentType.RESUME: "resume/CV",
            DocumentType.JOB_DESCRIPTION: "job description",
            DocumentType.COMPANY_INFO: "company information",
            DocumentType.INTERVIEWER_INFO: "interviewer background",
            DocumentType.OTHER: "document",
        }
        return type_names.get(doc_type, "document")
    
    async def get_all_summaries(self) -> List[DocumentSummary]:
        """Get all cached document summaries."""
        if self.memory_store:
            return self.memory_store.get_all_document_summaries()
        return []
    
    def get_combined_context(self) -> str:
        """Get combined context from all summaries for prompt injection."""
        summaries = []
        
        if self.memory_store:
            all_summaries = self.memory_store.get_all_document_summaries()
            
            for summary in all_summaries:
                section_text = ""
                if summary.section_summaries:
                    sections = [f"  - {k}: {v}" for k, v in summary.section_summaries.items()]
                    section_text = "\n".join(sections)
                
                points_text = ""
                if summary.key_points:
                    points_text = "\n".join(f"  - {p}" for p in summary.key_points[:5])
                
                doc_context = f"""### {summary.filename or summary.document_type.value}
{summary.document_summary}

**Sections:**
{section_text}

**Key Points:**
{points_text}
"""
                summaries.append(doc_context)
        
        return "\n---\n".join(summaries)
