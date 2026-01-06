"""
Text chunking logic for splitting documents into manageable segments.
"""

from dataclasses import dataclass
from typing import List

@dataclass
class Chunk:
    """A segment of text from a document."""
    text: str
    start_char: int
    end_char: int
    metadata: dict = None

class Chunker:
    """Splits text into chunks with overlap."""
    
    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Target size of each chunk in characters (approx 500 tokens)
            chunk_overlap: Number of characters to overlap between chunks (approx 50 tokens)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict = None) -> List[Chunk]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: The full text to split
            metadata: Metadata to attach to each chunk (e.g., source file)
            
        Returns:
            List of Chunk objects
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            # Calculate end position
            end = min(start + self.chunk_size, text_len)
            
            # If we're not at the end, try to break at a newline or space
            if end < text_len:
                # Look for the last newline within the chunk
                # We search back from the end up to half the chunk size
                search_limit = max(start, end - self.chunk_size // 2)
                
                # Try to find a paragraph break first
                last_newline = text.rfind('\n', search_limit, end)
                
                if last_newline != -1:
                    end = last_newline + 1  # Include the newline
                else:
                    # Fallback to space
                    last_space = text.rfind(' ', search_limit, end)
                    if last_space != -1:
                        end = last_space + 1
            
            chunk_text = text[start:end]
            
            # Create chunk object
            chunks.append(Chunk(
                text=chunk_text,
                start_char=start,
                end_char=end,
                metadata=metadata or {}
            ))
            
            # Move start forward, respecting overlap
            # If we reached the end, we're done
            if end == text_len:
                break
                
            start = end - self.chunk_overlap
            
            # Sanity check to prevent infinite loops if overlap >= chunk_size
            if start >= end:
                start = end
                
        return chunks
