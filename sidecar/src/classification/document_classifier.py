"""
Document Type Classifier.

Uses LLM to intelligently classify document types for interview preparation.
Analyzes document content to determine if it's a resume, job description,
interviewer info, etc. - providing accurate classification even when
filenames are ambiguous.

Part of the hybrid classification system:
1. Fast filename-based heuristic (frontend)
2. LLM-based content analysis (this module)
3. User confirmation/override (frontend)
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.providers.base import LLMProvider

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document types for interview context."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INTERVIEWER_INFO = "interviewer_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    CUSTOM = "custom"


@dataclass
class DocumentTypeResult:
    """Result of document type classification."""
    document_type: str
    confidence: float
    reason: str
    
    def to_dict(self) -> dict:
        return {
            "documentType": self.document_type,
            "confidence": self.confidence,
            "reason": self.reason
        }


# Prompt template for document type inference
CLASSIFICATION_PROMPT = """You are classifying a document for interview preparation.

## Allowed Document Types:
- resume: Candidate's CV/resume with their experience, skills, education, projects (first-person or describing the job seeker)
- job_description: Job posting with role responsibilities, requirements, qualifications (describes what company is looking for)
- company_info: Company overview, culture, values, products, news (about an organization)
- interviewer_info: Information about a person who will conduct the interview - their bio, LinkedIn profile, career history, background (third-person description of an interviewer/hiring manager)
- industry_research: Market analysis, competitor info, industry trends
- sample_qa: Interview questions and answers, prep notes, frameworks, practice materials
- custom: Anything else or unclear

## Key Distinctions:
- RESUME: Written FROM the candidate's perspective ("I led...", "Managed team of 5...")
- INTERVIEWER_INFO: Written ABOUT someone else who interviews ("John has 10 years at Google...", "Director of Engineering at...")
- JOB_DESCRIPTION: Describes requirements ("We're looking for...", "Responsibilities include...")

## Task:
Analyze the filename and document excerpt below. Return a JSON object with:
- documentType: exactly one of the allowed types
- confidence: number from 0.0 to 1.0
- reason: brief explanation (max 15 words)

## Important:
- If the document discusses someone's career/background in THIRD PERSON, it's likely interviewer_info
- If it's in FIRST PERSON with skills/experience, it's likely resume
- If ambiguous, use "custom" with low confidence

Filename: {filename}

Document excerpt (first ~1500 chars):
\"\"\"
{excerpt}
\"\"\"

Respond with ONLY valid JSON, no markdown:"""


class DocumentClassifier:
    """
    Classifies documents using LLM for accurate type detection.
    
    Uses a lightweight prompt with the first ~1500 chars of the document
    to determine its type. Designed for <2s latency using Gemini Flash.
    """
    
    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        """
        Initialize the classifier.
        
        Args:
            llm_provider: LLM provider for inference (should use Flash model for speed)
        """
        self._llm = llm_provider
        
    def set_llm_provider(self, llm_provider: "LLMProvider") -> None:
        """Set or update the LLM provider."""
        self._llm = llm_provider
        
    async def classify(
        self, 
        filename: str, 
        text_content: str,
        fallback_type: str = "custom"
    ) -> DocumentTypeResult:
        """
        Classify a document's type using LLM analysis.
        
        Args:
            filename: Original filename (provides hints)
            text_content: Extracted text content from the document
            fallback_type: Type to use if classification fails
            
        Returns:
            DocumentTypeResult with type, confidence, and reason
        """
        # If no LLM available, use filename-based fallback
        if not self._llm:
            logger.warning("No LLM provider for document classification, using filename heuristic")
            return self._filename_heuristic(filename, fallback_type)
        
        # Take first ~1500 chars for analysis (balance between accuracy and speed)
        excerpt = text_content[:1500] if len(text_content) > 1500 else text_content
        
        # Build prompt
        prompt = CLASSIFICATION_PROMPT.format(
            filename=filename,
            excerpt=excerpt
        )
        
        try:
            # Collect response (non-streaming for simplicity)
            response_text = ""
            async for chunk in self._llm.generate_response(prompt, "", []):
                response_text += chunk
                # Early exit once we have enough for JSON parsing
                if len(response_text) > 200 and "}" in response_text:
                    break
            
            # Parse JSON response
            result = self._parse_response(response_text, fallback_type)
            logger.info(f"Classified '{filename}' as {result.document_type} ({result.confidence:.0%}): {result.reason}")
            return result
            
        except Exception as e:
            logger.error(f"Document classification failed: {e}")
            return self._filename_heuristic(filename, fallback_type)
    
    async def classify_batch(
        self,
        documents: List[dict]
    ) -> List[DocumentTypeResult]:
        """
        Classify multiple documents.
        
        Args:
            documents: List of dicts with 'id', 'filename', 'text_content'
            
        Returns:
            List of DocumentTypeResult in same order
        """
        results = []
        for doc in documents:
            result = await self.classify(
                filename=doc.get("filename", "unknown"),
                text_content=doc.get("text_content", ""),
                fallback_type=doc.get("fallback_type", "custom")
            )
            results.append(result)
        return results
    
    def _parse_response(self, response: str, fallback_type: str) -> DocumentTypeResult:
        """Parse LLM JSON response into DocumentTypeResult."""
        import json
        
        # Clean up response - find JSON object
        response = response.strip()
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                doc_type = data.get("documentType", fallback_type)
                
                # Validate document type
                valid_types = [t.value for t in DocumentType]
                if doc_type not in valid_types:
                    doc_type = fallback_type
                
                return DocumentTypeResult(
                    document_type=doc_type,
                    confidence=float(data.get("confidence", 0.5)),
                    reason=str(data.get("reason", "LLM classification"))[:100]
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse classification JSON: {e}")
        
        # Fallback: try to extract type from text
        response_upper = response.upper()
        for doc_type in DocumentType:
            if doc_type.value.upper().replace("_", " ") in response_upper or \
               doc_type.value.upper() in response_upper:
                return DocumentTypeResult(
                    document_type=doc_type.value,
                    confidence=0.6,
                    reason="Extracted from LLM response"
                )
        
        return DocumentTypeResult(
            document_type=fallback_type,
            confidence=0.3,
            reason="Could not parse LLM response"
        )
    
    def _filename_heuristic(self, filename: str, fallback_type: str) -> DocumentTypeResult:
        """Fallback: classify based on filename patterns."""
        lower_name = filename.lower()
        
        patterns = [
            (["resume", "cv", "curriculum"], "resume", "Filename contains resume/CV keyword"),
            (["job", "jd", "description", "posting", "role"], "job_description", "Filename suggests job description"),
            (["interviewer", "hiring_manager", "hiring manager", "recruiter", "manager bio"], "interviewer_info", "Filename suggests interviewer info"),
            (["company", "about us", "culture"], "company_info", "Filename suggests company info"),
            (["research", "industry", "market", "competitor"], "industry_research", "Filename suggests research"),
            (["qa", "question", "answer", "prep", "sample"], "sample_qa", "Filename suggests Q&A prep"),
        ]
        
        for keywords, doc_type, reason in patterns:
            if any(kw in lower_name for kw in keywords):
                return DocumentTypeResult(
                    document_type=doc_type,
                    confidence=0.7,
                    reason=reason
                )
        
        return DocumentTypeResult(
            document_type=fallback_type,
            confidence=0.4,
            reason="No pattern matched in filename"
        )
