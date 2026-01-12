"""
Gemini File Uploader.

Handles uploading files to Google Gemini API for use in context caching and prompting.
"""

import base64
import logging
import os
import tempfile
from typing import Optional
from google.genai import types

from src.providers.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

class GeminiFileUploader:
    """
    Handles file uploads to Gemini.
    """
    
    def __init__(self, api_key: str):
        self.client = GeminiClient(api_key=api_key)
        
    def upload_from_base64(self, content_b64: str, filename: str, mime_type: Optional[str] = None) -> types.File:
        """
        Upload a base64 encoded file to Gemini.
        
        Args:
            content_b64: Base64 encoded content
            filename: Original filename (used for extension detection)
            mime_type: Optional mime type (auto-detected if None)
            
        Returns:
            Uploaded Gemini File object
        """
        # Auto-detect mime type if not provided
        if not mime_type:
            ext = os.path.splitext(filename)[1].lower()
            if ext == '.pdf':
                mime_type = 'application/pdf'
            elif ext in ['.txt', '.md']:
                mime_type = 'text/plain'
            elif ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext == '.png':
                mime_type = 'image/png'
            else:
                mime_type = 'text/plain' # Default fallback
        
        try:
            # Decode base64
            content = base64.b64decode(content_b64)
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
                
            try:
                # Upload to Gemini
                logger.info(f"Uploading {filename} to Gemini...")
                file_obj = self.client.upload_file(tmp_path, mime_type=mime_type)
                logger.info(f"Successfully uploaded {filename} as {file_obj.name}")
                return file_obj
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise
