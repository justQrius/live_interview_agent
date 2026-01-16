"""
Enhanced Context Manager with multi-type document support.

Extends ContextManager to support:
- Document type tagging (resume, job description, etc.)
- PRE-CHUNKING section detection (detect sections BEFORE splitting)
- Hierarchical parent-child chunking for better RAG
- Q&A atomic chunking for sample_qa documents
- Type-filtered retrieval for intelligent context management
"""

import base64
import hashlib
import logging
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .parsers import get_parser_for_file
from .hierarchical_chunker import HierarchicalChunker, HierarchicalChunk

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents that can be processed."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    INTERVIEWER_INFO = "interviewer_info"
    CUSTOM = "custom"


@dataclass
class EnhancedChunk:
    """
    An enhanced chunk with rich metadata for intelligent retrieval.
    
    Attributes:
        id: Unique identifier for this chunk
        text: The actual text content
        document_type: Type of document this chunk came from
        section: Auto-detected section (e.g., "experience", "requirements")
        relevance_tags: Keywords for relevance matching
        parent_chunk_id: ID of parent chunk for hierarchical relationships
        level: "parent" or "child" for hierarchical retrieval
        start_char: Starting character position in original document
        end_char: Ending character position in original document
        metadata: Additional metadata (source file, timestamps, etc.)
    """
    id: str
    text: str
    document_type: DocumentType
    section: str
    relevance_tags: List[str]
    parent_chunk_id: Optional[str]
    level: str  # "parent" or "child"
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# Section detection patterns for different document types
SECTION_PATTERNS: Dict[DocumentType, Dict[str, str]] = {
    DocumentType.RESUME: {
        "experience": r"(?i)^[\s#*\-]*(?:work\s+)?experience|work\s+history|employment|professional\s+background",
        "education": r"(?i)^[\s#*\-]*education|academic|degrees?|university|college",
        "skills": r"(?i)^[\s#*\-]*(?:technical\s+)?skills|technologies|competencies|proficiencies",
        "summary": r"(?i)^[\s#*\-]*summary|objective|profile|about\s+me|introduction",
        "projects": r"(?i)^[\s#*\-]*projects|portfolio|work\s+samples",
        "certifications": r"(?i)^[\s#*\-]*certifications?|certificates?|licenses?",
        "achievements": r"(?i)^[\s#*\-]*achievements?|accomplishments?|awards?",
    },
    DocumentType.JOB_DESCRIPTION: {
        "requirements": r"(?i)^[\s#*\-]*(?:what\s+you.ll?\s+)?(?:bring|need)|requirements?|qualifications?|must\s+have|required\s+skills",
        "responsibilities": r"(?i)^[\s#*\-]*(?:how\s+will\s+you\s+)?contribute|responsibilities|duties|(?:what\s+)?you.ll?\s+do",
        "benefits": r"(?i)^[\s#*\-]*benefits?|perks?|compensation|what\s+we\s+offer|why\s+join",
        "about": r"(?i)^[\s#*\-]*about\s+(?:us|the\s+company|our)|who\s+are\s+we|company|our\s+(?:mission|team|culture)",
        "nice_to_have": r"(?i)^[\s#*\-]*nice\s+to\s+have|preferred|bonus|plus",
    },
    DocumentType.INTERVIEWER_INFO: {
        "background": r"(?i)^[\s#*\-]*(?:key\s+)?background|current\s+role|experience",
        "expertise": r"(?i)^[\s#*\-]*(?:critical\s+)?expertise|domain\s+knowledge|technical",
        "leadership": r"(?i)^[\s#*\-]*leadership|personality|traits",
        "recommendations": r"(?i)^[\s#*\-]*(?:interview\s+)?(?:preparation\s+)?recommendations?|tips?|what\s+(?:to|not\s+to)\s+do",
        "questions": r"(?i)^[\s#*\-]*questions?\s+to\s+ask|key\s+questions",
    },
    DocumentType.COMPANY_INFO: {
        "overview": r"(?i)^[\s#*\-]*overview|about|company\s+(?:overview|description)",
        "products": r"(?i)^[\s#*\-]*products?|services?|offerings?|solutions?",
        "culture": r"(?i)^[\s#*\-]*culture|values|mission|vision",
        "news": r"(?i)^[\s#*\-]*news|recent|updates?|announcements?",
    },
}

# Q&A detection patterns for SAMPLE_QA documents
QA_PATTERNS = [
    r"^(?:Q\d*[:.\\s]|Question\\s*\\d*[:.\\s])",  # Q: or Q1: or Question:
    r"^(?:\\*\\*Q\\d*[:.\\s]|\\*\\*Question)",  # **Q: markdown
    r"^(?:[-*]\\s*Q[:.\\s])",  # - Q: bullet
    r"^#+\\s*\\d+\\.\\s+",  # ## 10. (markdown numbered headers)
    r"^\\d+\\.\\s+[A-Z]",  # 10. Title (numbered sections at start of line)
]


class EnhancedContextManager:
    """
    Enhanced context manager with multi-type document support.
    
    Key improvements over basic ContextManager:
    - PRE-CHUNKING section detection: Detects sections on full text BEFORE chunking
    - Hierarchical chunking: Parent chunks (2048 chars) + child chunks (512 chars)
    - Q&A atomic chunking: Keeps Q+A pairs together for sample_qa documents
    - Rich metadata: Section, document_type, parent_id, level for filtering
    """
    
    def __init__(
        self,
        parent_size: int = 4096,
        child_size: int = 1024,
        overlap: int = 150
    ):
        """
        Initialize enhanced context manager.
        
        Args:
            parent_size: Size of parent chunks in characters (default 4096)
            child_size: Size of child chunks in characters (default 1024)
            overlap: Overlap between consecutive chunks (default 150)
        """
        self.hierarchical_chunker = HierarchicalChunker(
            parent_size=parent_size,
            child_size=child_size,
            overlap=overlap
        )
        self.documents_by_type: Dict[DocumentType, List[EnhancedChunk]] = {}
        self._enhanced_chunks: List[EnhancedChunk] = []
        self._parent_map: Dict[str, EnhancedChunk] = {}  # parent_id -> parent chunk
        self.processed_files: Dict[str, dict] = {}
        # Hash-based deduplication: content_hash -> list of chunk IDs
        self._content_hashes: Dict[str, List[str]] = {}
        self._hash_to_chunks: Dict[str, List[EnhancedChunk]] = {}
    
    async def process_file(
        self,
        filename: str,
        content_b64: str,
        document_type: DocumentType = DocumentType.CUSTOM
    ) -> List[EnhancedChunk]:
        """
        Process a file with intelligent chunking and section detection.
        
        Pipeline:
        1. Decode and parse file content
        2. Compute content hash for deduplication
        3. Detect section boundaries on FULL TEXT (before chunking)
        4. Apply document-type-specific chunking strategy
        5. Create hierarchical parent-child chunks with rich metadata
        
        Args:
            filename: Name of the file
            content_b64: Base64 encoded file content
            document_type: Type of document (defaults to CUSTOM)
            
        Returns:
            List of EnhancedChunk objects (both parents and children)
        """
        # Step 1: Decode and parse
        try:
            content = base64.b64decode(content_b64)
        except Exception as e:
            logger.error(f"Failed to decode base64 content for {filename}: {e}")
            raise ValueError(f"Invalid base64 content for {filename}")
        
        # Step 2: Compute content hash for deduplication
        content_hash = hashlib.sha256(content).hexdigest()
        
        # Check if this exact content was already processed
        if content_hash in self._content_hashes:
            existing_chunks = self._hash_to_chunks.get(content_hash, [])
            logger.info(
                f"Skipping duplicate content for {filename} (hash={content_hash[:12]}..., "
                f"{len(existing_chunks)} chunks already exist)"
            )
            return existing_chunks
        
        parser = get_parser_for_file(filename)
        text = parser.parse(content, filename)
        
        if not text or not text.strip():
            logger.warning(f"No text extracted from {filename}")
            return []
        
        logger.info(f"Processing {filename} as {document_type.value} ({len(text)} chars)")
        
        # Step 3: Pre-chunking section detection on FULL TEXT
        section_map = self._detect_all_sections(text, document_type)
        
        # Step 4: Apply document-type-specific chunking
        if document_type == DocumentType.SAMPLE_QA:
            enhanced_chunks = self._chunk_qa_document(text, document_type, filename, section_map)
        else:
            enhanced_chunks = self._chunk_hierarchical(text, document_type, filename, section_map)
        
        # Step 5: Store chunks
        if document_type not in self.documents_by_type:
            self.documents_by_type[document_type] = []
        self.documents_by_type[document_type].extend(enhanced_chunks)
        self._enhanced_chunks.extend(enhanced_chunks)
        
        # Build parent map for quick lookup
        for chunk in enhanced_chunks:
            if chunk.level == "parent":
                self._parent_map[chunk.id] = chunk
        
        # Store content hash for deduplication
        self._content_hashes[content_hash] = [c.id for c in enhanced_chunks]
        self._hash_to_chunks[content_hash] = enhanced_chunks
        
        self.processed_files[filename] = {
            "id": str(uuid.uuid4()),
            "document_type": document_type.value,
            "chunk_count": len(enhanced_chunks),
            "parent_count": sum(1 for c in enhanced_chunks if c.level == "parent"),
            "child_count": sum(1 for c in enhanced_chunks if c.level == "child"),
            "content_hash": content_hash,
        }
        
        logger.info(
            f"Processed {filename}: {len(enhanced_chunks)} chunks "
            f"({self.processed_files[filename]['parent_count']} parents, "
            f"{self.processed_files[filename]['child_count']} children)"
        )
        
        return enhanced_chunks
    
    def _detect_all_sections(
        self,
        text: str,
        document_type: DocumentType
    ) -> Dict[int, str]:
        """
        Detect all section boundaries in the full text BEFORE chunking.
        
        This is the key improvement: we scan the entire document to find
        section headers, then each chunk inherits the section of its position.
        
        Args:
            text: Full document text
            document_type: Document type for pattern selection
            
        Returns:
            Dict mapping character position -> section name
        """
        patterns = SECTION_PATTERNS.get(document_type, {})
        section_positions: List[Tuple[int, str]] = []
        
        # Scan each line for section headers
        lines = text.split('\n')
        char_pos = 0
        
        for line in lines:
            line_stripped = line.strip()
            
            # Check each section pattern
            for section_name, pattern in patterns.items():
                if re.search(pattern, line_stripped):
                    section_positions.append((char_pos, section_name))
                    break  # Only one section per line
            
            char_pos += len(line) + 1  # +1 for newline
        
        # Convert to position -> section map
        # Each position maps to the most recent section header
        section_map: Dict[int, str] = {}
        
        if not section_positions:
            # No sections found, everything is "unknown"
            section_map[0] = "unknown"
        else:
            # First section starts at position 0 as "unknown" until first header
            if section_positions[0][0] > 0:
                section_map[0] = "unknown"
            
            for pos, section in section_positions:
                section_map[pos] = section
        
        return section_map
    
    def _get_section_for_position(
        self,
        position: int,
        section_map: Dict[int, str]
    ) -> str:
        """
        Get the section name for a given character position.
        
        Args:
            position: Character position in document
            section_map: Map of position -> section from _detect_all_sections
            
        Returns:
            Section name for this position
        """
        # Find the most recent section header before this position
        current_section = "unknown"
        
        for pos in sorted(section_map.keys()):
            if pos <= position:
                current_section = section_map[pos]
            else:
                break
        
        return current_section
    
    def _chunk_hierarchical(
        self,
        text: str,
        document_type: DocumentType,
        filename: str,
        section_map: Dict[int, str]
    ) -> List[EnhancedChunk]:
        """
        Create hierarchical parent-child chunks with section inheritance.
        
        Args:
            text: Full document text
            document_type: Document type
            filename: Source filename
            section_map: Pre-detected section positions
            
        Returns:
            List of EnhancedChunk objects
        """
        # Use hierarchical chunker
        hierarchical_chunks = self.hierarchical_chunker.chunk_text(
            text,
            metadata={"source": filename, "document_type": document_type.value}
        )
        
        enhanced_chunks = []
        
        for h_chunk in hierarchical_chunks:
            # Determine section based on chunk's starting position
            section = self._get_section_for_position(h_chunk.start_char, section_map)
            
            # Extract relevance tags
            relevance_tags = self._extract_relevance_tags(h_chunk.text)
            
            # Extract metadata enrichments (companies, dates, roles)
            enrichments = self._extract_metadata_enrichments(h_chunk.text)
            
            # Build rich metadata
            metadata = dict(h_chunk.metadata)
            metadata["document_type"] = document_type.value
            metadata["section"] = section
            metadata["level"] = h_chunk.level
            if h_chunk.parent_id:
                metadata["parent_id"] = h_chunk.parent_id
            
            # Add enrichments to metadata
            if enrichments["companies"]:
                metadata["companies"] = enrichments["companies"]
            if enrichments["date_ranges"]:
                metadata["date_ranges"] = enrichments["date_ranges"]
            if enrichments["roles"]:
                metadata["roles"] = enrichments["roles"]
            
            enhanced = EnhancedChunk(
                id=h_chunk.id,
                text=h_chunk.text,
                document_type=document_type,
                section=section,
                relevance_tags=relevance_tags,
                parent_chunk_id=h_chunk.parent_id,
                level=h_chunk.level,
                start_char=h_chunk.start_char,
                end_char=h_chunk.end_char,
                metadata=metadata
            )
            enhanced_chunks.append(enhanced)
        
        return enhanced_chunks
    
    def _chunk_qa_document(
        self,
        text: str,
        document_type: DocumentType,
        filename: str,
        section_map: Dict[int, str]
    ) -> List[EnhancedChunk]:
        """
        Chunk Q&A documents by keeping question-answer pairs together.
        
        This is critical for interview prep documents where Q+A should
        never be split across chunks.
        
        Args:
            text: Full document text
            document_type: Document type (should be SAMPLE_QA)
            filename: Source filename
            section_map: Pre-detected section positions
            
        Returns:
            List of EnhancedChunk objects (each containing one Q&A pair)
        """
        qa_pairs = self._split_into_qa_pairs(text)
        enhanced_chunks = []
        char_pos = 0
        
        for i, qa_text in enumerate(qa_pairs):
            if not qa_text.strip():
                char_pos += len(qa_text)
                continue
            
            section = self._get_section_for_position(char_pos, section_map)
            relevance_tags = self._extract_relevance_tags(qa_text)
            
            # Extract metadata enrichments
            enrichments = self._extract_metadata_enrichments(qa_text)
            
            # Each Q&A pair is its own "parent" - no children needed
            # because we want to retrieve the full Q&A together
            chunk_id = str(uuid.uuid4())
            
            metadata = {
                "source": filename,
                "document_type": document_type.value,
                "section": section,
                "level": "parent",  # Q&A pairs are atomic, treated as parents
                "qa_index": i,
            }
            
            # Add enrichments to metadata
            if enrichments["companies"]:
                metadata["companies"] = enrichments["companies"]
            if enrichments["date_ranges"]:
                metadata["date_ranges"] = enrichments["date_ranges"]
            if enrichments["roles"]:
                metadata["roles"] = enrichments["roles"]
            
            enhanced = EnhancedChunk(
                id=chunk_id,
                text=qa_text.strip(),
                document_type=document_type,
                section=section,
                relevance_tags=relevance_tags,
                parent_chunk_id=None,
                level="parent",
                start_char=char_pos,
                end_char=char_pos + len(qa_text),
                metadata=metadata
            )
            enhanced_chunks.append(enhanced)
            char_pos += len(qa_text)
        
        logger.info(f"Split Q&A document into {len(enhanced_chunks)} atomic Q&A pairs")
        return enhanced_chunks
    
    def _split_into_qa_pairs(self, text: str) -> List[str]:
        """
        Split text into Q&A pairs, keeping each question with its answer.
        
        Handles various formats:
        - Q: ... A: ...
        - Question 1: ... Answer: ...
        - **Q1:** ... (markdown)
        - Numbered questions followed by answers
        - ## 10. Question Title (markdown headers)
        - ### Subsections within questions
        
        Args:
            text: Full Q&A document text
            
        Returns:
            List of Q&A pair strings
        """
        # Combined pattern to detect question starts (handles leading whitespace)
        # Match: newline/start + optional whitespace + Q marker OR markdown numbered header
        question_pattern = r"(?:^|\n)\s*(?:Q\d*[:.\\s]|Question\s*\d*[:.\\s]|\*\*Q\d*[:.\\s]|[-*]\s*Q[:.\\s]|\d+\.\s*(?:Q[:.\\s])?|#{1,3}\s*\d+\.\s+)"
        
        # Find all question positions
        matches = list(re.finditer(question_pattern, text, re.IGNORECASE | re.MULTILINE))
        
        if not matches:
            # No Q&A pattern found, fall back to paragraph splitting
            paragraphs = text.split('\n\n')
            return [p for p in paragraphs if p.strip()]
        
        # Split at question boundaries
        qa_pairs = []
        for i, match in enumerate(matches):
            start = match.start()
            # If match starts with newline, skip it
            if text[start] == '\n':
                start += 1
            
            # End is either next question or end of text
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(text)
            
            qa_text = text[start:end].strip()
            if qa_text:
                qa_pairs.append(qa_text)
        
        return qa_pairs
    
    def _extract_relevance_tags(self, text: str) -> List[str]:
        """
        Extract relevance tags (keywords) from text.
        
        Includes technology keywords, soft skills, and common interview terms.
        
        Args:
            text: The chunk text
            
        Returns:
            List of relevance tags
        """
        # Technology patterns
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|Rust|Go|Java|C\+\+|C#|Ruby|PHP|Scala|Kotlin)\b',
            r'\b(React|Vue|Angular|Next\.?js|Node\.?js|Django|Flask|FastAPI|Spring|Rails)\b',
            r'\b(AWS|GCP|Azure|Docker|Kubernetes|K8s|Terraform|Jenkins|CI/CD)\b',
            r'\b(SQL|PostgreSQL|MySQL|MongoDB|Redis|DynamoDB|Elasticsearch|Cassandra)\b',
            r'\b(API|REST|GraphQL|gRPC|WebSocket|HTTP|Microservices)\b',
            r'\b(Machine Learning|ML|AI|NLP|Deep Learning|TensorFlow|PyTorch|LLM)\b',
            r'\b(Agile|Scrum|Kanban|DevOps|SRE|TDD|CI/CD)\b',
        ]
        
        # Soft skill patterns
        soft_skill_patterns = [
            r'\b(leadership|teamwork|collaboration|communication)\b',
            r'\b(problem.solving|critical.thinking|analytical)\b',
            r'\b(mentoring|coaching|training)\b',
        ]
        
        tags = set()
        
        for pattern in tech_patterns + soft_skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                tags.add(match.lower().replace(' ', '_'))
        
        return list(tags)
    
    def _extract_metadata_enrichments(self, text: str) -> Dict[str, Any]:
        """
        Extract enriched metadata from text.
        
        Extracts:
        - Company names (from employment contexts)
        - Date ranges (employment periods)
        - Role/title mentions
        
        Args:
            text: The chunk text
            
        Returns:
            Dict with extracted metadata (companies, date_ranges, roles)
        """
        enrichments: Dict[str, Any] = {
            "companies": [],
            "date_ranges": [],
            "roles": [],
        }
        
        # Company name patterns - extract from document context only
        # No hardcoded list - trust the user's uploaded documents
        company_patterns = [
            # "Company Inc.", "Company Corp", "Company LLC" - formal suffixes
            r'(?<![a-zA-Z])([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\s+(?:Inc\.?|Corp\.?|Corporation|LLC|Ltd\.?|Limited|Co\.)\b',
            # Title-cased multi-word names before common contexts (at X, joined X)
            r'(?:at|joined|left|from)\s+([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)?)\b(?=\s+(?:as|for|from|in|where|during|\d|,|\.))',
        ]
        
        companies = set()
        for pattern in company_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                company = match.strip().strip('.,')
                # Filter out common false positives
                false_positives = {
                    'the', 'a', 'an', 'and', 'or', 'in', 'at', 'to', 'for', 
                    'i', 'we', 'my', 'our', 'this', 'that', 'it', 'is', 'was',
                    'january', 'february', 'march', 'april', 'may', 'june',
                    'july', 'august', 'september', 'october', 'november', 'december',
                }
                if company.lower() not in false_positives:
                    # Remove any leading common words that may have been captured
                    for prefix in ['at ', 'and ', 'the ', 'or ']:
                        if company.lower().startswith(prefix):
                            company = company[len(prefix):]
                    if 2 <= len(company) <= 40 and len(company) > 0 and company[0].isupper():
                        companies.add(company)
        
        enrichments["companies"] = list(companies)
        
        # Date range patterns (employment periods) - supports years through 2029
        date_patterns = [
            # "2024 - 2026", "2025-Present", "2023 to 2026"
            r'\b(20[1-2]\d)\s*[-–—to]+\s*(20[1-2]\d|Present|Current|Now)\b',
            # "Jan 2024 - Mar 2026", "January 2025 - Present"
            r'\b((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20[1-2]\d)\s*[-–—to]+\s*((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20[1-2]\d|Present|Current|Now)\b',
            # "Since 2024", "From 2023"
            r'\b(?:Since|From)\s+(20[1-2]\d)\b',
        ]
        
        date_ranges = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    date_ranges.append(f"{match[0]} - {match[1]}" if len(match) > 1 else match[0])
                else:
                    date_ranges.append(match)
        
        enrichments["date_ranges"] = list(set(date_ranges))
        
        # Role/title patterns - capture full title as single group
        role_patterns = [
            # Common engineering titles (full capture)
            r'\b((?:Senior|Staff|Principal|Lead|Junior|Associate|Director|VP|Head|Chief)\s+(?:Software|Backend|Frontend|Full[- ]?Stack|ML|Data|Platform|DevOps|SRE|Cloud|Security|Mobile|iOS|Android)\s+(?:Engineer|Developer|Architect|Manager|Scientist))\b',
            # Engineering titles without level prefix
            r'\b((?:Software|Backend|Frontend|Full[- ]?Stack|ML|Data|Platform|DevOps|SRE|Cloud|Security|Mobile|iOS|Android)\s+(?:Engineer|Developer|Architect|Manager|Scientist))\b',
            # Other common titles with level prefix
            r'\b((?:Senior|Staff|Principal|Lead|Junior|Associate|Director|VP|Head|Chief)\s+(?:Product|Program|Project|Engineering|Technical)\s+(?:Manager|Lead|Director|Owner))\b',
            # Other common titles without level prefix  
            r'\b((?:Product|Program|Project|Engineering|Technical)\s+(?:Manager|Lead|Director|Owner))\b',
            # CxO titles
            r'\b(CEO|CTO|CFO|COO|CPO|CIO|CISO|VP\s+of\s+Engineering|Director\s+of\s+Engineering)\b',
        ]
        
        roles = set()
        for pattern in role_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                role = match.strip() if isinstance(match, str) else match
                if role and len(role) >= 3:
                    roles.add(role)
        
        enrichments["roles"] = list(roles)
        
        return enrichments
    
    def get_parent_chunk(self, parent_id: str) -> Optional[EnhancedChunk]:
        """
        Get a parent chunk by ID for context expansion.
        
        Args:
            parent_id: ID of the parent chunk
            
        Returns:
            Parent chunk or None if not found
        """
        return self._parent_map.get(parent_id)
    
    def get_chunks_by_type(self, doc_type: DocumentType) -> List[EnhancedChunk]:
        """
        Get all chunks of a specific document type.
        
        Args:
            doc_type: The document type to filter by
            
        Returns:
            List of chunks matching the type, empty list if none
        """
        return self.documents_by_type.get(doc_type, [])
    
    def get_child_chunks(self) -> List[EnhancedChunk]:
        """Get only child chunks (for retrieval)."""
        return [c for c in self._enhanced_chunks if c.level == "child"]
    
    def get_parent_chunks(self) -> List[EnhancedChunk]:
        """Get only parent chunks (for context)."""
        return [c for c in self._enhanced_chunks if c.level == "parent"]
    
    def get_all_enhanced_chunks(self) -> List[EnhancedChunk]:
        """
        Get all enhanced chunks across all document types.
        
        Returns:
            List of all EnhancedChunk objects
        """
        return self._enhanced_chunks.copy()
    
    def get_all_chunks(self) -> List[EnhancedChunk]:
        """Alias for get_all_enhanced_chunks for backward compatibility."""
        return self.get_all_enhanced_chunks()
    
    def clear_context(self) -> None:
        """Clear all context including enhanced chunks."""
        self.documents_by_type.clear()
        self._enhanced_chunks.clear()
        self._parent_map.clear()
        self.processed_files.clear()
        self._content_hashes.clear()
        self._hash_to_chunks.clear()
        logger.info("Enhanced context cleared")
