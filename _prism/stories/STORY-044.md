# STORY-044: Metadata-Driven Vector Store

**Phase**: 3B (Enhanced Context)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: STORY-043

## Description

Enhance the VectorStore to support metadata filtering. Queries can filter by document_type, level (parent/child), and other metadata fields before vector similarity search.

## Acceptance Criteria

- [ ] Extend `VectorStore` to store rich metadata with each document
- [ ] Support metadata filtering in queries (`where` clause)
- [ ] Filter by document_type before vector search
- [ ] Filter by chunk level (parent/child)
- [ ] Verify ChromaDB version supports required features
- [ ] Unit tests for filtered queries

## Technical Details

### Enhanced Metadata Schema

```python
# Metadata stored with each chunk
{
    "document_type": "resume",           # DocumentType.value
    "level": "child",                    # "parent" or "child"
    "parent_id": "chunk_abc123",         # For child chunks
    "section": "experience",             # Detected section
    "source": "resume.pdf",              # Original filename
    "file_id": "file_xyz789",            # Unique file identifier
}
```

### Interface Extensions

```python
class VectorStore:
    def add_documents_with_metadata(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        ids: List[str] = None
    ) -> None:
        """Add documents with rich metadata."""
        # Validate metadata schema
        # Store in ChromaDB
    
    def query_with_filter(
        self,
        query: str,
        n_results: int = 5,
        where: Dict = None,
        where_document: Dict = None
    ) -> QueryResult:
        """
        Query with metadata filtering.
        
        Args:
            query: Search query text
            n_results: Number of results to return
            where: Metadata filter (e.g., {"document_type": "resume"})
            where_document: Document content filter
        
        Example:
            store.query_with_filter(
                "Python experience",
                where={"document_type": "resume", "level": "child"}
            )
        """
```

### ChromaDB Where Clause Examples

```python
# Filter by document type
where={"document_type": "resume"}

# Filter by multiple conditions (AND)
where={
    "$and": [
        {"document_type": "resume"},
        {"level": "child"}
    ]
}

# Filter by multiple document types (OR)
where={
    "document_type": {"$in": ["resume", "job_description"]}
}
```

## Test Cases

1. **Add with metadata**: Add documents, verify metadata stored
2. **Query without filter**: Normal query returns results
3. **Filter by type**: Query only resume chunks
4. **Filter by level**: Query only child chunks
5. **Combined filters**: Filter by type AND level
6. **No matches**: Filter that matches nothing returns empty
7. **Invalid metadata**: Reject documents with missing required fields

## Definition of Done

- [ ] Metadata filtering implemented
- [ ] ChromaDB compatibility verified
- [ ] Unit tests for all filter scenarios
- [ ] Performance acceptable with 1000+ chunks
- [ ] Documentation of metadata schema
