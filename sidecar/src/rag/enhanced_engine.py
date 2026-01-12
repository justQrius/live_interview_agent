"""
Enhanced RAG Engine with question-type-aware retrieval and parent expansion.

Extends the base RAGEngine to use intelligent document type prioritization
based on question classification, and performs actual parent chunk expansion
for richer context.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .store import VectorStore
from .retrieval import RetrievalResult, confidence_from_distance

# Import with explicit src prefix for test compatibility
try:
    from src.context.enhanced_manager import DocumentType
except ImportError:
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
    "culture": [DocumentType.COMPANY_INFO, DocumentType.INTERVIEWER_INFO],
    "interviewer": [DocumentType.INTERVIEWER_INFO, DocumentType.COMPANY_INFO],
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
    - Child chunk retrieval with ACTUAL parent expansion
    - Sub-question aggregation
    - Parent caching for performance
    - Backward compatible with base RAGEngine interface
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        context_manager: Optional[Any] = None,
        expand_to_parent: bool = True
    ):
        """
        Initialize the Enhanced RAG Engine.
        
        Args:
            vector_store: The VectorStore instance to use for retrieval.
            context_manager: Optional EnhancedContextManager for parent lookup.
            expand_to_parent: Whether to expand child results to parent context.
        """
        self.vector_store = vector_store
        self.context_manager = context_manager
        self.expand_to_parent = expand_to_parent
        self.parent_cache: Dict[str, str] = {}  # parent_id -> text
    
    def set_context_manager(self, context_manager: Any) -> None:
        """
        Set the context manager for parent chunk lookup.
        
        Args:
            context_manager: EnhancedContextManager instance
        """
        self.context_manager = context_manager
    
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
        
        Pipeline:
        1. Get document priorities for question type
        2. Query child chunks with type filter
        3. Expand to parent chunks for full context (NEW: actually does it!)
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
        seen_texts: Set[str] = set()  # Use text hash for dedup
        
        # Query each priority document type
        results_per_type = max(2, limit // len(priorities))
        
        for doc_type in priorities:
            try:
                type_results = self._query_by_type(
                    query=question,
                    doc_type=doc_type,
                    limit=results_per_type
                )
                
                for result in type_results:
                    # Deduplicate by text content (first 200 chars)
                    text_key = result.text[:200] if len(result.text) > 200 else result.text
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        all_results.append(result)
                        
            except Exception as e:
                logger.warning(f"Failed to query for doc_type {doc_type.value}: {e}")
                continue
        
        # Handle sub-questions if provided
        if sub_questions:
            for sub_q in sub_questions:
                sub_results = self._query_general(sub_q, limit=2)
                for result in sub_results:
                    text_key = result.text[:200] if len(result.text) > 200 else result.text
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        all_results.append(result)
        
        # Expand child chunks to parents for fuller context
        if self.expand_to_parent:
            expanded_results = self._expand_to_parents(all_results)
        else:
            expanded_results = all_results
        
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
        
        Prefers child chunks for precise matching, falls back to all chunks.
        
        Args:
            query: Search query.
            doc_type: Document type to filter by.
            limit: Maximum results.
            
        Returns:
            List of RetrievalResult objects.
        """
        try:
            # Try to filter by document type and child level first
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
            
            parsed = self._parse_results(results)
            if parsed:
                return parsed
            
            # If no child chunks, try without level filter
            results = self.vector_store.query_with_filter(
                query=query,
                n_results=limit,
                where={"document_type": doc_type.value}
            )
            return self._parse_results(results)
            
        except Exception as e:
            logger.error(f"Error querying by type {doc_type.value}: {e}")
            # Final fallback: query without filters
            try:
                results = self.vector_store.query_with_scores(query, n_results=limit)
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
            # Prefer child chunks for precision
            results = self.vector_store.query_with_filter(
                query=query,
                n_results=limit,
                where={"level": "child"}
            )
            parsed = self._parse_results(results)
            if parsed:
                return parsed
            
            # Fallback to all chunks
            results = self.vector_store.query_with_scores(query, n_results=limit)
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
            
            # Include chunk ID in metadata for parent lookup
            if meta is None:
                meta = {}
            meta["chunk_id"] = ids[i]
            
            retrieval_results.append(RetrievalResult(
                text=text,
                distance=dist,
                confidence=confidence,
                metadata=meta
            ))
        
        return retrieval_results
    
    def _expand_to_parents(
        self,
        child_results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Expand child chunks to their parent chunks for fuller context.
        
        This is the KEY improvement: when we match a child chunk (512 chars),
        we replace it with its parent chunk (2048 chars) to give the LLM
        more context around the matched content.
        
        Args:
            child_results: List of child chunk results.
            
        Returns:
            List of RetrievalResult with expanded parent context.
        """
        if not child_results:
            return []
        
        expanded_results: List[RetrievalResult] = []
        seen_parent_ids: Set[str] = set()
        
        for result in child_results:
            parent_id = result.metadata.get("parent_id")
            level = result.metadata.get("level", "unknown")
            
            # If it's already a parent or has no parent_id, keep as-is
            if level == "parent" or not parent_id:
                expanded_results.append(result)
                continue
            
            # Avoid duplicate parents
            if parent_id in seen_parent_ids:
                continue
            
            # Try to get parent text
            parent_text = self._get_parent_text(parent_id)
            
            if parent_text:
                # Replace child text with parent text
                seen_parent_ids.add(parent_id)
                
                expanded_result = RetrievalResult(
                    text=parent_text,
                    distance=result.distance,  # Keep child's relevance score
                    confidence=result.confidence,
                    metadata={
                        **result.metadata,
                        "expanded_from_child": True,
                        "original_child_text": result.text[:100] + "..." if len(result.text) > 100 else result.text,
                    }
                )
                expanded_results.append(expanded_result)
                logger.debug(f"Expanded child to parent: {len(result.text)} -> {len(parent_text)} chars")
            else:
                # Couldn't find parent, keep child
                result.metadata["parent_not_found"] = True
                expanded_results.append(result)
        
        return expanded_results
    
    def _get_parent_text(self, parent_id: str) -> Optional[str]:
        """
        Get the full text of a parent chunk.
        
        Tries multiple strategies:
        1. Check local cache
        2. Query context manager (if available)
        3. Query vector store by ID
        
        Args:
            parent_id: ID of the parent chunk.
            
        Returns:
            Parent chunk text if found, None otherwise.
        """
        # Strategy 1: Check cache
        if parent_id in self.parent_cache:
            return self.parent_cache[parent_id]
        
        # Strategy 2: Query context manager
        if self.context_manager is not None:
            try:
                parent_chunk = self.context_manager.get_parent_chunk(parent_id)
                if parent_chunk:
                    self.parent_cache[parent_id] = parent_chunk.text
                    return parent_chunk.text
            except Exception as e:
                logger.debug(f"Context manager lookup failed: {e}")
        
        # Strategy 3: Query vector store by parent_id filter
        try:
            results = self.vector_store.query_with_filter(
                query="",  # Empty query, we're filtering by ID
                n_results=1,
                where={"level": "parent"}
            )
            
            # This is imperfect - we can't query by exact ID in ChromaDB
            # without the collection.get() method. For now, return None.
            # TODO: Add get_by_id to VectorStore
            
        except Exception as e:
            logger.debug(f"Vector store parent lookup failed: {e}")
        
        return None
    
    def cache_parents(self, parent_chunks: List[Any]) -> None:
        """
        Pre-populate the parent cache for faster expansion.
        
        Call this after processing documents to enable instant parent expansion.
        
        Args:
            parent_chunks: List of parent EnhancedChunk objects
        """
        for chunk in parent_chunks:
            if hasattr(chunk, 'id') and hasattr(chunk, 'text'):
                self.parent_cache[chunk.id] = chunk.text
        
        logger.info(f"Cached {len(parent_chunks)} parent chunks for expansion")
    
    def get_parent_context(self, parent_id: str) -> Optional[str]:
        """
        Get the full text of a parent chunk (public API).
        
        Args:
            parent_id: ID of the parent chunk.
            
        Returns:
            Parent chunk text if found, None otherwise.
        """
        return self._get_parent_text(parent_id)
    
    def clear_cache(self) -> None:
        """Clear the parent chunk cache."""
        self.parent_cache.clear()
        logger.info("Parent cache cleared")
