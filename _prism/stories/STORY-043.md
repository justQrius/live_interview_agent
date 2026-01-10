# STORY-043: Hierarchical Chunker

**Phase**: 3B (Enhanced Context)
**Priority**: P1 - Must Have
**Effort**: 0.5 days
**Dependencies**: STORY-042

## Description

Implement hierarchical chunking that creates parent chunks (2048 chars) and child chunks (512 chars). Child chunks are used for precise retrieval, while parent chunks provide full context when returned.

## Acceptance Criteria

- [ ] Create `HierarchicalChunker` class
- [ ] Generate parent chunks (2048 chars) and child chunks (512 chars)
- [ ] Link children to parents via `parent_chunk_id`
- [ ] Configurable chunk sizes with sensible defaults
- [ ] Maintain overlap between chunks (100 chars default)
- [ ] Unit tests for hierarchical relationships

## Technical Details

### File Location
```
sidecar/src/context/
├── chunker.py              # Existing flat chunker
└── hierarchical_chunker.py # New
```

### Interface

```python
from dataclasses import dataclass
from typing import List, Optional
import uuid

@dataclass
class HierarchicalChunk:
    id: str
    text: str
    level: str  # "parent" or "child"
    parent_id: Optional[str]  # None for parents
    start_char: int
    end_char: int
    metadata: Dict[str, Any]

class HierarchicalChunker:
    def __init__(
        self,
        parent_size: int = 2048,
        child_size: int = 512,
        overlap: int = 100
    ):
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap
    
    def chunk_text(
        self, 
        text: str, 
        metadata: Dict = None
    ) -> List[HierarchicalChunk]:
        """
        Create hierarchical chunks from text.
        
        Returns both parent and child chunks.
        Children reference their parent via parent_id.
        """
        chunks = []
        
        # First pass: create parent chunks
        parents = self._create_chunks(text, self.parent_size, "parent")
        chunks.extend(parents)
        
        # Second pass: create child chunks within each parent
        for parent in parents:
            children = self._create_children(parent)
            chunks.extend(children)
        
        return chunks
    
    def _create_children(
        self, 
        parent: HierarchicalChunk
    ) -> List[HierarchicalChunk]:
        """Create child chunks from a parent chunk."""
        child_chunks = self._create_chunks(
            parent.text, 
            self.child_size, 
            "child"
        )
        for child in child_chunks:
            child.parent_id = parent.id
        return child_chunks
```

### Visualization

```
Document (10,000 chars)
│
├── Parent 1 (chars 0-2048)
│   ├── Child 1a (chars 0-512)
│   ├── Child 1b (chars 412-924)    # 100 char overlap
│   ├── Child 1c (chars 824-1336)
│   └── Child 1d (chars 1236-1748)
│
├── Parent 2 (chars 1948-3996)      # 100 char overlap with Parent 1
│   ├── Child 2a (chars 1948-2460)
│   └── ...
│
└── ...
```

## Test Cases

1. **Small document**: Document smaller than parent size → 1 parent, N children
2. **Large document**: 10K document → verify correct parent/child counts
3. **Overlap verification**: Children within parent have proper overlap
4. **Parent linkage**: All children have valid parent_id
5. **Boundary handling**: Chunks break at word boundaries
6. **Empty document**: Empty text returns empty list
7. **Configurable sizes**: Custom sizes respected

## Definition of Done

- [ ] HierarchicalChunker implemented
- [ ] Parent-child relationships correct
- [ ] Overlap working properly
- [ ] Unit tests passing
- [ ] Documentation complete
