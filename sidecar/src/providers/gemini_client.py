"""
Unified Gemini Client Wrapper.

Wraps the google-genai SDK (v1.57+) to provide a simplified interface for:
- File Uploads
- Context Caching
- Content Generation (with Thinking & System Instructions)
- Embeddings
- Web Search (Grounding)
"""

import logging
import time
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

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
        try:
            config = types.UploadFileConfig(mime_type=mime_type) if mime_type else None
            file_obj = self.client.files.upload(path=file_path, config=config)
            
            logger.info(f"Uploaded file {file_path} as {file_obj.name} ({file_obj.mime_type})")
            
            # Wait for processing to complete for video/audio
            if file_obj.state.name == "PROCESSING":
                logger.info(f"Waiting for {file_obj.name} to process...")
                while file_obj.state.name == "PROCESSING":
                    time.sleep(2)
                    file_obj = self.client.files.get(name=file_obj.name)
            
            if file_obj.state.name == "FAILED":
                raise ValueError(f"File processing failed: {file_obj.error.message}")
                
            return file_obj
            
        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {e}")
            raise

    def create_cache(
        self,
        contents: List[Any],
        ttl_seconds: int = 7200,
        model: str = "gemini-3-pro-preview",
        system_instruction: Optional[str] = None
    ) -> types.CachedContent:
        """
        Create a context cache.
        
        Args:
            contents: List of contents (text strings, File objects, or Content objects)
            ttl_seconds: Time to live in seconds (default 2 hours)
            model: Model to use (must support caching, e.g. gemini-3-pro-preview)
            system_instruction: Optional system instruction to bake into cache
            
        Returns:
            CachedContent object
        """
        try:
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
            
        except Exception as e:
            logger.error(f"Failed to create cache: {e}")
            raise

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
            model: Model name (e.g. 'gemini-2.0-flash-thinking-exp')
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
        try:
            config = types.EmbedContentConfig(
                output_dimensionality=output_dimensionality
            ) if output_dimensionality else None
            
            result = self.client.models.embed_content(
                model=model,
                contents=contents,
                config=config
            )
            
            # Normalize to list of lists
            if hasattr(result, 'embeddings'):
                return [e.values for e in result.embeddings]
            return []
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise
