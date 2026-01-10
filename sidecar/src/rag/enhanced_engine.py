"""
Enhanced RAG Engine with question-type-aware retrieval.

Extends the base RAGEngine to use intelligent document type prioritization
based on question classification, and supports parent chunk expansion.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .store import VectorStore
from .retrieval import RetrievalResult, confidence_from_distance
from context.enhanced_manager import DocumentType

logger = logging.getLogger(__name__)


# Question type to document priority mapping
# First document type in list has highest priority
DOC_PRIORITY_BY_QUESTION_TYPE: Dict[str, List[DocumentType]] = {
    "behavioral": [DocumentType.RESUME, DocumentType.SAMPLE_QA],
    "intro": [DocumentType.RESUME],
    "technical": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
    "motivation": [DocumentType.COMPANY_INFO, DocumentType.JOB_DESCRIPTION, DocumentType.INDUSTRY_RESEARCH],
    "weakness": [DocumentType.SAMPLE_QA, DocumentType.RESUME],
    "strength": [DocumentType.RESUME, DocumentType.SAMPLE_QA],
    "experience": [DocumentType.RESUME],
    "salary": [DocumentType.JOB_DESCRIPTION, DocumentType.INDUSTRY_RESEARCH],
    "culture": [DocumentType.COMPANY_INFO],
    "general": [DocumentType.RESUME, DocumentType.JOB_DESCRIPTION],
}

# Default priorities when question type is unknown
DEFAULT_PRIORITIES = [
    DocumentType.RESUME,
    DocumentType.JOB_DESCRIPTION,
    DocumentType.COMPANY_INFO,
]


class EnhancedRAGEngine:
    """
    Enhanced RAG Engine with question-type-aware retrieval.
    
    Features:
    - Question type to document type priority mapping
    - Child chunk retrieval with parent expansion
    - Sub-question aggregation
    - Backward compatible with base RAGEngine interface
    """
    
    def __init__(self, vector_store: VectorStore):
        """
        Initialize the Enhanced RAG Engine.
        
        Args:
            vector_store: The VectorStore instance to use for retrieval.
        """
        self.vector_store = vector_store
        self.parent_cache: Dict[str, str] = {}  # parent_id -> text
    
    def retrieve(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        """
        Basic retrieve method for backward compatibility.
        
        Uses 'general' question type for prioritization.
        
        Args:
            query: The question or query string.
            limit: Maximum number of results to return.
            
        Returns:
            List of RetrievalResult objects.
        """
        return self.retrieve_for_question(
            question=query,
            question_type="general",
            limit=limit
        )
    
    def retrieve_for_question(
        self,
        question: str,
        question_type: str,
        sub_questions: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Retrieve context with question-type-aware filtering.
        
        1. Get document priorities for question type
        2. Query child chunks with type filter
        3. Expand to parent chunks for full context
        4. Aggregate across sub-questions if provided
        
        Args:
            question: The main question text.
            question_type: Classification of the question (behavioral, technical, etc.)
            sub_questions: Optional list of sub-questions for aggregation.
            limit: Maximum number of results to return.
            
        Returns:
            List of RetrievalResult objects, sorted by relevance.
        """
        if not question or not question.strip():
            logger.warning("Empty question provided to Enhanced RAG Engine")
            return []
        
        # Get document priorities for this question type
        priorities = DOC_PRIORITY_BY_QUESTION_TYPE.get(
            question_type,
            DEFAULT_PRIORITIES
        )
        
        logger.info(f"Retrieving for question type '{question_type}' with priorities: {[p.value for p in priorities]}")
        
        all_results: List[RetrievalResult] = []
        seen_ids: Set[str] = set()
        
        # Query each priority document type
        results_per_type = max(1, limit // len(priorities))
        
        for doc_type in priorities:
            try:
                type_results = self._query_by_type(
                    query=question,
                    doc_type=doc_type,
                    limit=results_per_type
                )
                
                for result in type_results:
                    # Deduplicate by text hash
                    text_hash = hash(result.text[:100] if len(result.text) > 100 else result.text)
                    if text_hash not in seen_ids:
                        seen_ids.add(text_hash)
                        all_results.append(result)
                        
            except Exception as e:
                logger.warning(f"Failed to query for doc_type {doc_type.value}: {e}")
                continue
        
        # Handle sub-questions if provided
        if sub_questions:
            for sub_q in sub_questions:
                sub_results = self._query_general(sub_q, limit=2)
                for result in sub_results:
                    text_hash = hash(result.text[:100] if len(result.text) > 100 else result.text)
                    if text_hash not in seen_ids:
                        seen_ids.add(text_hash)
                        all_results.append(result)
        
        # Expand child chunks to parents for fuller context
        expanded_results = self._expand_to_parents(all_results)
        
        # Sort by confidence/distance and limit
        sorted_results = sorted(expanded_results, key=lambda r: r.distance)
        
        return sorted_results[:limit]
    
    def _query_by_type(
        self,
        query: str,
        doc_type: DocumentType,
        limit: int = 5
    ) -> List[RetrievalResult]:
        """
        Query for chunks of a specific document type.
        
        Args:
            query: Search query.
            doc_type: Document type to filter by.
            limit: Maximum results.
            
        Returns:
            List of RetrievalResult objects.
        """
        try:
            # Filter by document type and child level
            where_filter = {
                "$and": [
                    {"document_type": doc_type.value},
                    {"level": "child"}
                ]
            }
            
            results = self.vector_store.query_with_filter(
                query=query,
                n_results=limit,
                where=where_filter
            )
            
            return self._parse_results(results)
            
        except Exception as e:
            logger.error(f"Error querying by type {doc_type.value}: {e}")
            # Fallback to simpler filter
            try:
                results = self.vector_store.query_with_filter(
                    query=query,
                    n_results=limit,
                    where={"document_type": doc_type.value}
                )
                return self._parse_results(results)
            except Exception as e2:
                logger.error(f"Fallback query also failed: {e2}")
                return []
    
    def _query_general(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        """
        General query without type filtering.
        
        Args:
            query: Search query.
            limit: Maximum results.
            
        Returns:
            List of RetrievalResult objects.
        """
        try:
            results = self.vector_store.query_with_filter(
                query=query,
                n_results=limit,
                where={"level": "child"}
            )
            return self._parse_results(results)
        except Exception as e:
            logger.error(f"Error in general query: {e}")
            return []
    
    def _parse_results(self, results: Dict[str, Any]) -> List[RetrievalResult]:
        """
        Parse ChromaDB results into RetrievalResult objects.
        
        Args:
            results: Raw ChromaDB query results.
            
        Returns:
            List of RetrievalResult objects.
        """
        if not results or not results.get('ids') or not results['ids'][0]:
            return []
        
        retrieval_results = []
        
        # ChromaDB returns lists of lists (one per query)
        ids = results['ids'][0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        documents = results.get('documents', [[]])[0]
        
        for i in range(len(ids)):
            dist = distances[i] if i < len(distances) else 1.0
            text = documents[i] if i < len(documents) else ""
            meta = metadatas[i] if i < len(metadatas) else {}
            
            confidence = confidence_from_distance(dist)
            
            retrieval_results.append(RetrievalResult(
                text=text,
                distance=dist,
                confidence=confidence,
                metadata=meta or {}
            ))
        
        return retrieval_results
    
    def _expand_to_parents(
        self,
        child_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Expand child chunks to their parent chunks for fuller context.
        
        If a child chunk has a parent_id, we can optionally fetch the
        parent chunk to provide more complete context. This implementation
        keeps child chunks but annotates them with parent availability.
        
        Args:
            child_results: List of child chunk results.
            
        Returns:
            List of RetrievalResult (may include expanded context).
        """
        if not child_results:
            return []
        
        # Collect unique parent IDs
        parent_ids: Set[str] = set()
        for result in child_results:
            parent_id = result.metadata.get("parent_id")
            if parent_id and parent_id not in self.parent_cache:
                parent_ids.add(parent_id)
        
        # For now, we return the child results as-is
        # Parent expansion could fetch parent chunks and merge/replace
        # This keeps the implementation simple while supporting the interface
        
        # Annotate results with parent_available flag
        for result in child_results:
            parent_id = result.metadata.get("parent_id")
            if parent_id:
                result.metadata["parent_available"] = True
        
        return child_results
    
    def get_parent_context(self, parent_id: str) -> Optional[str]:
        """
        Get the full text of a parent chunk.
        
        Args:
            parent_id: ID of the parent chunk.
            
        Returns:
            Parent chunk text if found, None otherwise.
        """
        # Check cache first
        if parent_id in self.parent_cache:
            return self.parent_cache[parent_id]
        
        # Could query vector store by ID here if needed
        # For now, return None as we'd need a get_by_id method
        return None
    
    def clear_cache(self) -> None:
        """Clear the parent chunk cache."""
        self.parent_cache.clear()
        logger.info("Parent cache cleared")
