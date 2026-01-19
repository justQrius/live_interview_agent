"""
Gemini File Uploader with Persistence.

Handles uploading files to Google Gemini API for use in context caching and prompting.
Persists uploaded files to disk to allow cache reconstruction after app restart.
"""

import asyncio
import base64
import logging
import os
import shutil
import json
import tempfile
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path

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
    filename: str
    document_type: DocumentType
    mime_type: str
    size_bytes: int
    gemini_file: Optional[Any] = None  # types.File, None if loaded from disk but not yet uploaded
    timestamp: float = field(default_factory=time.time)
    
    @property
    def name(self) -> str:
        """Get the Gemini resource name."""
        return self.gemini_file.name if self.gemini_file else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "filename": self.filename,
            "document_type": self.document_type.value,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UploadedFile":
        """Create from dictionary."""
        return cls(
            filename=data["filename"],
            document_type=DocumentType(data["document_type"]),
            mime_type=data["mime_type"],
            size_bytes=data["size_bytes"],
            timestamp=data.get("timestamp", time.time()),
            gemini_file=None
        )


class GeminiFileUploader:
    """
    Handles file uploads to Gemini with persistence and document type awareness.
    
    Maintains a local copy of files in ~/.live_interview_agent/documents/
    to allow restoring context after app restart.
    """
    
    DEFAULT_STORAGE_DIR = ".live_interview_agent/documents"
    MANIFEST_FILE = "manifest.json"
    
    def __init__(self, api_key: str, storage_dir: Optional[str] = None):
        self.client = GeminiClient(api_key=api_key)
        self._uploaded_files: Dict[str, UploadedFile] = {}  # filename -> UploadedFile
        self._files_by_type: Dict[DocumentType, List[UploadedFile]] = {}
        
        # Setup storage directory
        if storage_dir:
            self.storage_path = Path(storage_dir)
        else:
            self.storage_path = Path.home() / self.DEFAULT_STORAGE_DIR
            
        self._init_storage()
        self._load_state()
        
    def _init_storage(self) -> None:
        """Initialize storage directory."""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            manifest_path = self.storage_path / self.MANIFEST_FILE
            if not manifest_path.exists():
                with open(manifest_path, 'w') as f:
                    json.dump({"files": {}}, f)
        except Exception as e:
            logger.error(f"Failed to initialize storage at {self.storage_path}: {e}")

    def _save_state(self) -> None:
        """Save manifest to disk."""
        try:
            manifest_path = self.storage_path / self.MANIFEST_FILE
            data = {
                "files": {
                    name: f.to_dict() 
                    for name, f in self._uploaded_files.items()
                }
            }
            with open(manifest_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")

    def _load_state(self) -> None:
        """Load state from disk."""
        try:
            manifest_path = self.storage_path / self.MANIFEST_FILE
            if not manifest_path.exists():
                return
                
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                
            loaded_count = 0
            files_data = data.get("files", [])
            
            # Handle both list format (new) and dict format (legacy)
            if isinstance(files_data, list):
                # New format: list of file objects
                for file_data in files_data:
                    name = file_data.get("filename")
                    if not name:
                        continue
                    # Verify file exists on disk
                    file_path = self.storage_path / name
                    if file_path.exists():
                        uploaded_file = UploadedFile.from_dict(file_data)
                        self._uploaded_files[name] = uploaded_file
                        
                        # Add to type index
                        doc_type = uploaded_file.document_type
                        if doc_type not in self._files_by_type:
                            self._files_by_type[doc_type] = []
                        self._files_by_type[doc_type].append(uploaded_file)
                        loaded_count += 1
                    else:
                        logger.warning(f"File {name} in manifest but not found on disk")
            elif isinstance(files_data, dict):
                # Legacy format: dict with filename as key
                for name, file_data in files_data.items():
                    # Verify file exists on disk
                    file_path = self.storage_path / name
                    if file_path.exists():
                        uploaded_file = UploadedFile.from_dict(file_data)
                        self._uploaded_files[name] = uploaded_file
                        
                        # Add to type index
                        doc_type = uploaded_file.document_type
                        if doc_type not in self._files_by_type:
                            self._files_by_type[doc_type] = []
                        self._files_by_type[doc_type].append(uploaded_file)
                        loaded_count += 1
                    else:
                        logger.warning(f"File {name} in manifest but not found on disk")
            
            if loaded_count > 0:
                logger.info(f"Loaded {loaded_count} files from persistence storage")
                
        except Exception as e:
            logger.error(f"Failed to load state: {e}")

    def _save_file_to_disk(self, filename: str, content: bytes) -> None:
        """Save file content to storage directory."""
        try:
            file_path = self.storage_path / filename
            with open(file_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Failed to save file {filename} to disk: {e}")

    def upload_from_base64(
        self, 
        content_b64: str, 
        filename: str, 
        document_type: DocumentType = DocumentType.CUSTOM,
        mime_type: Optional[str] = None
    ) -> UploadedFile:
        """
        Upload a base64 encoded file to Gemini and persist locally.
        
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
            
            # PERSISTENCE: Save to local disk first
            self._save_file_to_disk(filename, upload_content)
            
            # Create temporary file for upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=upload_ext) as tmp:
                tmp.write(upload_content)
                tmp_path = tmp.name
                
            try:
                # Upload to Gemini
                logger.info(f"Uploading {filename} to Gemini ({size_bytes} bytes)...")
                gemini_file = self.client.client.files.upload(
                    file=tmp_path,
                    config=types.UploadFileConfig(
                        display_name=filename,
                        mime_type=upload_mime_type
                    )
                )
                logger.info(f"Uploaded {filename} as {gemini_file.name}")
                
                # Create UploadedFile record
                uploaded_file = UploadedFile(
                    filename=filename,
                    document_type=document_type,
                    mime_type=upload_mime_type,
                    size_bytes=size_bytes,
                    gemini_file=gemini_file
                )
                
                # Update registry
                self._uploaded_files[filename] = uploaded_file
                
                if document_type not in self._files_by_type:
                    self._files_by_type[document_type] = []
                self._files_by_type[document_type].append(uploaded_file)
                
                # Update manifest
                self._update_manifest()
                
                return uploaded_file
                
            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            raise

    async def upload_from_base64_async(
        self, 
        content_b64: str, 
        filename: str, 
        document_type: DocumentType = DocumentType.CUSTOM,
        mime_type: Optional[str] = None
    ) -> UploadedFile:
        """Async wrapper for upload_from_base64."""
        return await asyncio.to_thread(
            self.upload_from_base64,
            content_b64,
            filename,
            document_type,
            mime_type
        )
            
    def get_uploaded_files(self) -> List["UploadedFile"]:
        """Get list of UploadedFile wrapper objects for cache creation.
        
        Returns:
            List of UploadedFile objects (each has .gemini_file, .filename, etc.)
        """
        return [f for f in self._uploaded_files.values() if f.gemini_file]

    def get_document_manifest(self) -> str:
        """Get formatted manifest of documents for cache metadata.
        
        Returns:
            A formatted string describing all uploaded documents, suitable for
            inclusion in the system prompt.
        """
        if not self._uploaded_files:
            return ""
        
        lines = ["## Document Manifest", ""]
        
        # Group by type
        by_type: Dict[DocumentType, List[UploadedFile]] = {}
        for f in self._uploaded_files.values():
            if f.document_type not in by_type:
                by_type[f.document_type] = []
            by_type[f.document_type].append(f)
        
        for doc_type, files in by_type.items():
            lines.append(f"### {doc_type.value.replace('_', ' ').title()}")
            for f in files:
                size_kb = f.size_bytes / 1024
                lines.append(f"- {f.filename} ({size_kb:.1f} KB)")
            lines.append("")
        
        return "\n".join(lines)
        
    def has_files(self) -> bool:
        """Check if any files have been uploaded."""
        return len(self._uploaded_files) > 0

    def clear(self) -> None:
        """Clear all uploaded files (local and remote)."""
        # Delete from Gemini
        for f in self._uploaded_files.values():
            if f.gemini_file:
                try:
                    self.client.client.files.delete(name=f.gemini_file.name)
                except Exception as e:
                    logger.warning(f"Failed to delete file {f.gemini_file.name}: {e}")
        
        # Clear local registry
        self._uploaded_files.clear()
        self._files_by_type.clear()
        
        # Clear local storage
        try:
            if self.storage_path.exists():
                shutil.rmtree(self.storage_path)
                self._init_storage()
        except Exception as e:
            logger.error(f"Failed to clear storage directory: {e}")
            
    def _update_manifest(self) -> None:
        """Update manifest file on disk."""
        try:
            manifest_path = self.storage_path / self.MANIFEST_FILE
            
            data = {
                "updated_at": time.time(),
                "files": [f.to_dict() for f in self._uploaded_files.values()]
            }
            
            with open(manifest_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update manifest: {e}")

    def _detect_mime_type(self, ext: str) -> str:
        """Detect mime type from extension."""
        mime_types = {
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.doc': 'application/msword',
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.xml': 'text/xml',
            '.html': 'text/html',
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.ts': 'text/typescript',
            '.java': 'text/x-java-source',
            '.c': 'text/x-c',
            '.cpp': 'text/x-c++',
            '.h': 'text/x-c',
            '.hpp': 'text/x-c++'
        }
        return mime_types.get(ext.lower(), 'text/plain')
