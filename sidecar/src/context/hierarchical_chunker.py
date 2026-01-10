"""
Hierarchical Chunker for creating parent-child chunk relationships.

Creates large parent chunks and smaller child chunks within each parent.
Children are used for precise retrieval, parents provide full context.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HierarchicalChunk:
    """
    A chunk with hierarchical relationship information.
    
    Attributes:
        id: Unique identifier for this chunk
        text: The text content
        level: "parent" or "child"
        parent_id: ID of parent chunk (None for parents)
        start_char: Starting character position in original text
        end_char: Ending character position in original text
        metadata: Additional metadata
    """
    id: str
    text: str
    level: str  # "parent" or "child"
    parent_id: Optional[str]
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class HierarchicalChunker:
    """
    Creates hierarchical chunks with parent-child relationships.
    
    Parent chunks (default 2048 chars) contain the full context.
    Child chunks (default 512 chars) are used for precise retrieval.
    When a child chunk is matched, its parent provides broader context.
    """
    
    def __init__(
        self,
        parent_size: int = 2048,
        child_size: int = 512,
        overlap: int = 100
    ):
        """
        Initialize the hierarchical chunker.
        
        Args:
            parent_size: Size of parent chunks in characters
            child_size: Size of child chunks in characters
            overlap: Overlap between consecutive chunks
        """
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap
    
    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[HierarchicalChunk]:
        """
        Create hierarchical chunks from text.
        
        Args:
            text: The text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of HierarchicalChunk objects (both parents and children)
        """
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        chunks: List[HierarchicalChunk] = []
        
        # First pass: create parent chunks
        parents = self._create_level_chunks(
            text=text,
            chunk_size=self.parent_size,
            overlap=self.overlap,
            level="parent",
            parent_id=None,
            metadata=metadata,
            base_offset=0
        )
        chunks.extend(parents)
        
        # Second pass: create child chunks within each parent
        for parent in parents:
            children = self._create_level_chunks(
                text=parent.text,
                chunk_size=self.child_size,
                overlap=self.overlap,
                level="child",
                parent_id=parent.id,
                metadata=metadata,
                base_offset=parent.start_char
            )
            chunks.extend(children)
        
        return chunks
    
    def _create_level_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        level: str,
        parent_id: Optional[str],
        metadata: Dict[str, Any],
        base_offset: int = 0
    ) -> List[HierarchicalChunk]:
        """
        Create chunks at a specific level.
        
        Args:
            text: Text to chunk
            chunk_size: Target size for chunks
            overlap: Overlap between chunks
            level: "parent" or "child"
            parent_id: ID of parent (None for parents)
            metadata: Metadata to attach
            base_offset: Character offset from original document start
            
        Returns:
            List of chunks at this level
        """
        if not text or not text.strip():
            return []
        
        chunks: List[HierarchicalChunk] = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # Calculate end position
            end = min(start + chunk_size, text_len)
            
            # Try to break at word boundary if not at end
            if end < text_len:
                end = self._find_break_point(text, start, end)
            
            chunk_text = text[start:end]
            
            # Skip empty chunks
            if chunk_text.strip():
                chunks.append(HierarchicalChunk(
                    id=str(uuid.uuid4()),
                    text=chunk_text,
                    level=level,
                    parent_id=parent_id,
                    start_char=base_offset + start,
                    end_char=base_offset + end,
                    metadata=dict(metadata)
                ))
            
            # Move forward, respecting overlap
            if end >= text_len:
                break
            
            start = end - overlap
            
            # Prevent infinite loop
            if start >= end:
                start = end
        
        return chunks
    
    def _find_break_point(self, text: str, start: int, end: int) -> int:
        """
        Find a good break point (word/sentence boundary).
        
        Args:
            text: Full text
            start: Start of current chunk
            end: Proposed end of chunk
            
        Returns:
            Adjusted end position at a word boundary
        """
        # Look for newline first (paragraph break)
        search_start = max(start, end - (end - start) // 2)
        last_newline = text.rfind('\n', search_start, end)
        if last_newline != -1:
            return last_newline + 1
        
        # Look for sentence end
        for punct in ['. ', '! ', '? ']:
            last_punct = text.rfind(punct, search_start, end)
            if last_punct != -1:
                return last_punct + 2
        
        # Fall back to space (word boundary)
        last_space = text.rfind(' ', search_start, end)
        if last_space != -1:
            return last_space + 1
        
        # No good break point found, use original end
        return end
    
    @staticmethod
    def get_parents(chunks: List[HierarchicalChunk]) -> List[HierarchicalChunk]:
        """
        Filter to only parent chunks.
        
        Args:
            chunks: List of all chunks
            
        Returns:
            List of parent chunks only
        """
        return [c for c in chunks if c.level == "parent"]
    
    @staticmethod
    def get_children(chunks: List[HierarchicalChunk]) -> List[HierarchicalChunk]:
        """
        Filter to only child chunks.
        
        Args:
            chunks: List of all chunks
            
        Returns:
            List of child chunks only
        """
        return [c for c in chunks if c.level == "child"]
    
    @staticmethod
    def get_children_of_parent(
        chunks: List[HierarchicalChunk],
        parent_id: str
    ) -> List[HierarchicalChunk]:
        """
        Get all children of a specific parent.
        
        Args:
            chunks: List of all chunks
            parent_id: ID of the parent chunk
            
        Returns:
            List of children belonging to that parent
        """
        return [c for c in chunks if c.parent_id == parent_id]
    
    @staticmethod
    def get_parent_for_child(
        chunks: List[HierarchicalChunk],
        child: HierarchicalChunk
    ) -> Optional[HierarchicalChunk]:
        """
        Get the parent chunk for a given child.
        
        Args:
            chunks: List of all chunks
            child: The child chunk
            
        Returns:
            Parent chunk or None if not found
        """
        if child.parent_id is None:
            return None
        
        for chunk in chunks:
            if chunk.id == child.parent_id:
                return chunk
        
        return None
