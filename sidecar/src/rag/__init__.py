# RAG (Retrieval Augmented Generation) module
"""
Contains ChromaDB integration and retrieval pipeline.
"""

from .store import VectorStore
from .engine import RAGEngine
from .enhanced_engine import EnhancedRAGEngine, DOC_PRIORITY_BY_QUESTION_TYPE
from .retrieval import RetrievalResult, confidence_from_distance

__all__ = [
    "VectorStore",
    "RAGEngine",
    "EnhancedRAGEngine",
    "DOC_PRIORITY_BY_QUESTION_TYPE",
    "RetrievalResult",
    "confidence_from_distance",
]
