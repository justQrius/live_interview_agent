"""
Gemini Context Caching Manager.

Manages the lifecycle of Gemini context caches to reduce latency and cost.
"""

import logging
from typing import Optional, List, Dict, Any
import datetime

from src.providers.gemini_client import GeminiClient
from .enhanced_manager import EnhancedContextManager

logger = logging.getLogger(__name__)

class GeminiCacheManager:
    """
    Manages Gemini Context Caching.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the cache manager.
        
        Args:
            api_key: Gemini API Key
        """
        self.client = GeminiClient(api_key=api_key)
        self.current_cache_name: Optional[str] = None
        self.cache_expiry: Optional[datetime.datetime] = None
        
    def create_cache_from_context(
        self, 
        context_manager: EnhancedContextManager,
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Create a cache from the current context in EnhancedContextManager.
        
        Args:
            context_manager: The context manager containing parsed documents
            ttl_seconds: TTL in seconds (default 2 hours)
            model: Model to use
            system_instruction: Optional system instruction
            
        Returns:
            Cache name (resource ID)
        """
        # Collect all text from chunks
        # We want to reconstruct the documents or at least provide all chunks
        # Grouping by document/source might be cleaner
        
        chunks = context_manager.get_all_enhanced_chunks()
        if not chunks:
            logger.warning("No context to cache")
            return ""
            
        # De-duplicate by source file to reconstruct documents if possible
        # Since we have full text in chunks, we can just concatenate
        # But wait, chunks are parts. 
        # Ideally we'd use the full text of the documents if we had it.
        # EnhancedContextManager doesn't seem to store full doc text persistently 
        # (it chunks immediately).
        # So we will aggregate chunks.
        
        # Sort chunks by source and position to reconstruct roughly
        sorted_chunks = sorted(chunks, key=lambda c: (c.metadata.get('source', ''), c.start_char))
        
        # Reconstruct text content
        # We'll just pass the chunks as a list of strings to Gemini
        contents = [c.text for c in sorted_chunks]
        
        logger.info(f"Creating cache from {len(contents)} chunks...")
        
        try:
            # If we already have a cache, delete it (we are updating context)
            if self.current_cache_name:
                self.delete_current_cache()
                
            cache = self.client.create_cache(
                contents=contents,
                ttl_seconds=ttl_seconds,
                model=model,
                system_instruction=system_instruction
            )
            
            self.current_cache_name = cache.name
            self.cache_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl_seconds)
            
            logger.info(f"Context cached successfully: {self.current_cache_name}")
            return self.current_cache_name
            
        except Exception as e:
            logger.error(f"Failed to create context cache: {e}")
            raise

    def get_cached_content_name(self) -> Optional[str]:
        """Get the current valid cache name."""
        if not self.current_cache_name:
            return None
            
        # Check expiry
        if self.cache_expiry and datetime.datetime.now() > self.cache_expiry:
            logger.info("Cache expired")
            self.current_cache_name = None
            self.cache_expiry = None
            return None
            
        return self.current_cache_name

    def delete_current_cache(self) -> None:
        """Delete the current active cache."""
        if self.current_cache_name:
            self.client.delete_cache(self.current_cache_name)
            self.current_cache_name = None
            self.cache_expiry = None
