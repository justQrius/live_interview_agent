# STORY-042: Enhanced Context Manager - Multi-Type

**Phase**: 3B (Enhanced Context)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: None

## Description

Enhance the ContextManager to support multiple document types with rich metadata. Documents are tagged by type (resume, job_description, company_info, etc.) which enables intelligent retrieval later.

## Acceptance Criteria

- [ ] Create `EnhancedContextManager` extending existing ContextManager
- [ ] Define `DocumentType` enum with 6 types
- [ ] Store document type metadata with each chunk
- [ ] Track documents by type for selective retrieval
- [ ] Support getting chunks filtered by document type
- [ ] Backward compatible with existing upload flow
- [ ] Unit tests for all document types

## Technical Details

### File Location
```
sidecar/src/context/
├── __init__.py
├── manager.py           # Existing
├── enhanced_manager.py  # New
├── chunker.py           # Existing
└── parsers.py           # Existing
```

### Document Types

```python
from enum import Enum

class DocumentType(Enum):
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INDUSTRY_RESEARCH = "industry_research"
    SAMPLE_QA = "sample_qa"
    CUSTOM = "custom"
```

### Enhanced Chunk

```python
@dataclass
class EnhancedChunk:
    id: str
    text: str
    document_type: DocumentType
    section: str  # auto-detected: "experience", "skills", "requirements"
    relevance_tags: List[str]  # extracted keywords
    parent_chunk_id: Optional[str]
    start_char: int
    end_char: int
    metadata: Dict[str, Any]
```

### Enhanced Context Manager

```python
class EnhancedContextManager(ContextManager):
    def __init__(self):
        super().__init__()
        self.documents_by_type: Dict[DocumentType, List[EnhancedChunk]] = {}
    
    async def process_file(
        self, 
        filename: str, 
        content_b64: str,
        document_type: DocumentType = DocumentType.CUSTOM
    ) -> List[EnhancedChunk]:
        """Process file with document type tagging."""
        # Call parent for parsing
        # Add document type to metadata
        # Store in type-indexed dictionary
    
    def get_chunks_by_type(
        self, 
        doc_type: DocumentType
    ) -> List[EnhancedChunk]:
        """Get all chunks of a specific document type."""
        return self.documents_by_type.get(doc_type, [])
    
    def get_all_enhanced_chunks(self) -> List[EnhancedChunk]:
        """Get all chunks across all document types."""
```

### Section Detection (Basic)

```python
SECTION_PATTERNS = {
    DocumentType.RESUME: {
        "experience": r"(experience|work history|employment)",
        "education": r"(education|academic|degree|university)",
        "skills": r"(skills|technologies|competencies)",
        "summary": r"(summary|objective|profile)",
    },
    DocumentType.JOB_DESCRIPTION: {
        "requirements": r"(requirements|qualifications|must have)",
        "responsibilities": r"(responsibilities|duties|role)",
        "benefits": r"(benefits|perks|compensation)",
        "about": r"(about us|company|who we are)",
    }
}
```

## Test Cases

1. **Resume processing**: Upload resume, verify chunks tagged as RESUME
2. **JD processing**: Upload job description, verify JD type
3. **Type filtering**: Get only resume chunks
4. **Section detection**: Verify sections detected for resume
5. **Multiple documents**: Upload 3 documents, verify type isolation
6. **Custom type**: Upload unknown format, defaults to CUSTOM

## Definition of Done

- [ ] EnhancedContextManager implemented
- [ ] All 6 document types supported
- [ ] Section detection working
- [ ] Unit tests passing
- [ ] Integration with existing upload flow
