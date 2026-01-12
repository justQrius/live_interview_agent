"""
Gemini File Uploader.

Handles uploading files to Google Gemini API for use in context caching and prompting.
Tracks uploaded files with document type metadata for intelligent cache creation.
"""

import asyncio
import base64
import logging
import os
import tempfile
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from google.genai import types

from src.providers.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents for context understanding."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    INTERVIEWER_INFO = "interviewer_info"
    CUSTOM = "custom"


import io
import docx

@dataclass
class UploadedFile:
    """Represents a file uploaded to Gemini."""
    gemini_file: Any  # types.File
    filename: str
    document_type: DocumentType
    mime_type: str
    size_bytes: int
    
    @property
    def name(self) -> str:
        """Get the Gemini resource name."""
        return self.gemini_file.name if self.gemini_file else ""


class GeminiFileUploader:
    """
    Handles file uploads to Gemini with tracking and document type awareness.
    
    Maintains a registry of uploaded files for cache creation and context management.
    """
    
    def __init__(self, api_key: str):
        self.client = GeminiClient(api_key=api_key)
        self._uploaded_files: Dict[str, UploadedFile] = {}  # filename -> UploadedFile
        self._files_by_type: Dict[DocumentType, List[UploadedFile]] = {}
        
    def upload_from_base64(
        self, 
        content_b64: str, 
        filename: str, 
        document_type: DocumentType = DocumentType.CUSTOM,
        mime_type: Optional[str] = None
    ) -> UploadedFile:
        """
        Upload a base64 encoded file to Gemini.
        
        Args:
            content_b64: Base64 encoded content
            filename: Original filename (used for extension detection)
            document_type: Type of document for context understanding
            mime_type: Optional mime type (auto-detected if None)
            
        Returns:
            UploadedFile object with Gemini file reference
        """
        # Auto-detect mime type if not provided
        ext = os.path.splitext(filename)[1].lower()
        if not mime_type:
            mime_type = self._detect_mime_type(ext)
        
        try:
            # Decode base64
            content = base64.b64decode(content_b64)
            original_size = len(content)
            
            upload_content = content
            upload_mime_type = mime_type
            upload_ext = ext
            
            # Convert DOCX to Text for Gemini Caching compatibility
            if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                try:
                    logger.info(f"Converting DOCX {filename} to text for Gemini compatibility...")
                    doc = docx.Document(io.BytesIO(content))
                    full_text = []
                    for para in doc.paragraphs:
                        full_text.append(para.text)
                    
                    text_content = '\n'.join(full_text)
                    upload_content = text_content.encode('utf-8')
                    upload_mime_type = 'text/plain'
                    upload_ext = '.txt'
                    logger.info(f"Converted {filename} to text ({len(upload_content)} bytes)")
                except Exception as conv_err:
                    logger.warning(f"Failed to convert DOCX {filename}: {conv_err}. Attempting raw upload.")
            
            size_bytes = len(upload_content)
            
            # Create temp file with correct extension
            with tempfile.NamedTemporaryFile(delete=False, suffix=upload_ext) as tmp:
                tmp.write(upload_content)
                tmp_path = tmp.name
                
            try:
                # Upload to Gemini
                logger.info(f"Uploading {filename} ({document_type.value}) to Gemini as {upload_mime_type}...")
                gemini_file = self.client.upload_file(tmp_path, mime_type=upload_mime_type)
                logger.info(f"Successfully uploaded {filename} as {gemini_file.name}")
                
                # Create tracked file record
                uploaded = UploadedFile(
                    gemini_file=gemini_file,
                    filename=filename,
                    document_type=document_type,
                    mime_type=upload_mime_type,  # Store the actual uploaded type
                    size_bytes=size_bytes
                )
                
                # Track the file
                self._uploaded_files[filename] = uploaded
                if document_type not in self._files_by_type:
                    self._files_by_type[document_type] = []
                self._files_by_type[document_type].append(uploaded)
                
                return uploaded
                
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise

    async def upload_from_base64_async(
        self,
        content_b64: str,
        filename: str,
        document_type: DocumentType = DocumentType.CUSTOM,
        mime_type: Optional[str] = None
    ) -> UploadedFile:
        """Async version of upload_from_base64."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.upload_from_base64(content_b64, filename, document_type, mime_type)
        )

    def _detect_mime_type(self, ext: str) -> str:
        """Detect MIME type from file extension."""
        mime_map = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.html': 'text/html',
            '.json': 'application/json',
        }
        return mime_map.get(ext, 'text/plain')

    def get_uploaded_files(self) -> List[UploadedFile]:
        """Get all uploaded files."""
        return list(self._uploaded_files.values())

    def get_files_by_type(self, doc_type: DocumentType) -> List[UploadedFile]:
        """Get uploaded files of a specific type."""
        return self._files_by_type.get(doc_type, [])

    def get_gemini_files(self) -> List[Any]:
        """Get all Gemini file objects for cache creation."""
        return [f.gemini_file for f in self._uploaded_files.values()]

    def get_file(self, filename: str) -> Optional[UploadedFile]:
        """Get an uploaded file by filename."""
        return self._uploaded_files.get(filename)

    def has_files(self) -> bool:
        """Check if any files have been uploaded."""
        return len(self._uploaded_files) > 0

    def get_document_manifest(self) -> str:
        """
        Generate a document manifest for cache system instruction.
        
        This helps the model understand what documents are available
        and how to attribute information correctly.
        """
        if not self._uploaded_files:
            return ""
        
        lines = ["The following documents have been uploaded for context:"]
        
        # Group by type for clarity
        type_labels = {
            DocumentType.RESUME: "CANDIDATE'S RESUME (Use for questions about the candidate's experience, skills, background)",
            DocumentType.JOB_DESCRIPTION: "JOB DESCRIPTION (Use for role requirements and expectations)",
            DocumentType.COMPANY_INFO: "COMPANY INFORMATION (Use for company culture, values, news)",
            DocumentType.INTERVIEWER_INFO: "INTERVIEWER BACKGROUND (Use ONLY for understanding interviewer context, NOT as candidate info)",
            DocumentType.SAMPLE_QA: "SAMPLE Q&A (Use for reference answers and frameworks)",
            DocumentType.INDUSTRY_RESEARCH: "INDUSTRY RESEARCH (Use for market trends and context)",
            DocumentType.CUSTOM: "ADDITIONAL CONTEXT",
        }
        
        for doc_type, files in self._files_by_type.items():
            if files:
                label = type_labels.get(doc_type, doc_type.value)
                lines.append(f"\n## {label}")
                for f in files:
                    lines.append(f"  - {f.filename}")
        
        lines.append("\n\nIMPORTANT INSTRUCTIONS FOR CONTEXT USAGE:")
        lines.append("1. **YOUR IDENTITY**: You are the candidate described in the 'CANDIDATE'S RESUME' above.")
        lines.append("   - When answering 'Tell me about yourself' or 'What is your experience', use ONLY the Resume.")
        lines.append("   - Do NOT attribute qualities/experience from the 'INTERVIEWER BACKGROUND' or 'JOB DESCRIPTION' to yourself.")
        lines.append("2. **THE INTERVIEWER**: Information in 'INTERVIEWER BACKGROUND' refers to the person ASKING the questions.")
        lines.append("   - Use this to build rapport or ask smart questions, but NEVER claim their experience as your own.")
        lines.append("3. **THE COMPANY**: Use 'COMPANY INFORMATION' to show research and enthusiasm.")
        
        return "\n".join(lines)

    def clear(self) -> None:
        """Clear all tracked files (does not delete from Gemini)."""
        self._uploaded_files.clear()
        self._files_by_type.clear()
        logger.info("Cleared uploaded files registry")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about uploaded files."""
        total_size = sum(f.size_bytes for f in self._uploaded_files.values())
        return {
            "total_files": len(self._uploaded_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": {
                doc_type.value: len(files) 
                for doc_type, files in self._files_by_type.items()
            }
        }
