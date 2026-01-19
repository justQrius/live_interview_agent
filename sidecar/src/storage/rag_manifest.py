"""
RAG Manifest - Persistent registry of documents in RAG storage.

Tracks what documents have been uploaded and indexed, enabling:
- App restart with existing RAG data (no re-upload needed)
- Cache refresh without re-uploading documents
- Clean "start fresh" functionality

Storage: ~/.live_interview_agent/rag_manifest.json
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Manifest schema version for future migrations
MANIFEST_VERSION = 1


class DocumentType(str, Enum):
    """Document types matching context/file_uploader.py"""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    INTERVIEWER_INFO = "interviewer_info"
    CUSTOM = "custom"


@dataclass
class ManifestDocument:
    """Record of a document in RAG storage."""
    filename: str
    document_type: str  # DocumentType value
    upload_timestamp: str  # ISO format
    file_size_bytes: int
    chunk_count: int
    # Base64 content for Gemini cache refresh (optional, can be large)
    content_b64: Optional[str] = None
    # Metadata for display
    preview: str = ""  # First 200 chars
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "document_type": self.document_type,
            "upload_timestamp": self.upload_timestamp,
            "file_size_bytes": self.file_size_bytes,
            "chunk_count": self.chunk_count,
            "content_b64": self.content_b64,
            "preview": self.preview,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManifestDocument":
        """Create from dictionary."""
        return cls(
            filename=data.get("filename", ""),
            document_type=data.get("document_type", "custom"),
            upload_timestamp=data.get("upload_timestamp", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            chunk_count=data.get("chunk_count", 0),
            content_b64=data.get("content_b64"),
            preview=data.get("preview", ""),
        )


@dataclass
class RagManifestData:
    """Complete manifest data structure."""
    version: int = MANIFEST_VERSION
    documents: List[ManifestDocument] = field(default_factory=list)
    last_cache_timestamp: Optional[str] = None  # ISO format
    last_modified: Optional[str] = None  # ISO format
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "documents": [d.to_dict() for d in self.documents],
            "last_cache_timestamp": self.last_cache_timestamp,
            "last_modified": self.last_modified,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RagManifestData":
        """Create from dictionary."""
        return cls(
            version=data.get("version", MANIFEST_VERSION),
            documents=[ManifestDocument.from_dict(d) for d in data.get("documents", [])],
            last_cache_timestamp=data.get("last_cache_timestamp"),
            last_modified=data.get("last_modified"),
        )


class RagManifest:
    """
    Manages the RAG manifest file for persistent document tracking.
    
    This enables the app to:
    1. Know what documents are already in ChromaDB on restart
    2. Re-create Gemini cache without re-uploading files
    3. Provide "Clear All" functionality
    """
    
    DEFAULT_PATH = Path.home() / ".live_interview_agent" / "rag_manifest.json"
    
    def __init__(self, manifest_path: Optional[Path] = None):
        """
        Initialize the manifest manager.
        
        Args:
            manifest_path: Custom path for manifest file. Defaults to ~/.live_interview_agent/rag_manifest.json
        """
        self.manifest_path = manifest_path or self.DEFAULT_PATH
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Optional[RagManifestData] = None
        
    def _load(self) -> RagManifestData:
        """Load manifest from disk."""
        if self._data is not None:
            return self._data
            
        if not self.manifest_path.exists():
            self._data = RagManifestData()
            return self._data
            
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            self._data = RagManifestData.from_dict(raw_data)
            logger.info(f"Loaded RAG manifest: {len(self._data.documents)} documents")
            return self._data
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            self._data = RagManifestData()
            return self._data
    
    def _save(self) -> bool:
        """Save manifest to disk."""
        if self._data is None:
            return False
            
        try:
            self._data.last_modified = datetime.now().isoformat()
            with open(self.manifest_path, 'w', encoding='utf-8') as f:
                json.dump(self._data.to_dict(), f, indent=2)
            logger.info(f"Saved RAG manifest: {len(self._data.documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to save manifest: {e}")
            return False
    
    def has_documents(self) -> bool:
        """Check if there are any documents in the manifest."""
        data = self._load()
        return len(data.documents) > 0
    
    def get_documents(self) -> List[ManifestDocument]:
        """Get all documents in the manifest."""
        return self._load().documents.copy()
    
    def get_document_count(self) -> int:
        """Get the number of documents in the manifest."""
        return len(self._load().documents)
    
    def add_document(
        self,
        filename: str,
        document_type: str,
        file_size_bytes: int,
        chunk_count: int,
        content_b64: Optional[str] = None,
        preview: str = "",
    ) -> ManifestDocument:
        """
        Add a document to the manifest.
        
        Args:
            filename: Original filename
            document_type: Type of document (resume, job_description, etc.)
            file_size_bytes: Size of the original file
            chunk_count: Number of chunks created for RAG
            content_b64: Base64 encoded content for cache refresh (optional)
            preview: First 200 chars of content
            
        Returns:
            The created ManifestDocument
        """
        data = self._load()
        
        # Remove existing document with same filename (replace)
        data.documents = [d for d in data.documents if d.filename != filename]
        
        doc = ManifestDocument(
            filename=filename,
            document_type=document_type,
            upload_timestamp=datetime.now().isoformat(),
            file_size_bytes=file_size_bytes,
            chunk_count=chunk_count,
            content_b64=content_b64,
            preview=preview[:200] if preview else "",
        )
        
        data.documents.append(doc)
        self._save()
        
        logger.info(f"Added document to manifest: {filename} ({document_type})")
        return doc
    
    def remove_document(self, filename: str) -> bool:
        """Remove a document from the manifest."""
        data = self._load()
        original_count = len(data.documents)
        data.documents = [d for d in data.documents if d.filename != filename]
        
        if len(data.documents) < original_count:
            self._save()
            logger.info(f"Removed document from manifest: {filename}")
            return True
        return False
    
    def update_cache_timestamp(self) -> None:
        """Update the last cache creation timestamp."""
        data = self._load()
        data.last_cache_timestamp = datetime.now().isoformat()
        self._save()
    
    def get_last_cache_timestamp(self) -> Optional[datetime]:
        """Get the last cache creation timestamp."""
        data = self._load()
        if data.last_cache_timestamp:
            try:
                return datetime.fromisoformat(data.last_cache_timestamp)
            except ValueError:
                return None
        return None
    
    def is_cache_expired(self, ttl_hours: float = 2.0) -> bool:
        """
        Check if the Gemini cache has expired.
        
        Args:
            ttl_hours: Cache TTL in hours (default 2 hours for Gemini)
            
        Returns:
            True if cache is expired or never created
        """
        last_cache = self.get_last_cache_timestamp()
        if last_cache is None:
            return True
            
        from datetime import timedelta
        expiry_time = last_cache + timedelta(hours=ttl_hours)
        return datetime.now() > expiry_time
    
    def clear(self) -> bool:
        """
        Clear the entire manifest.
        
        Returns:
            True if successful
        """
        self._data = RagManifestData()
        success = self._save()
        if success:
            logger.info("Cleared RAG manifest")
        return success
    
    def delete_file(self) -> bool:
        """
        Delete the manifest file from disk.
        
        Returns:
            True if successful or file didn't exist
        """
        try:
            if self.manifest_path.exists():
                self.manifest_path.unlink()
                logger.info(f"Deleted manifest file: {self.manifest_path}")
            self._data = None
            return True
        except Exception as e:
            logger.error(f"Failed to delete manifest file: {e}")
            return False
    
    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current RAG state for frontend.
        
        Returns:
            Dictionary with state information
        """
        data = self._load()
        return {
            "has_documents": len(data.documents) > 0,
            "document_count": len(data.documents),
            "documents": [
                {
                    "filename": d.filename,
                    "document_type": d.document_type,
                    "upload_timestamp": d.upload_timestamp,
                    "file_size_bytes": d.file_size_bytes,
                    "chunk_count": d.chunk_count,
                    "preview": d.preview,
                    # Don't include content_b64 in summary (too large)
                }
                for d in data.documents
            ],
            "cache_expired": self.is_cache_expired(),
            "last_cache_timestamp": data.last_cache_timestamp,
            "last_modified": data.last_modified,
        }
    
    def get_documents_for_cache(self) -> List[Dict[str, Any]]:
        """
        Get documents with content for cache refresh.
        
        Returns:
            List of documents with content_b64 for re-uploading to Gemini
        """
        data = self._load()
        return [
            {
                "filename": d.filename,
                "document_type": d.document_type,
                "content_b64": d.content_b64,
            }
            for d in data.documents
            if d.content_b64  # Only include docs with stored content
        ]
