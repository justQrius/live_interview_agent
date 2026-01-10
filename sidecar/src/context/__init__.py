# Context management module
"""
Contains document parsing, chunking, and embedding functionality.
"""

from .chunker import Chunk, Chunker
from .manager import ContextManager
from .enhanced_manager import (
    DocumentType,
    EnhancedChunk,
    EnhancedContextManager,
    SECTION_PATTERNS,
)
from .hierarchical_chunker import (
    HierarchicalChunk,
    HierarchicalChunker,
)

__all__ = [
    "Chunk",
    "Chunker",
    "ContextManager",
    "DocumentType",
    "EnhancedChunk",
    "EnhancedContextManager",
    "HierarchicalChunk",
    "HierarchicalChunker",
    "SECTION_PATTERNS",
]
