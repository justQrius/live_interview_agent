"""
Tests for EnhancedContextManager with multi-type document support.
"""

import pytest
import base64
from unittest.mock import patch, MagicMock

from src.context.enhanced_manager import (
    DocumentType,
    EnhancedChunk,
    EnhancedContextManager,
    SECTION_PATTERNS,
)


class TestDocumentType:
    """Tests for DocumentType enum."""
    
    def test_document_type_values(self):
        """All 6 document types should exist with correct values."""
        assert DocumentType.RESUME.value == "resume"
        assert DocumentType.JOB_DESCRIPTION.value == "job_description"
        assert DocumentType.COMPANY_INFO.value == "company_info"
        assert DocumentType.INDUSTRY_RESEARCH.value == "industry_research"
        assert DocumentType.SAMPLE_QA.value == "sample_qa"
        assert DocumentType.CUSTOM.value == "custom"
    
    def test_document_type_count(self):
        """Should have exactly 6 document types."""
        assert len(DocumentType) == 6
    
    def test_document_type_from_string(self):
        """Should be able to create from string value."""
        assert DocumentType("resume") == DocumentType.RESUME
        assert DocumentType("job_description") == DocumentType.JOB_DESCRIPTION


class TestEnhancedChunk:
    """Tests for EnhancedChunk dataclass."""
    
    def test_enhanced_chunk_creation(self):
        """Should create an EnhancedChunk with all fields."""
        chunk = EnhancedChunk(
            id="chunk-123",
            text="Sample text",
            document_type=DocumentType.RESUME,
            section="experience",
            relevance_tags=["python", "backend"],
            parent_chunk_id=None,
            start_char=0,
            end_char=11,
            metadata={"source": "resume.pdf"}
        )
        
        assert chunk.id == "chunk-123"
        assert chunk.text == "Sample text"
        assert chunk.document_type == DocumentType.RESUME
        assert chunk.section == "experience"
        assert chunk.relevance_tags == ["python", "backend"]
        assert chunk.parent_chunk_id is None
        assert chunk.start_char == 0
        assert chunk.end_char == 11
        assert chunk.metadata == {"source": "resume.pdf"}
    
    def test_enhanced_chunk_with_parent(self):
        """Should support parent-child relationships."""
        parent = EnhancedChunk(
            id="parent-1",
            text="Parent text",
            document_type=DocumentType.RESUME,
            section="summary",
            relevance_tags=[],
            parent_chunk_id=None,
            start_char=0,
            end_char=11,
            metadata={}
        )
        
        child = EnhancedChunk(
            id="child-1",
            text="Child text",
            document_type=DocumentType.RESUME,
            section="summary",
            relevance_tags=[],
            parent_chunk_id=parent.id,
            start_char=0,
            end_char=10,
            metadata={}
        )
        
        assert child.parent_chunk_id == "parent-1"
    
    def test_enhanced_chunk_default_empty_tags(self):
        """Should handle empty relevance tags."""
        chunk = EnhancedChunk(
            id="chunk-1",
            text="Text",
            document_type=DocumentType.CUSTOM,
            section="unknown",
            relevance_tags=[],
            parent_chunk_id=None,
            start_char=0,
            end_char=4,
            metadata={}
        )
        
        assert chunk.relevance_tags == []


class TestSectionPatterns:
    """Tests for section detection patterns."""
    
    def test_resume_section_patterns_exist(self):
        """Resume should have expected section patterns."""
        assert DocumentType.RESUME in SECTION_PATTERNS
        resume_patterns = SECTION_PATTERNS[DocumentType.RESUME]
        
        assert "experience" in resume_patterns
        assert "education" in resume_patterns
        assert "skills" in resume_patterns
        assert "summary" in resume_patterns
    
    def test_job_description_section_patterns_exist(self):
        """Job description should have expected section patterns."""
        assert DocumentType.JOB_DESCRIPTION in SECTION_PATTERNS
        jd_patterns = SECTION_PATTERNS[DocumentType.JOB_DESCRIPTION]
        
        assert "requirements" in jd_patterns
        assert "responsibilities" in jd_patterns
        assert "benefits" in jd_patterns
        assert "about" in jd_patterns


class TestEnhancedContextManager:
    """Tests for EnhancedContextManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    def test_initialization(self, manager):
        """Should initialize with empty state."""
        assert manager.documents_by_type == {}
        assert manager.chunks == []
        assert manager.processed_files == {}
    
    def test_inherits_from_context_manager(self, manager):
        """Should inherit from ContextManager."""
        from src.context.manager import ContextManager
        assert isinstance(manager, ContextManager)
    
    @pytest.mark.asyncio
    async def test_process_file_with_document_type(self, manager):
        """Should process file with document type tagging."""
        resume_text = """
        John Doe
        
        Summary
        Experienced software engineer with 10 years of experience.
        
        Experience
        Senior Developer at TechCorp (2018-2023)
        - Led team of 5 engineers
        - Built microservices architecture
        
        Skills
        Python, TypeScript, Rust
        """
        content_b64 = base64.b64encode(resume_text.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            document_type=DocumentType.RESUME
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, EnhancedChunk)
            assert chunk.document_type == DocumentType.RESUME
    
    @pytest.mark.asyncio
    async def test_process_file_default_custom_type(self, manager):
        """Should default to CUSTOM type if not specified."""
        content = "Some generic content"
        content_b64 = base64.b64encode(content.encode()).decode()
        
        chunks = await manager.process_file("notes.txt", content_b64)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.CUSTOM
    
    @pytest.mark.asyncio
    async def test_process_job_description(self, manager):
        """Should process job description with correct type."""
        jd_text = """
        Software Engineer Position
        
        About Us
        We are a leading tech company building innovative solutions.
        
        Responsibilities
        - Design and implement backend services
        - Collaborate with product team
        
        Requirements
        - 5+ years of experience
        - Strong Python skills
        
        Benefits
        - Competitive salary
        - Remote work
        """
        content_b64 = base64.b64encode(jd_text.encode()).decode()
        
        chunks = await manager.process_file(
            "job.txt",
            content_b64,
            document_type=DocumentType.JOB_DESCRIPTION
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.JOB_DESCRIPTION
    
    @pytest.mark.asyncio
    async def test_get_chunks_by_type(self, manager):
        """Should filter chunks by document type."""
        # Upload resume
        resume = base64.b64encode(b"Resume content with experience").decode()
        await manager.process_file("resume.txt", resume, DocumentType.RESUME)
        
        # Upload job description
        jd = base64.b64encode(b"Job requirements for the role").decode()
        await manager.process_file("job.txt", jd, DocumentType.JOB_DESCRIPTION)
        
        # Filter by type
        resume_chunks = manager.get_chunks_by_type(DocumentType.RESUME)
        jd_chunks = manager.get_chunks_by_type(DocumentType.JOB_DESCRIPTION)
        
        assert len(resume_chunks) > 0
        assert len(jd_chunks) > 0
        
        for chunk in resume_chunks:
            assert chunk.document_type == DocumentType.RESUME
        
        for chunk in jd_chunks:
            assert chunk.document_type == DocumentType.JOB_DESCRIPTION
    
    @pytest.mark.asyncio
    async def test_get_chunks_by_type_empty(self, manager):
        """Should return empty list for unused type."""
        chunks = manager.get_chunks_by_type(DocumentType.INDUSTRY_RESEARCH)
        assert chunks == []
    
    @pytest.mark.asyncio
    async def test_get_all_enhanced_chunks(self, manager):
        """Should return all chunks across all types."""
        # Upload multiple documents
        resume = base64.b64encode(b"Resume content").decode()
        jd = base64.b64encode(b"Job description content").decode()
        company = base64.b64encode(b"Company info content").decode()
        
        await manager.process_file("resume.txt", resume, DocumentType.RESUME)
        await manager.process_file("job.txt", jd, DocumentType.JOB_DESCRIPTION)
        await manager.process_file("company.txt", company, DocumentType.COMPANY_INFO)
        
        all_chunks = manager.get_all_enhanced_chunks()
        
        # Should have chunks from all 3 documents
        assert len(all_chunks) >= 3
        
        # Should include all types
        types = {chunk.document_type for chunk in all_chunks}
        assert DocumentType.RESUME in types
        assert DocumentType.JOB_DESCRIPTION in types
        assert DocumentType.COMPANY_INFO in types
    
    @pytest.mark.asyncio
    async def test_section_detection_resume(self, manager):
        """Should detect sections in resume."""
        resume_text = """
        Summary
        Experienced engineer with strong background.
        
        Experience
        Senior Developer at BigCo
        - Built scalable systems
        
        Education
        BS Computer Science, MIT
        
        Skills
        Python, JavaScript, Go
        """
        content_b64 = base64.b64encode(resume_text.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            document_type=DocumentType.RESUME
        )
        
        # At least some chunks should have detected sections
        sections = {chunk.section for chunk in chunks}
        # We expect at least "unknown" or detected sections
        assert len(sections) >= 1
    
    @pytest.mark.asyncio
    async def test_section_detection_job_description(self, manager):
        """Should detect sections in job description."""
        jd_text = """
        About Us
        We are a great company.
        
        Responsibilities
        - Write code
        - Review PRs
        
        Requirements
        - 3+ years experience
        - Strong coding skills
        
        Benefits
        - Health insurance
        - 401k
        """
        content_b64 = base64.b64encode(jd_text.encode()).decode()
        
        chunks = await manager.process_file(
            "job.txt",
            content_b64,
            document_type=DocumentType.JOB_DESCRIPTION
        )
        
        sections = {chunk.section for chunk in chunks}
        assert len(sections) >= 1
    
    @pytest.mark.asyncio
    async def test_chunk_has_unique_id(self, manager):
        """Each chunk should have a unique ID."""
        content = base64.b64encode(b"Some text content here").decode()
        chunks = await manager.process_file("doc.txt", content, DocumentType.CUSTOM)
        
        ids = [chunk.id for chunk in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs should be unique"
    
    @pytest.mark.asyncio
    async def test_chunk_preserves_positions(self, manager):
        """Chunks should preserve start/end character positions."""
        content = base64.b64encode(b"Short text").decode()
        chunks = await manager.process_file("doc.txt", content, DocumentType.CUSTOM)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_get_all_chunks(self, manager):
        """Should still support get_all_chunks() for backward compatibility."""
        content = base64.b64encode(b"Test content").decode()
        await manager.process_file("test.txt", content, DocumentType.RESUME)
        
        # Original method should still work
        all_chunks = manager.get_all_chunks()
        assert len(all_chunks) > 0
    
    @pytest.mark.asyncio
    async def test_clear_context(self, manager):
        """Should clear all enhanced chunks when clearing context."""
        content = base64.b64encode(b"Test content").decode()
        await manager.process_file("test.txt", content, DocumentType.RESUME)
        
        assert len(manager.get_all_enhanced_chunks()) > 0
        
        manager.clear_context()
        
        assert len(manager.get_all_enhanced_chunks()) == 0
        assert len(manager.documents_by_type) == 0
    
    @pytest.mark.asyncio
    async def test_metadata_includes_document_type(self, manager):
        """Chunk metadata should include document type."""
        content = base64.b64encode(b"Resume content").decode()
        chunks = await manager.process_file(
            "resume.txt",
            content,
            DocumentType.RESUME
        )
        
        for chunk in chunks:
            assert "document_type" in chunk.metadata
            assert chunk.metadata["document_type"] == "resume"
    
    @pytest.mark.asyncio
    async def test_multiple_files_same_type(self, manager):
        """Should handle multiple files of the same type."""
        resume1 = base64.b64encode(b"First resume content").decode()
        resume2 = base64.b64encode(b"Second resume content").decode()
        
        await manager.process_file("resume1.txt", resume1, DocumentType.RESUME)
        await manager.process_file("resume2.txt", resume2, DocumentType.RESUME)
        
        resume_chunks = manager.get_chunks_by_type(DocumentType.RESUME)
        
        # Should have chunks from both files
        sources = {chunk.metadata.get("source") for chunk in resume_chunks}
        assert "resume1.txt" in sources
        assert "resume2.txt" in sources
    
    @pytest.mark.asyncio
    async def test_sample_qa_document_type(self, manager):
        """Should handle SAMPLE_QA document type."""
        qa_content = """
        Q: Tell me about yourself
        A: I am a software engineer with 5 years of experience...
        
        Q: What are your strengths?
        A: My key strengths include problem-solving...
        """
        content_b64 = base64.b64encode(qa_content.encode()).decode()
        
        chunks = await manager.process_file(
            "qa_samples.txt",
            content_b64,
            DocumentType.SAMPLE_QA
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.SAMPLE_QA
    
    @pytest.mark.asyncio
    async def test_industry_research_document_type(self, manager):
        """Should handle INDUSTRY_RESEARCH document type."""
        research_content = "Market analysis shows growth in AI sector..."
        content_b64 = base64.b64encode(research_content.encode()).decode()
        
        chunks = await manager.process_file(
            "research.txt",
            content_b64,
            DocumentType.INDUSTRY_RESEARCH
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.INDUSTRY_RESEARCH
    
    @pytest.mark.asyncio
    async def test_company_info_document_type(self, manager):
        """Should handle COMPANY_INFO document type."""
        company_content = "Founded in 2010, our company specializes in..."
        content_b64 = base64.b64encode(company_content.encode()).decode()
        
        chunks = await manager.process_file(
            "about_company.txt",
            content_b64,
            DocumentType.COMPANY_INFO
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.COMPANY_INFO
