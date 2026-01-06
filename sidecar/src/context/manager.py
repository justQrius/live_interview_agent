"""
Context Manager for handling document processing and storage.
"""

import logging
import base64
from typing import List, Dict, Optional
import uuid

from .parsers import get_parser_for_file
from .chunker import Chunker, Chunk

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages the lifecycle of context documents: parsing, chunking, and storage.
    """
    
    def __init__(self):
        """Initialize the context manager."""
        self.chunker = Chunker()
        self.chunks: List[Chunk] = []
        self.processed_files: Dict[str, dict] = {} # filename -> metadata
        
    async def process_file(self, filename: str, content_b64: str) -> int:
        """
        Process a file: decode, parse, and chunk.
        
        Args:
            filename: Name of the file
            content_b64: Base64 encoded file content
            
        Returns:
            Number of chunks created
        """
        try:
            # Decode base64
            try:
                content = base64.b64decode(content_b64)
            except Exception as e:
                logger.error(f"Failed to decode base64 content for {filename}: {e}")
                raise ValueError(f"Invalid base64 content for {filename}")
                
            # Get appropriate parser
            parser = get_parser_for_file(filename)
            
            # Parse text
            logger.info(f"Parsing {filename}...")
            text = parser.parse(content, filename)
            
            if not text.strip():
                logger.warning(f"No text extracted from {filename}")
                return 0
                
            # Chunk text
            logger.info(f"Chunking {filename}...")
            file_id = str(uuid.uuid4())
            metadata = {
                "source": filename,
                "file_id": file_id,
                "type": "upload"
            }
            
            new_chunks = self.chunker.chunk_text(text, metadata)
            
            # Store chunks
            self.chunks.extend(new_chunks)
            self.processed_files[filename] = {
                "id": file_id,
                "chunk_count": len(new_chunks),
                "timestamp": __import__("time").time()
            }
            
            logger.info(f"Processed {filename}: {len(new_chunks)} chunks created")
            return len(new_chunks)
            
        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            raise

    def get_all_chunks(self) -> List[Chunk]:
        """Return all stored chunks."""
        return self.chunks

    def clear_context(self) -> None:
        """Clear all stored context."""
        self.chunks.clear()
        self.processed_files.clear()
        logger.info("Context cleared")
