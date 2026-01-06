"""
Document parsers for extracting text from various file formats.
"""

import io
import logging
from typing import Optional
from abc import ABC, abstractmethod

import pypdf
import docx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Abstract base class for document parsers."""
    
    @abstractmethod
    def parse(self, content: bytes, filename: str = "") -> str:
        """
        Parse file content and extract text.
        
        Args:
            content: Raw file content in bytes
            filename: Name of the file (optional, for logging/extension check)
            
        Returns:
            Extracted text string
        """
        pass

class PDFParser(BaseParser):
    """Parser for PDF files."""
    
    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            # Create a file-like object from bytes
            pdf_file = io.BytesIO(content)
            reader = pypdf.PdfReader(pdf_file)
            
            text = []
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
                else:
                    logger.warning(f"Empty text in PDF {filename} page {page_num}")
            
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Error parsing PDF {filename}: {e}")
            raise ValueError(f"Failed to parse PDF: {e}")

class DocxParser(BaseParser):
    """Parser for Word documents (docx)."""
    
    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            
            text = []
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)
            
            return "\n".join(text)
        except Exception as e:
            logger.error(f"Error parsing DOCX {filename}: {e}")
            raise ValueError(f"Failed to parse DOCX: {e}")

class TextParser(BaseParser):
    """Parser for plain text files."""
    
    def parse(self, content: bytes, filename: str = "") -> str:
        try:
            # Try decoding as utf-8, fallback to latin-1 if needed
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                logger.warning(f"UTF-8 decode failed for {filename}, retrying with latin-1")
                return content.decode('latin-1')
        except Exception as e:
            logger.error(f"Error parsing TXT {filename}: {e}")
            raise ValueError(f"Failed to parse TXT: {e}")

def get_parser_for_file(filename: str) -> BaseParser:
    """Factory function to get appropriate parser based on filename extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    if ext == 'pdf':
        return PDFParser()
    elif ext in ['docx', 'doc']:
        return DocxParser()
    elif ext in ['txt', 'md', 'json', 'yaml', 'xml', 'csv']:
        return TextParser()
    else:
        # Default to text parser for unknown types, but log warning
        logger.warning(f"Unknown extension '{ext}' for file {filename}, using TextParser")
        return TextParser()
