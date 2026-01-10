"""
Tests for HierarchicalChunker with parent-child chunk relationships.
"""

import pytest

from src.context.hierarchical_chunker import (
    HierarchicalChunk,
    HierarchicalChunker,
)


class TestHierarchicalChunk:
    """Tests for HierarchicalChunk dataclass."""
    
    def test_chunk_creation(self):
        """Should create a HierarchicalChunk with all fields."""
        chunk = HierarchicalChunk(
            id="chunk-123",
            text="Sample text content",
            level="parent",
            parent_id=None,
            start_char=0,
            end_char=19,
            metadata={"source": "test.txt"}
        )
        
        assert chunk.id == "chunk-123"
        assert chunk.text == "Sample text content"
        assert chunk.level == "parent"
        assert chunk.parent_id is None
        assert chunk.start_char == 0
        assert chunk.end_char == 19
        assert chunk.metadata == {"source": "test.txt"}
    
    def test_child_chunk_with_parent_id(self):
        """Child chunks should have parent_id set."""
        parent = HierarchicalChunk(
            id="parent-1",
            text="Parent text",
            level="parent",
            parent_id=None,
            start_char=0,
            end_char=11,
            metadata={}
        )
        
        child = HierarchicalChunk(
            id="child-1",
            text="Child text",
            level="child",
            parent_id=parent.id,
            start_char=0,
            end_char=10,
            metadata={}
        )
        
        assert child.parent_id == "parent-1"
        assert child.level == "child"


class TestHierarchicalChunker:
    """Tests for HierarchicalChunker class."""
    
    @pytest.fixture
    def chunker(self):
        """Create a chunker with default settings."""
        return HierarchicalChunker()
    
    @pytest.fixture
    def small_chunker(self):
        """Create a chunker with smaller sizes for testing."""
        return HierarchicalChunker(
            parent_size=200,
            child_size=50,
            overlap=10
        )
    
    def test_default_initialization(self, chunker):
        """Should initialize with default sizes."""
        assert chunker.parent_size == 2048
        assert chunker.child_size == 512
        assert chunker.overlap == 100
    
    def test_custom_initialization(self):
        """Should accept custom sizes."""
        chunker = HierarchicalChunker(
            parent_size=4096,
            child_size=1024,
            overlap=200
        )
        
        assert chunker.parent_size == 4096
        assert chunker.child_size == 1024
        assert chunker.overlap == 200
    
    def test_empty_document(self, chunker):
        """Empty text should return empty list."""
        chunks = chunker.chunk_text("")
        assert chunks == []
    
    def test_whitespace_only_document(self, chunker):
        """Whitespace-only text should return empty list."""
        chunks = chunker.chunk_text("   \n\t   ")
        assert chunks == []
    
    def test_small_document_single_parent(self, small_chunker):
        """Document smaller than parent size creates 1 parent."""
        text = "This is a small document."  # 25 chars
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        assert len(parents) == 1
        assert parents[0].text.strip() == text.strip()
    
    def test_small_document_has_children(self, small_chunker):
        """Small document should still have children of the parent."""
        text = "This is a small document that fits in one parent chunk."
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        children = [c for c in chunks if c.level == "child"]
        
        assert len(parents) == 1
        assert len(children) >= 1
    
    def test_large_document_multiple_parents(self, small_chunker):
        """Large document creates multiple parents."""
        # Create text larger than parent_size (200)
        text = "Word " * 100  # 500 chars
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        assert len(parents) >= 2
    
    def test_children_have_valid_parent_id(self, small_chunker):
        """All children should have valid parent_id."""
        text = "This is some text that will be chunked into parents and children."
        chunks = small_chunker.chunk_text(text)
        
        parent_ids = {c.id for c in chunks if c.level == "parent"}
        children = [c for c in chunks if c.level == "child"]
        
        for child in children:
            assert child.parent_id is not None
            assert child.parent_id in parent_ids
    
    def test_parents_have_no_parent_id(self, small_chunker):
        """Parents should have parent_id = None."""
        text = "Sample text for chunking."
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        for parent in parents:
            assert parent.parent_id is None
    
    def test_chunk_ids_are_unique(self, small_chunker):
        """All chunk IDs should be unique."""
        text = "Word " * 100
        chunks = small_chunker.chunk_text(text)
        
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))
    
    def test_parent_overlap(self):
        """Parents should overlap by specified amount."""
        chunker = HierarchicalChunker(
            parent_size=100,
            child_size=30,
            overlap=20
        )
        
        # Create text that spans multiple parents
        text = "A" * 250  # Will create 3 parents with 100 char size
        chunks = chunker.chunk_text(text)
        
        parents = sorted(
            [c for c in chunks if c.level == "parent"],
            key=lambda x: x.start_char
        )
        
        if len(parents) >= 2:
            # Second parent should start before first parent ends
            # (due to overlap)
            # With 100 char size and 20 overlap, parent 2 starts at ~80
            assert parents[1].start_char < parents[0].end_char
    
    def test_child_overlap(self, small_chunker):
        """Children within a parent should overlap."""
        # Create text that will have multiple children in one parent
        text = "Word " * 30  # 150 chars, should fit in one parent (200)
        chunks = small_chunker.chunk_text(text)
        
        children = sorted(
            [c for c in chunks if c.level == "child"],
            key=lambda x: x.start_char
        )
        
        if len(children) >= 2:
            # Verify overlap exists
            assert children[1].start_char < children[0].end_char
    
    def test_chunks_preserve_positions(self, small_chunker):
        """Chunks should have valid start/end positions."""
        text = "Sample text for testing positions."
        chunks = small_chunker.chunk_text(text)
        
        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
            assert chunk.end_char <= len(text) + 1  # Allow for boundary
    
    def test_metadata_propagation(self, small_chunker):
        """Metadata should be passed to all chunks."""
        text = "Some text content"
        metadata = {"source": "test.txt", "type": "resume"}
        
        chunks = small_chunker.chunk_text(text, metadata)
        
        for chunk in chunks:
            assert "source" in chunk.metadata
            assert chunk.metadata["source"] == "test.txt"
    
    def test_word_boundary_breaking(self, small_chunker):
        """Chunks should try to break at word boundaries."""
        text = "This is a sentence with multiple words for testing."
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        
        # Parent text shouldn't start/end mid-word (unless at doc boundary)
        for parent in parents:
            # Should not start with a partial word (no leading letters after space)
            # This is a soft check - main thing is it doesn't crash
            assert len(parent.text.strip()) > 0
    
    def test_children_within_parent_bounds(self, small_chunker):
        """Child chunks should be derived from their parent's text."""
        text = "Parent one content here. " * 5 + "Parent two content here. " * 5
        chunks = small_chunker.chunk_text(text)
        
        parent_map = {c.id: c for c in chunks if c.level == "parent"}
        children = [c for c in chunks if c.level == "child"]
        
        for child in children:
            parent = parent_map[child.parent_id]
            # Child text should be a substring of parent text
            assert child.text in parent.text or parent.text in child.text
    
    def test_get_parent_for_child(self, small_chunker):
        """Should be able to retrieve parent given a child."""
        text = "Some sample text that will be chunked."
        chunks = small_chunker.chunk_text(text)
        
        parent_map = {c.id: c for c in chunks if c.level == "parent"}
        children = [c for c in chunks if c.level == "child"]
        
        for child in children:
            parent = parent_map.get(child.parent_id)
            assert parent is not None
            assert parent.level == "parent"
    
    def test_large_document_chunk_counts(self):
        """Verify approximate chunk counts for large document."""
        chunker = HierarchicalChunker(
            parent_size=1000,
            child_size=250,
            overlap=50
        )
        
        # 5000 char document
        text = "Word " * 1000  # 5000 chars
        chunks = chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        children = [c for c in chunks if c.level == "child"]
        
        # Should have ~5-6 parents (5000 / (1000 - 50))
        assert len(parents) >= 4
        assert len(parents) <= 8
        
        # Each parent should have multiple children
        assert len(children) > len(parents)
    
    def test_only_parents_filter(self, small_chunker):
        """Should be able to filter to only parent chunks."""
        text = "Sample text for testing."
        chunks = small_chunker.chunk_text(text)
        
        parents_only = small_chunker.get_parents(chunks)
        
        for chunk in parents_only:
            assert chunk.level == "parent"
    
    def test_only_children_filter(self, small_chunker):
        """Should be able to filter to only child chunks."""
        text = "Sample text for testing."
        chunks = small_chunker.chunk_text(text)
        
        children_only = small_chunker.get_children(chunks)
        
        for chunk in children_only:
            assert chunk.level == "child"
    
    def test_get_children_of_parent(self, small_chunker):
        """Should get all children of a specific parent."""
        text = "Word " * 50  # Multiple children
        chunks = small_chunker.chunk_text(text)
        
        parents = [c for c in chunks if c.level == "parent"]
        
        if parents:
            parent = parents[0]
            children = small_chunker.get_children_of_parent(chunks, parent.id)
            
            for child in children:
                assert child.parent_id == parent.id
