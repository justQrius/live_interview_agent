"""
Gemini Context Caching Manager.

Manages the lifecycle of Gemini context caches to reduce latency and cost.
Includes atomic cache swapping, version tracking, and async-safe operations.
"""

import asyncio
import hashlib
import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import datetime

from src.providers.gemini_client import GeminiClient
from .enhanced_manager import EnhancedContextManager

if TYPE_CHECKING:
    from .file_uploader import UploadedFile

logger = logging.getLogger(__name__)


from src.providers.llm.prompts import MASTER_SYSTEM_PROMPT

class GeminiCacheManager:
    """
    Manages Gemini Context Caching with atomic operations.
    
    Features:
    - Atomic cache swap (create new before deleting old)
    - Version tracking via content hash
    - Async-safe with asyncio.Lock
    - Profile-aware cache invalidation
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
        self._cache_lock = asyncio.Lock()
        self._content_version: Optional[str] = None
        self._profile_version: Optional[str] = None
    
    def _compute_content_hash(self, contents: List[str], profile_text: Optional[str] = None) -> str:
        """
        Compute a hash of the cached content for version tracking.
        
        Args:
            contents: List of content strings
            profile_text: Optional candidate profile text
            
        Returns:
            SHA256 hash of combined content
        """
        hasher = hashlib.sha256()
        for content in sorted(contents):  # Sort for deterministic hashing
            hasher.update(content.encode('utf-8'))
        if profile_text:
            hasher.update(profile_text.encode('utf-8'))
        return hasher.hexdigest()[:16]  # First 16 chars for readability
    
    def get_content_version(self) -> Optional[str]:
        """Get the current content version hash."""
        return self._content_version
    
    def get_profile_version(self) -> Optional[str]:
        """Get the current profile version hash."""
        return self._profile_version
    
    async def create_cache_from_context_async(
        self, 
        context_manager: EnhancedContextManager,
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",  # SYNC: Must match GeminiLLMProvider.DEFAULT_MODEL
        system_instruction: Optional[str] = None,
        profile_text: Optional[str] = None
    ) -> str:
        """
        Create a cache from the current context with atomic swap (async).
        
        Uses atomic swap pattern:
        1. Create new cache
        2. Swap pointer atomically
        3. Delete old cache in background
        
        Args:
            context_manager: The context manager containing parsed documents
            ttl_seconds: TTL in seconds (default 2 hours)
            model: Model to use
            system_instruction: Optional system instruction
            profile_text: Optional candidate profile to include in cache
            
        Returns:
            Cache name (resource ID)
        """
        async with self._cache_lock:
            result: str = await asyncio.to_thread(
                self._create_cache_atomic,
                context_manager, ttl_seconds, model, system_instruction, profile_text
            )
            return result
    
    def _create_cache_atomic(
        self,
        context_manager: EnhancedContextManager,
        ttl_seconds: int,
        model: str,
        system_instruction: Optional[str],
        profile_text: Optional[str]
    ) -> str:
        """
        Internal atomic cache creation (runs in thread pool).
        """
        chunks = context_manager.get_all_enhanced_chunks()
        if not chunks:
            logger.warning("No context to cache")
            return ""
        
        # Sort chunks by source and position to reconstruct roughly
        sorted_chunks = sorted(chunks, key=lambda c: (c.metadata.get('source', ''), c.start_char))
        contents = [c.text for c in sorted_chunks]
        
        # Compute version hash
        new_content_version = self._compute_content_hash(contents, profile_text)
        new_profile_version = hashlib.sha256(
            (profile_text or "").encode('utf-8')
        ).hexdigest()[:16] if profile_text else None
        
        # Check if content unchanged
        if (self.current_cache_name and 
            self._content_version == new_content_version and
            self._profile_version == new_profile_version):
            logger.info(f"Cache content unchanged (version: {new_content_version}), skipping refresh")
            return self.current_cache_name
        
        logger.info(f"Creating cache from {len(contents)} chunks (version: {new_content_version})...")
        
        # Include profile in system instruction if provided
        effective_instruction = system_instruction or ""
        if profile_text:
            effective_instruction = f"{profile_text}\n\n{effective_instruction}" if effective_instruction else profile_text
        
        try:
            # Create NEW cache first (before touching old one)
            new_cache = self.client.create_cache(
                contents=contents,
                ttl_seconds=ttl_seconds,
                model=model,
                system_instruction=effective_instruction if effective_instruction else None
            )
            
            # Extract the cache name (cast for type safety since SDK types are incomplete)
            new_cache_name: str = str(new_cache.name)
            
            # Store reference to old cache for cleanup
            old_cache_name = self.current_cache_name
            
            # ATOMIC SWAP: Update pointers
            self.current_cache_name = new_cache_name
            self.cache_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl_seconds)
            self._content_version = new_content_version
            self._profile_version = new_profile_version
            
            logger.info(f"Context cached successfully: {new_cache_name} (version: {new_content_version})")
            
            # Delete old cache AFTER swap (non-blocking if possible)
            if old_cache_name:
                try:
                    self.client.delete_cache(old_cache_name)
                    logger.info(f"Deleted old cache: {old_cache_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old cache {old_cache_name}: {e}")
            
            return new_cache_name
            
        except Exception as e:
            logger.error(f"Failed to create context cache: {e}")
            raise
    
    def create_cache_from_context(
        self, 
        context_manager: EnhancedContextManager,
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",  # SYNC: Must match GeminiLLMProvider.DEFAULT_MODEL
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Create a cache from the current context (sync, legacy API).
        
        Note: Prefer create_cache_from_context_async for async code.
        This method still uses atomic swap but without async lock.
        """
        return self._create_cache_atomic(
            context_manager, ttl_seconds, model, system_instruction, None
        )

    async def create_cache_from_files_async(
        self,
        uploaded_files: List["UploadedFile"],
        document_manifest: str,
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",  # SYNC: Must match GeminiLLMProvider.DEFAULT_MODEL
        profile_text: Optional[str] = None
    ) -> str:
        """
        Create a cache from uploaded Gemini Files (async).
        
        This is the preferred method for Cache-First architecture.
        Uses raw files uploaded to Gemini File API instead of text chunks.
        
        Args:
            uploaded_files: List of UploadedFile objects from GeminiFileUploader
            document_manifest: Document manifest with type labels for system instruction
            ttl_seconds: TTL in seconds (default 2 hours)
            model: Model to use
            profile_text: Optional candidate profile to include in cache
            
        Returns:
            Cache name (resource ID)
        """
        async with self._cache_lock:
            result: str = await asyncio.to_thread(
                self._create_cache_from_files_atomic,
                uploaded_files, document_manifest, ttl_seconds, model, profile_text
            )
            return result

    def _create_cache_from_files_atomic(
        self,
        uploaded_files: List["UploadedFile"],
        document_manifest: str,
        ttl_seconds: int,
        model: str,
        profile_text: Optional[str]
    ) -> str:
        """
        Internal atomic cache creation from files (runs in thread pool).
        """
        if not uploaded_files:
            logger.warning("No files to cache")
            return ""
        
        # Extract Gemini file objects
        gemini_files = [f.gemini_file for f in uploaded_files]
        
        # Compute version hash from file names + sizes
        hasher = hashlib.sha256()
        for f in sorted(uploaded_files, key=lambda x: x.filename):
            hasher.update(f.filename.encode('utf-8'))
            hasher.update(str(f.size_bytes).encode('utf-8'))
            hasher.update(f.document_type.value.encode('utf-8'))
        if profile_text:
            hasher.update(profile_text.encode('utf-8'))
        new_content_version = hasher.hexdigest()[:16]
        
        new_profile_version = hashlib.sha256(
            (profile_text or "").encode('utf-8')
        ).hexdigest()[:16] if profile_text else None
        
        # Check if content unchanged
        if (self.current_cache_name and 
            self._content_version == new_content_version and
            self._profile_version == new_profile_version):
            logger.info(f"Cache content unchanged (version: {new_content_version}), skipping refresh")
            return self.current_cache_name
        
        logger.info(f"Creating cache from {len(uploaded_files)} files (version: {new_content_version})...")
        
        # Build system instruction with document manifest and profile
        # CRITICAL: Since we can't pass system_instruction during generation when using cache,
        # we MUST include the MASTER_SYSTEM_PROMPT here in the cache configuration.
        system_parts = [MASTER_SYSTEM_PROMPT]
        
        if document_manifest:
            system_parts.append(document_manifest)
        if profile_text:
            system_parts.append(f"\n\n## CANDIDATE PROFILE (HIGH PRIORITY)\n{profile_text}")
        
        effective_instruction = "\n\n".join(system_parts)
        
        try:
            # Create NEW cache with file objects
            new_cache = self.client.create_cache(
                contents=gemini_files,
                ttl_seconds=ttl_seconds,
                model=model,
                system_instruction=effective_instruction
            )
            
            new_cache_name: str = str(new_cache.name)
            
            # Store reference to old cache for cleanup
            old_cache_name = self.current_cache_name
            
            # ATOMIC SWAP: Update pointers
            self.current_cache_name = new_cache_name
            self.cache_expiry = datetime.datetime.now() + datetime.timedelta(seconds=ttl_seconds)
            self._content_version = new_content_version
            self._profile_version = new_profile_version
            
            logger.info(f"File-based cache created: {new_cache_name} (version: {new_content_version})")
            
            # Delete old cache AFTER swap
            if old_cache_name:
                try:
                    self.client.delete_cache(old_cache_name)
                    logger.info(f"Deleted old cache: {old_cache_name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old cache {old_cache_name}: {e}")
            
            return new_cache_name
            
        except Exception as e:
            logger.error(f"Failed to create file-based cache: {e}")
            raise

    def create_cache_from_files(
        self,
        uploaded_files: List["UploadedFile"],
        document_manifest: str,
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",  # SYNC: Must match GeminiLLMProvider.DEFAULT_MODEL
        profile_text: Optional[str] = None
    ) -> str:
        """
        Create a cache from uploaded Gemini Files (sync).
        
        Note: Prefer create_cache_from_files_async for async code.
        """
        return self._create_cache_from_files_atomic(
            uploaded_files, document_manifest, ttl_seconds, model, profile_text
        )

    def get_cached_content_name(self) -> Optional[str]:
        """Get the current valid cache name."""
        if not self.current_cache_name:
            return None
            
        # Check expiry
        if self.cache_expiry and datetime.datetime.now() > self.cache_expiry:
            logger.info("Cache expired")
            self.current_cache_name = None
            self.cache_expiry = None
            self._content_version = None
            self._profile_version = None
            return None
            
        return self.current_cache_name
    
    def needs_refresh(self, profile_text: Optional[str] = None) -> bool:
        """
        Check if cache needs refresh due to profile change.
        
        Args:
            profile_text: Current candidate profile text
            
        Returns:
            True if cache should be refreshed
        """
        if not self.current_cache_name:
            return True
        
        if self.cache_expiry and datetime.datetime.now() > self.cache_expiry:
            return True
        
        if profile_text:
            current_hash = hashlib.sha256(profile_text.encode('utf-8')).hexdigest()[:16]
            if current_hash != self._profile_version:
                logger.info(f"Profile changed (old: {self._profile_version}, new: {current_hash})")
                return True
        
        return False

    def delete_current_cache(self) -> None:
        """Delete the current active cache."""
        if self.current_cache_name:
            self.client.delete_cache(self.current_cache_name)
            self.current_cache_name = None
            self.cache_expiry = None
            self._content_version = None
            self._profile_version = None
