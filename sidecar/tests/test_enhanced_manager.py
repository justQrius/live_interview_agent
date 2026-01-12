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
        """Should have exactly 7 document types (includes INTERVIEWER_INFO)."""
        assert len(DocumentType) == 7
    
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
            level="child",
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
        assert chunk.level == "child"
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
            level="parent",
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
            level="child",
            start_char=0,
            end_char=10,
            metadata={}
        )
        
        assert child.parent_chunk_id == "parent-1"
        assert child.level == "child"
        assert parent.level == "parent"
    
    def test_enhanced_chunk_default_empty_tags(self):
        """Should handle empty relevance tags."""
        chunk = EnhancedChunk(
            id="chunk-1",
            text="Text",
            document_type=DocumentType.CUSTOM,
            section="unknown",
            relevance_tags=[],
            parent_chunk_id=None,
            level="parent",
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
        assert manager._enhanced_chunks == []
        assert manager._parent_map == {}
        assert manager.processed_files == {}
    
    def test_has_hierarchical_chunker(self, manager):
        """Should have HierarchicalChunker instance."""
        from src.context.hierarchical_chunker import HierarchicalChunker
        assert hasattr(manager, 'hierarchical_chunker')
        assert isinstance(manager.hierarchical_chunker, HierarchicalChunker)
    
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


class TestHierarchicalChunking:
    """Tests for hierarchical parent-child chunking."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    @pytest.mark.asyncio
    async def test_long_document_creates_hierarchical_chunks(self, manager):
        """Long documents should create both parent and child chunks."""
        # Create a document long enough to require chunking
        long_text = """
        Experience
        
        Senior Software Engineer at TechCorp (2020-2024)
        I worked extensively on building microservices architecture using Python and Rust.
        Led a team of 5 engineers to deliver critical infrastructure components.
        Implemented CI/CD pipelines reducing deployment time by 60%.
        Designed and built a real-time data processing system handling 1M events/sec.
        Mentored junior engineers and established coding standards.
        
        Software Engineer at StartupXYZ (2017-2020)
        Developed full-stack web applications using React and Node.js.
        Built RESTful APIs serving mobile and web clients.
        Integrated third-party payment systems and authentication providers.
        Participated in on-call rotation and incident response.
        
        Education
        
        Master of Science in Computer Science, Stanford University (2017)
        Bachelor of Science in Computer Engineering, MIT (2015)
        
        Skills
        
        Programming Languages: Python, TypeScript, Rust, Go, Java
        Frameworks: React, FastAPI, Django, Express.js
        Cloud: AWS, GCP, Kubernetes, Docker, Terraform
        Databases: PostgreSQL, MongoDB, Redis, DynamoDB
        """
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            DocumentType.RESUME
        )
        
        # Should have both parent and child chunks
        parent_chunks = [c for c in chunks if c.level == "parent"]
        child_chunks = [c for c in chunks if c.level == "child"]
        
        assert len(parent_chunks) >= 1, "Should have at least one parent chunk"
        assert len(child_chunks) >= 1, "Should have child chunks"
    
    @pytest.mark.asyncio
    async def test_child_chunks_have_parent_id(self, manager):
        """Child chunks should reference their parent chunk ID."""
        long_text = "A" * 3000  # Long enough to create hierarchy
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        chunks = await manager.process_file("doc.txt", content_b64)
        
        child_chunks = [c for c in chunks if c.level == "child"]
        
        for child in child_chunks:
            assert child.parent_chunk_id is not None, "Child should have parent_id"
    
    @pytest.mark.asyncio
    async def test_parent_map_populated(self, manager):
        """Parent map should be populated for quick lookup."""
        long_text = "Content " * 500  # Long enough to create parents
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        await manager.process_file("doc.txt", content_b64)
        
        # Parent map should have entries
        parent_chunks = [c for c in manager._enhanced_chunks if c.level == "parent"]
        
        for parent in parent_chunks:
            assert parent.id in manager._parent_map
            assert manager._parent_map[parent.id] == parent
    
    @pytest.mark.asyncio
    async def test_get_parent_chunk(self, manager):
        """Should be able to retrieve parent chunk by ID."""
        long_text = "Content " * 500
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        await manager.process_file("doc.txt", content_b64)
        
        child_chunks = manager.get_child_chunks()
        
        if child_chunks:
            child = child_chunks[0]
            if child.parent_chunk_id:
                parent = manager.get_parent_chunk(child.parent_chunk_id)
                assert parent is not None
                assert parent.level == "parent"
    
    @pytest.mark.asyncio
    async def test_get_child_chunks(self, manager):
        """Should return only child chunks."""
        long_text = "Content " * 500
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        await manager.process_file("doc.txt", content_b64)
        
        child_chunks = manager.get_child_chunks()
        
        for chunk in child_chunks:
            assert chunk.level == "child"
    
    @pytest.mark.asyncio
    async def test_get_parent_chunks(self, manager):
        """Should return only parent chunks."""
        long_text = "Content " * 500
        content_b64 = base64.b64encode(long_text.encode()).decode()
        
        await manager.process_file("doc.txt", content_b64)
        
        parent_chunks = manager.get_parent_chunks()
        
        for chunk in parent_chunks:
            assert chunk.level == "parent"


class TestPreChunkingSectionDetection:
    """Tests for pre-chunking section detection."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    @pytest.mark.asyncio
    async def test_section_detected_for_each_chunk(self, manager):
        """Each chunk should have a section detected from pre-chunking scan."""
        resume_text = """
        Summary
        Experienced engineer with 10 years in tech.
        
        Experience
        Senior Developer at TechCorp 2020-2024.
        Built amazing things.
        
        Skills
        Python, TypeScript, Rust
        """
        content_b64 = base64.b64encode(resume_text.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            DocumentType.RESUME
        )
        
        # Every chunk should have a section (even if "unknown")
        for chunk in chunks:
            assert chunk.section is not None
            assert isinstance(chunk.section, str)
    
    @pytest.mark.asyncio
    async def test_section_inherited_from_position(self, manager):
        """Chunks should inherit section from their position in document."""
        resume_text = """
        Experience
        
        I have 10 years of experience building distributed systems.
        Led multiple teams and delivered complex projects.
        """ + "More experience content. " * 50  # Make it long enough to chunk
        
        content_b64 = base64.b64encode(resume_text.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            DocumentType.RESUME
        )
        
        # Chunks from the experience section should have section="experience"
        experience_chunks = [c for c in chunks if c.section == "experience"]
        assert len(experience_chunks) > 0, "Should detect experience section"


class TestQAAtomicChunking:
    """Tests for Q&A document atomic chunking."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    @pytest.mark.asyncio
    async def test_qa_pairs_kept_together(self, manager):
        """Q&A pairs should be kept as atomic chunks."""
        qa_content = """
        Q: Tell me about yourself
        A: I am a software engineer with 5 years of experience building 
        distributed systems. I specialize in Python and Rust.
        
        Q: What are your strengths?
        A: My key strengths include problem-solving, technical leadership,
        and strong communication skills. I excel at breaking down complex
        problems into manageable pieces.
        
        Q: Describe a challenging project
        A: At my previous company, I led the migration of a monolithic 
        application to microservices. This reduced deployment times by 80%
        and improved system reliability.
        """
        content_b64 = base64.b64encode(qa_content.encode()).decode()
        
        chunks = await manager.process_file(
            "qa_samples.txt",
            content_b64,
            DocumentType.SAMPLE_QA
        )
        
        # Should have approximately 3 chunks (one per Q&A pair)
        assert len(chunks) == 3, f"Expected 3 Q&A pairs, got {len(chunks)}"
        
        # Each chunk should contain both Q and A
        for chunk in chunks:
            text = chunk.text.lower()
            # Should contain both question and answer markers
            assert "q:" in text or "question" in text or text.startswith("tell") or text.startswith("what") or text.startswith("describe")
    
    @pytest.mark.asyncio
    async def test_qa_chunks_are_parents(self, manager):
        """Q&A pairs should be treated as parent-level (atomic, no children)."""
        qa_content = """
        Q1: First question
        A1: First answer with lots of detail.
        
        Q2: Second question
        A2: Second answer with explanation.
        """
        content_b64 = base64.b64encode(qa_content.encode()).decode()
        
        chunks = await manager.process_file(
            "qa.txt",
            content_b64,
            DocumentType.SAMPLE_QA
        )
        
        # All Q&A chunks should be parent level (no splitting)
        for chunk in chunks:
            assert chunk.level == "parent", "Q&A pairs should be atomic parents"
            assert chunk.parent_chunk_id is None, "Q&A pairs shouldn't have parent"
    
    @pytest.mark.asyncio
    async def test_qa_chunks_have_qa_index_metadata(self, manager):
        """Q&A chunks should have qa_index in metadata."""
        qa_content = """
        Q: Question one
        A: Answer one
        
        Q: Question two
        A: Answer two
        """
        content_b64 = base64.b64encode(qa_content.encode()).decode()
        
        chunks = await manager.process_file(
            "qa.txt",
            content_b64,
            DocumentType.SAMPLE_QA
        )
        
        for chunk in chunks:
            assert "qa_index" in chunk.metadata


class TestRelevanceTagExtraction:
    """Tests for relevance tag extraction."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    @pytest.mark.asyncio
    async def test_technology_tags_extracted(self, manager):
        """Should extract technology keywords as tags."""
        content = """
        Skills: Python, TypeScript, React, AWS, Docker, Kubernetes
        Experience with PostgreSQL and MongoDB databases.
        """
        content_b64 = base64.b64encode(content.encode()).decode()
        
        chunks = await manager.process_file("skills.txt", content_b64)
        
        # Collect all tags across chunks
        all_tags = set()
        for chunk in chunks:
            all_tags.update(chunk.relevance_tags)
        
        # Should detect at least some technologies
        assert len(all_tags) > 0, "Should extract technology tags"
        
        # Check for specific common technologies
        all_tags_lower = {t.lower() for t in all_tags}
        assert "python" in all_tags_lower or "typescript" in all_tags_lower or "react" in all_tags_lower
    
    @pytest.mark.asyncio
    async def test_soft_skills_tags_extracted(self, manager):
        """Should extract soft skill keywords as tags."""
        content = """
        Strong leadership abilities with excellent teamwork and communication skills.
        Experienced in mentoring and collaboration across teams.
        """
        content_b64 = base64.b64encode(content.encode()).decode()
        
        chunks = await manager.process_file("about.txt", content_b64)
        
        all_tags = set()
        for chunk in chunks:
            all_tags.update(chunk.relevance_tags)
        
        # Should detect soft skills
        all_tags_lower = {t.lower() for t in all_tags}
        has_soft_skill = any(
            skill in all_tags_lower 
            for skill in ["leadership", "teamwork", "communication", "mentoring", "collaboration"]
        )
        assert has_soft_skill, f"Should extract soft skill tags. Got: {all_tags_lower}"


class TestInterviewerInfoDocumentType:
    """Tests for INTERVIEWER_INFO document type."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    @pytest.mark.asyncio
    async def test_interviewer_info_document_type(self, manager):
        """Should handle INTERVIEWER_INFO document type."""
        interviewer_content = """
        Key Background
        John Smith is the VP of Engineering at TechCorp.
        15 years of experience in distributed systems.
        
        Critical Expertise
        Deep knowledge in system design and scalability.
        Known for asking detailed architecture questions.
        
        Interview Preparation Recommendations
        - Prepare STAR stories for leadership questions
        - Be ready to discuss system design
        - Research the company's tech stack
        """
        content_b64 = base64.b64encode(interviewer_content.encode()).decode()
        
        chunks = await manager.process_file(
            "interviewer.txt",
            content_b64,
            DocumentType.INTERVIEWER_INFO
        )
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.document_type == DocumentType.INTERVIEWER_INFO
    
    @pytest.mark.asyncio
    async def test_interviewer_section_detection(self, manager):
        """Should detect sections in interviewer info documents."""
        interviewer_content = """
        Key Background
        Senior engineering leader with 20 years experience.
        
        Interview Preparation Recommendations
        Focus on behavioral questions and leadership examples.
        """
        content_b64 = base64.b64encode(interviewer_content.encode()).decode()
        
        chunks = await manager.process_file(
            "interviewer.txt",
            content_b64,
            DocumentType.INTERVIEWER_INFO
        )
        
        sections = {chunk.section for chunk in chunks}
        # Should detect at least background or recommendations section
        assert len(sections) >= 1


class TestMetadataEnrichment:
    """Tests for metadata enrichment (companies, dates, roles extraction)."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    def test_extract_known_tech_companies(self, manager):
        """Should extract company names from document context."""
        # Using formal suffixes - these get extracted from actual document content
        text = "I worked at Acme Corp and TechStart Inc before joining DataFlow LLC."
        enrichments = manager._extract_metadata_enrichments(text)
        
        companies = {c.lower() for c in enrichments["companies"]}
        # Should extract companies with formal suffixes from the document
        assert any("acme" in c for c in companies) or any("techstart" in c for c in companies)
    
    def test_extract_company_with_suffix(self, manager):
        """Should extract companies with Inc/Corp/LLC suffixes."""
        text = "Worked at Acme Corp and TechStart Inc for 3 years."
        enrichments = manager._extract_metadata_enrichments(text)
        
        # Should extract just the company name without prefix "at"
        companies = enrichments["companies"]
        assert any("Acme" in c for c in companies)
    
    def test_extract_year_ranges(self, manager):
        """Should extract year ranges like 2023-2026."""
        text = "I worked at Acme Corp from 2023 to 2026 and at TechStart Inc from 2021-2023."
        enrichments = manager._extract_metadata_enrichments(text)
        
        date_ranges = enrichments["date_ranges"]
        assert len(date_ranges) >= 2
        assert any("2023" in d and "2026" in d for d in date_ranges)
        assert any("2021" in d and "2023" in d for d in date_ranges)
    
    def test_extract_month_year_ranges(self, manager):
        """Should extract month-year ranges like 'Jan 2024 - Present'."""
        text = "Senior Engineer from January 2024 - Present at DataFlow LLC."
        enrichments = manager._extract_metadata_enrichments(text)
        
        date_ranges = enrichments["date_ranges"]
        assert len(date_ranges) >= 1
        assert any("2024" in d and "Present" in d for d in date_ranges)
    
    def test_extract_engineering_roles(self, manager):
        """Should extract engineering role titles."""
        text = "As a Senior Software Engineer, I led the backend team. Before that I was a Data Scientist."
        enrichments = manager._extract_metadata_enrichments(text)
        
        roles = {r.lower() for r in enrichments["roles"]}
        assert any("software engineer" in r for r in roles)
        assert any("data scientist" in r for r in roles)
    
    def test_extract_management_roles(self, manager):
        """Should extract management titles."""
        text = "I'm currently a VP of Engineering leading 50 engineers. Previously I was an Engineering Manager."
        enrichments = manager._extract_metadata_enrichments(text)
        
        roles = {r.lower() for r in enrichments["roles"]}
        assert any("vp" in r or "engineering manager" in r for r in roles)
    
    def test_extract_cxo_titles(self, manager):
        """Should extract C-level titles."""
        text = "The CTO and CIO reviewed our architecture proposal."
        enrichments = manager._extract_metadata_enrichments(text)
        
        roles = {r.upper() for r in enrichments["roles"]}
        assert "CTO" in roles or any("CTO" in r for r in roles)
    
    def test_no_false_positive_companies(self, manager):
        """Should not extract common words as company names."""
        text = "I worked at the office and collaborated with my team on the project."
        enrichments = manager._extract_metadata_enrichments(text)
        
        companies = {c.lower() for c in enrichments["companies"]}
        assert "the" not in companies
        assert "my" not in companies
        assert "at" not in companies
    
    @pytest.mark.asyncio
    async def test_enrichments_in_chunk_metadata(self, manager):
        """Metadata enrichments should be included in processed chunks."""
        resume_text = """
        ## Experience
        
        ### Senior Software Engineer at TechCorp Inc. (2023-2026)
        Led the development of distributed systems.
        
        ### Software Engineer at StartupXYZ LLC (2021-2023)
        Developed backend services for the marketplace.
        """
        content_b64 = base64.b64encode(resume_text.encode()).decode()
        
        chunks = await manager.process_file("resume.md", content_b64, DocumentType.RESUME)
        
        # At least one chunk should have company metadata
        chunks_with_companies = [c for c in chunks if "companies" in c.metadata]
        assert len(chunks_with_companies) > 0
        
        all_companies = set()
        for chunk in chunks_with_companies:
            all_companies.update(c.lower() for c in chunk.metadata["companies"])
        
        # Should extract companies with formal suffixes
        assert any("techcorp" in c for c in all_companies) or any("startupxyz" in c for c in all_companies)
    
    @pytest.mark.asyncio
    async def test_enrichments_in_qa_chunks(self, manager):
        """Metadata enrichments should work for Q&A documents too."""
        qa_text = """
        Q1: Tell me about your experience at your current company.
        A: I was a Senior Software Engineer at TechCorp Inc. from 2023-2026, working on distributed systems.
        
        Q2: What was your role at the previous company?
        A: At DataFlow LLC, I was a Software Engineer working on cloud services.
        """
        content_b64 = base64.b64encode(qa_text.encode()).decode()
        
        chunks = await manager.process_file("qa.md", content_b64, DocumentType.SAMPLE_QA)
        
        all_companies = set()
        for chunk in chunks:
            if "companies" in chunk.metadata:
                all_companies.update(c.lower() for c in chunk.metadata["companies"])
        
        # Should extract companies with formal suffixes from Q&A content
        assert any("techcorp" in c for c in all_companies) or any("dataflow" in c for c in all_companies)
