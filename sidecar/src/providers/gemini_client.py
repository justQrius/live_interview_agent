"""
Unified Gemini Client Wrapper.

Wraps the google-genai SDK (v1.57+) to provide a simplified interface for:
- File Uploads
- Context Caching
- Content Generation (with Thinking & System Instructions)
- Embeddings
- Web Search (Grounding)

Includes built-in retry logic with exponential backoff for resilience.
"""

import logging
import time
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# Retry configuration constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 60.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

# Timeout configurations by operation type
OPERATION_TIMEOUTS = {
    "upload": 120,  # File uploads can be slow
    "cache": 60,    # Cache creation
    "generate": 30, # Content generation
    "embed": 10,    # Embeddings
}


def _should_retry(exception: Exception) -> bool:
    """Check if an exception is retryable."""
    error_str = str(exception).lower()
    
    # Check for rate limiting or transient errors
    if "429" in error_str or "rate" in error_str:
        return True
    if "503" in error_str or "unavailable" in error_str:
        return True
    if "500" in error_str or "internal" in error_str:
        return True
    if "timeout" in error_str:
        return True
    if "connection" in error_str:
        return True
    
    return False


def _retry_with_backoff(
    operation_name: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_INITIAL_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER
):
    """
    Decorator for retrying operations with exponential backoff.
    
    Args:
        operation_name: Name of the operation for logging
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        backoff_multiplier: Multiplier for exponential backoff
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= max_retries:
                        logger.error(f"{operation_name} failed after {max_retries + 1} attempts: {e}")
                        raise
                    
                    if not _should_retry(e):
                        logger.error(f"{operation_name} failed with non-retryable error: {e}")
                        raise
                    
                    logger.warning(
                        f"{operation_name} attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay = min(delay * backoff_multiplier, max_delay)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class GeminiClient:
    """
    Unified client for Google Gemini features.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Google AI API Key
        """
        self.client = genai.Client(api_key=api_key)
        self.api_key = api_key
        logger.info("Initialized Gemini Client (google-genai SDK)")

    def upload_file(self, file_path: str, mime_type: Optional[str] = None) -> types.File:
        """
        Upload a file for use in prompts or caching.
        
        Args:
            file_path: Path to the local file
            mime_type: Optional MIME type (e.g. 'application/pdf')
            
        Returns:
            Uploaded File object
        """
        return self._upload_file_with_retry(file_path, mime_type)
    
    @_retry_with_backoff("file_upload", max_retries=3, initial_delay=2.0)
    def _upload_file_with_retry(self, file_path: str, mime_type: Optional[str] = None) -> types.File:
        """Internal file upload with retry logic."""
        config = types.UploadFileConfig(mime_type=mime_type) if mime_type else None
        file_obj = self.client.files.upload(file=file_path, config=config)
        
        logger.info(f"Uploaded file {file_path} as {file_obj.name} ({file_obj.mime_type})")
        
        # Wait for processing to complete for video/audio
        if file_obj.state.name == "PROCESSING":
            logger.info(f"Waiting for {file_obj.name} to process...")
            max_wait = 120  # Maximum wait time in seconds
            waited = 0
            while file_obj.state.name == "PROCESSING" and waited < max_wait:
                time.sleep(2)
                waited += 2
                file_obj = self.client.files.get(name=file_obj.name)
        
        if file_obj.state.name == "FAILED":
            raise ValueError(f"File processing failed: {file_obj.error.message}")
            
        return file_obj

    def create_cache(
        self,
        contents: List[Any],
        ttl_seconds: int = 7200,
        model: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None
    ) -> types.CachedContent:
        """
        Create a context cache.
        
        Args:
            contents: List of contents (text strings, File objects, or Content objects)
            ttl_seconds: Time to live in seconds (default 2 hours)
            model: Model to use (must support caching)
            system_instruction: Optional system instruction to bake into cache
            
        Returns:
            CachedContent object
        """
        return self._create_cache_with_retry(contents, ttl_seconds, model, system_instruction)
    
    @_retry_with_backoff("cache_creation", max_retries=3, initial_delay=2.0)
    def _create_cache_with_retry(
        self,
        contents: List[Any],
        ttl_seconds: int,
        model: str,
        system_instruction: Optional[str]
    ) -> types.CachedContent:
        """Internal cache creation with retry logic."""
        config = types.CreateCachedContentConfig(
            contents=contents,
            ttl=f"{ttl_seconds}s",
            system_instruction=system_instruction
        )
        
        cache = self.client.caches.create(
            model=model,
            config=config
        )
        
        logger.info(f"Created context cache {cache.name} (exp: {cache.expire_time})")
        return cache

    def get_cache(self, name: str) -> types.CachedContent:
        """Get an existing cache by name."""
        return self.client.caches.get(name=name)
        
    def delete_cache(self, name: str) -> None:
        """Delete a cache by name."""
        try:
            self.client.caches.delete(name=name)
            logger.info(f"Deleted cache {name}")
        except Exception as e:
            logger.warning(f"Failed to delete cache {name}: {e}")

    def generate_content(
        self,
        model: str,
        contents: Any,
        cached_content_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
        thinking_budget: Optional[int] = None,
        temperature: Optional[float] = None,
        web_search: bool = False,
        json_mode: bool = False,
        stream: bool = False
    ) -> Union[types.GenerateContentResponse, Any]:
        """
        Generate content using Gemini.
        
        Args:
            model: Model name (e.g. 'gemini-3-flash-preview-thinking-exp')
            contents: Prompt contents
            cached_content_name: Optional name of cached context to use
            system_instruction: System prompt (overrides cached one if provided)
            thinking_budget: Token budget for thinking (if model supports it)
            temperature: Generation temperature
            web_search: Enable Google Search grounding
            json_mode: Force JSON output
            stream: Enable streaming response
            
        Returns:
            GenerateContentResponse or iterator if stream=True
        """
        try:
            tools = []
            if web_search:
                tools.append(types.Tool(google_search=types.GoogleSearch()))
                
            config = types.GenerateContentConfig(
                cached_content=cached_content_name,
                system_instruction=system_instruction,
                temperature=temperature,
                tools=tools if tools else None
            )
            
            if thinking_budget and thinking_budget > 0:
                config.thinking_config = types.ThinkingConfig(
                    include_thoughts=True
                )
            
            if json_mode:
                config.response_mime_type = "application/json"
                
            if stream:
                return self.client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config
                )
            else:
                return self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config
                )
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def embed_content(
        self,
        model: str,
        contents: Union[str, List[str]],
        output_dimensionality: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings.
        
        Args:
            model: Embedding model (e.g. 'text-embedding-004')
            contents: Single string or list of strings
            output_dimensionality: Optional dimension truncation
            
        Returns:
            List of embedding vectors
        """
        # Filter empty content to prevent API errors 400 INVALID_ARGUMENT
        if isinstance(contents, str):
            contents = [contents]
            
        # Replace empty strings with a placeholder space to maintain indices
        # This is critical because the vector store expects N embeddings for N inputs
        # We explicitly check for None or empty string or whitespace-only
        processed_contents = [c if c and c.strip() else " " for c in contents]
            
        return self._embed_content_with_retry(model, processed_contents, output_dimensionality)
    
    @_retry_with_backoff("embedding", max_retries=3, initial_delay=1.0)
    def _embed_content_with_retry(
        self,
        model: str,
        contents: Union[str, List[str]],
        output_dimensionality: Optional[int]
    ) -> List[List[float]]:
        """Internal embedding with retry logic."""
        config = types.EmbedContentConfig(
            output_dimensionality=output_dimensionality
        ) if output_dimensionality else None
        
        # Handle single string case
        if isinstance(contents, str):
            contents = [contents]
            
        all_embeddings = []
        BATCH_SIZE = 100
        
        # Process in batches to avoid SDK/API limits
        for i in range(0, len(contents), BATCH_SIZE):
            batch = contents[i:i + BATCH_SIZE]
            
            result = self.client.models.embed_content(
                model=model,
                contents=batch,
                config=config
            )
            
            # Normalize to list of lists
            if hasattr(result, 'embeddings'):
                all_embeddings.extend([e.values for e in result.embeddings])
                
        return all_embeddings
