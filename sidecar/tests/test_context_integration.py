"""
Integration tests for context processing with realistic documents.
Tests the full flow from document upload to chunk retrieval.
"""

import pytest
import base64
import asyncio

from src.context.enhanced_manager import (
    EnhancedContextManager,
    DocumentType,
    EnhancedChunk,
)


class TestContextProcessingIntegration:
    """Integration tests for context processing with realistic content."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh manager for each test."""
        return EnhancedContextManager()
    
    # Sample Resume Content
    SAMPLE_RESUME = """
John Smith
Senior Software Engineer
john.smith@email.com | San Francisco, CA

Summary
Experienced software engineer with 8+ years of expertise in building scalable distributed systems.
Passionate about clean code, test-driven development, and mentoring junior engineers.

Experience

Senior Software Engineer, TechCorp Inc. (2020 - Present)
- Led team of 5 engineers to design and implement microservices architecture serving 10M+ users
- Reduced API latency by 60% through caching strategy and database optimization
- Introduced CI/CD pipelines that decreased deployment time from 2 hours to 15 minutes
- Mentored 3 junior developers through pair programming and code reviews

Software Engineer, StartupXYZ (2017 - 2020)
- Built real-time data processing pipeline handling 1M events per second
- Developed REST and GraphQL APIs used by mobile and web clients
- Implemented authentication system using OAuth2 and JWT tokens
- Participated in on-call rotation, achieving 99.9% uptime SLA

Junior Developer, WebAgency (2015 - 2017)
- Developed full-stack web applications using React and Node.js
- Created responsive designs that improved mobile engagement by 40%

Education

Master of Science in Computer Science
Stanford University, 2015

Bachelor of Science in Computer Engineering
MIT, 2013

Skills

Programming Languages: Python, TypeScript, Go, Rust, Java
Frameworks: React, FastAPI, Django, Express.js, Spring Boot
Cloud & DevOps: AWS, GCP, Kubernetes, Docker, Terraform, Jenkins
Databases: PostgreSQL, MongoDB, Redis, DynamoDB, Elasticsearch
Other: Machine Learning, System Design, Agile/Scrum

Certifications
- AWS Solutions Architect Professional
- Kubernetes Certified Administrator
"""

    SAMPLE_JOB_DESCRIPTION = """
Solutions Engineer - Enterprise Platform

About the Company
We are a leading enterprise software company transforming how businesses manage compliance and communication.
Our platform processes billions of messages daily and serves Fortune 500 clients globally.

About the Role
We're seeking an exceptional Solutions Engineer to bridge the gap between our customers and our engineering team.
You'll work directly with enterprise clients to design and implement custom solutions using our platform.

What You'll Do
- Partner with sales teams to understand customer technical requirements
- Design and architect custom solutions leveraging our API and platform capabilities
- Conduct technical demonstrations and proof-of-concept implementations
- Collaborate with product and engineering teams to influence roadmap
- Create technical documentation and best practices guides
- Support enterprise deployments and integrations

What You'll Bring
- 5+ years of experience in solutions engineering, pre-sales, or technical consulting
- Strong programming skills in Python, JavaScript, or similar languages
- Experience with REST APIs, webhooks, and integration patterns
- Knowledge of enterprise architecture and security requirements
- Excellent communication skills - ability to explain complex concepts to non-technical audiences
- Experience with compliance, archiving, or communication platforms (preferred)

Nice to Have
- Experience with AWS, Azure, or GCP cloud platforms
- Background in financial services, healthcare, or regulated industries
- Knowledge of regulatory frameworks (SEC, FINRA, GDPR, HIPAA)

What We Offer
- Competitive salary ($150K - $200K) + equity
- Comprehensive health, dental, and vision coverage
- Flexible work arrangements
- Professional development budget
- 401(k) matching
"""

    SAMPLE_QA_DOCUMENT = """
Q: Tell me about yourself
A: I'm a senior software engineer with over 8 years of experience building distributed systems. 
I started my career at a web agency learning full-stack development, then moved to a startup where 
I built real-time data pipelines processing millions of events. Currently at TechCorp, I lead a team 
of 5 engineers building microservices that serve over 10 million users. I'm particularly passionate 
about mentoring and have helped 3 junior developers grow into mid-level engineers.

Q: Why are you interested in this role?
A: This Solutions Engineer role excites me for several reasons. First, it combines my technical 
expertise with customer-facing work, which I've found very rewarding when doing technical demos 
for my current team. Second, the enterprise compliance domain is fascinating - I've worked with 
regulated industries and understand the importance of data governance. Third, I'm drawn to the 
challenge of translating complex customer requirements into elegant technical solutions.

Q: What's your greatest strength?
A: My greatest strength is my ability to simplify complex technical concepts for different audiences.
At TechCorp, I regularly present architecture decisions to both engineering teams and executives.
For example, when we redesigned our caching strategy, I created visual diagrams that helped 
non-technical stakeholders understand why this would improve customer experience. This skill 
would directly translate to the Solutions Engineer role where explaining our platform to 
enterprise clients is crucial.

Q: Describe a challenging project
A: At StartupXYZ, I was tasked with building a real-time data pipeline that needed to handle 
1 million events per second with sub-100ms latency. 

Situation: Our existing batch processing system couldn't meet customer SLAs for real-time analytics.
Task: I needed to design and implement a streaming architecture from scratch.
Action: I evaluated Kafka, Kinesis, and Pulsar, ultimately choosing Kafka for its ecosystem. 
I implemented a distributed consumer group with exactly-once semantics, added Redis for 
deduplication, and created a monitoring dashboard with Grafana.
Result: We launched on time, achieved 99.99% message delivery, and the system has scaled to 
2M events/second without architectural changes. This experience would help me design robust 
integration solutions for enterprise clients.
"""

    SAMPLE_COMPANY_INFO = """
About Smarsh

Company Overview
Smarsh is the leading provider of enterprise communications archiving and compliance solutions.
Founded in 2001, headquartered in Portland, Oregon with offices globally.

Products and Services
- Enterprise Archive: Captures and stores communications across 100+ channels
- Compliance Platform: Policy management, supervision, and eDiscovery
- Analytics Suite: AI-powered insights and risk detection

Key Statistics
- 6,500+ enterprise customers worldwide
- Processing 3 billion+ messages daily
- 500+ employees globally
- Series D funded, valued at $1.4B

Recent News
- Launched AI-powered risk detection in Q3 2023
- Expanded APAC presence with Singapore office
- Named Leader in Gartner Magic Quadrant for Enterprise Information Archiving

Culture and Values
- Innovation: Continuous improvement and cutting-edge technology
- Customer Success: Dedicated to helping customers achieve compliance goals
- Collaboration: Cross-functional teams and open communication
- Integrity: Ethical practices and transparency
"""

    @pytest.mark.asyncio
    async def test_process_resume(self, manager):
        """Should process resume and detect sections correctly."""
        content_b64 = base64.b64encode(self.SAMPLE_RESUME.encode()).decode()
        
        chunks = await manager.process_file(
            "resume.txt",
            content_b64,
            DocumentType.RESUME
        )
        
        assert len(chunks) > 0
        
        # Should have both parents and children
        parent_chunks = [c for c in chunks if c.level == "parent"]
        child_chunks = [c for c in chunks if c.level == "child"]
        
        # For a document this size, should have some hierarchy
        assert len(parent_chunks) >= 1
        
        # Check section detection
        sections = {c.section for c in chunks}
        # Should detect at least some standard resume sections
        assert len(sections) >= 1
        
        # Check that experience section is detected
        experience_chunks = [c for c in chunks if c.section == "experience"]
        if experience_chunks:
            # Experience section should mention companies from the resume
            experience_text = " ".join([c.text for c in experience_chunks])
            # Check for ANY company name (chunking may split differently)
            has_company = any(company in experience_text for company in 
                            ["TechCorp", "StartupXYZ", "WebAgency"])
            # OR check that we have experience-related content
            has_experience_keywords = any(word in experience_text.lower() for word in 
                            ["engineer", "developer", "built", "led", "developed", "implemented"])
            assert has_company or has_experience_keywords, \
                f"Experience section should contain company names or job keywords. Got: {experience_text[:200]}..."
        
        # Check relevance tags extracted
        all_tags = set()
        for chunk in chunks:
            all_tags.update(chunk.relevance_tags)
        
        # Should extract some technology tags
        assert len(all_tags) > 0
        # Common technologies should be detected
        all_tags_lower = {t.lower() for t in all_tags}
        has_tech = any(t in all_tags_lower for t in ["python", "react", "kubernetes", "aws"])
        assert has_tech, f"Should detect technology tags. Got: {all_tags}"
    
    @pytest.mark.asyncio
    async def test_process_job_description(self, manager):
        """Should process job description and detect sections correctly."""
        content_b64 = base64.b64encode(self.SAMPLE_JOB_DESCRIPTION.encode()).decode()
        
        chunks = await manager.process_file(
            "job.txt",
            content_b64,
            DocumentType.JOB_DESCRIPTION
        )
        
        assert len(chunks) > 0
        
        # Check section detection
        sections = {c.section for c in chunks}
        
        # Requirements and responsibilities are key JD sections
        requirements_chunks = [c for c in chunks if c.section == "requirements"]
        responsibilities_chunks = [c for c in chunks if c.section == "responsibilities"]
        
        # At least one of these should be detected
        assert len(requirements_chunks) > 0 or len(responsibilities_chunks) > 0 or "about" in sections
        
        # Check document type tagging
        for chunk in chunks:
            assert chunk.document_type == DocumentType.JOB_DESCRIPTION
    
    @pytest.mark.asyncio
    async def test_process_qa_document(self, manager):
        """Should process Q&A document and keep pairs atomic."""
        content_b64 = base64.b64encode(self.SAMPLE_QA_DOCUMENT.encode()).decode()
        
        chunks = await manager.process_file(
            "qa_prep.txt",
            content_b64,
            DocumentType.SAMPLE_QA
        )
        
        # Should have 4 Q&A pairs (4 questions in the sample)
        assert len(chunks) == 4, f"Expected 4 Q&A pairs, got {len(chunks)}"
        
        # Each chunk should be a parent (atomic)
        for chunk in chunks:
            assert chunk.level == "parent", "Q&A pairs should be atomic parents"
        
        # Each chunk should contain a question
        for chunk in chunks:
            text_lower = chunk.text.lower()
            assert "q:" in text_lower or "?" in chunk.text
        
        # Each chunk should have qa_index metadata
        for i, chunk in enumerate(chunks):
            assert "qa_index" in chunk.metadata
    
    @pytest.mark.asyncio
    async def test_process_company_info(self, manager):
        """Should process company info document correctly."""
        content_b64 = base64.b64encode(self.SAMPLE_COMPANY_INFO.encode()).decode()
        
        chunks = await manager.process_file(
            "company.txt",
            content_b64,
            DocumentType.COMPANY_INFO
        )
        
        assert len(chunks) > 0
        
        for chunk in chunks:
            assert chunk.document_type == DocumentType.COMPANY_INFO
    
    @pytest.mark.asyncio
    async def test_multi_document_integration(self, manager):
        """Should handle multiple documents of different types."""
        # Upload all documents
        resume_b64 = base64.b64encode(self.SAMPLE_RESUME.encode()).decode()
        jd_b64 = base64.b64encode(self.SAMPLE_JOB_DESCRIPTION.encode()).decode()
        qa_b64 = base64.b64encode(self.SAMPLE_QA_DOCUMENT.encode()).decode()
        company_b64 = base64.b64encode(self.SAMPLE_COMPANY_INFO.encode()).decode()
        
        await manager.process_file("resume.txt", resume_b64, DocumentType.RESUME)
        await manager.process_file("job.txt", jd_b64, DocumentType.JOB_DESCRIPTION)
        await manager.process_file("qa.txt", qa_b64, DocumentType.SAMPLE_QA)
        await manager.process_file("company.txt", company_b64, DocumentType.COMPANY_INFO)
        
        # Get all chunks
        all_chunks = manager.get_all_enhanced_chunks()
        assert len(all_chunks) > 0
        
        # Verify we have chunks from all document types
        types = {c.document_type for c in all_chunks}
        assert DocumentType.RESUME in types
        assert DocumentType.JOB_DESCRIPTION in types
        assert DocumentType.SAMPLE_QA in types
        assert DocumentType.COMPANY_INFO in types
        
        # Verify type-specific retrieval
        resume_chunks = manager.get_chunks_by_type(DocumentType.RESUME)
        assert len(resume_chunks) > 0
        for chunk in resume_chunks:
            assert chunk.document_type == DocumentType.RESUME
        
        jd_chunks = manager.get_chunks_by_type(DocumentType.JOB_DESCRIPTION)
        assert len(jd_chunks) > 0
        
        qa_chunks = manager.get_chunks_by_type(DocumentType.SAMPLE_QA)
        assert len(qa_chunks) == 4  # 4 Q&A pairs
    
    @pytest.mark.asyncio
    async def test_parent_chunk_lookup(self, manager):
        """Should be able to look up parent chunks from child chunks."""
        content_b64 = base64.b64encode(self.SAMPLE_RESUME.encode()).decode()
        
        await manager.process_file("resume.txt", content_b64, DocumentType.RESUME)
        
        child_chunks = manager.get_child_chunks()
        
        for child in child_chunks:
            if child.parent_chunk_id:
                parent = manager.get_parent_chunk(child.parent_chunk_id)
                assert parent is not None, f"Parent {child.parent_chunk_id} not found"
                assert parent.level == "parent"
                # Parent should contain the child's content (or overlap)
    
    @pytest.mark.asyncio
    async def test_clear_context_clears_all(self, manager):
        """Should clear all data when clear_context is called."""
        content_b64 = base64.b64encode(self.SAMPLE_RESUME.encode()).decode()
        
        await manager.process_file("resume.txt", content_b64, DocumentType.RESUME)
        
        assert len(manager.get_all_enhanced_chunks()) > 0
        
        manager.clear_context()
        
        assert len(manager.get_all_enhanced_chunks()) == 0
        assert len(manager.documents_by_type) == 0
        assert len(manager._parent_map) == 0
        assert len(manager.processed_files) == 0


class TestChunkQuality:
    """Tests for chunk quality and content preservation."""
    
    @pytest.fixture
    def manager(self):
        return EnhancedContextManager()
    
    SAMPLE_TEXT = """
Experience

Senior Software Engineer at TechCorp (2020-2024)
Led team of 5 engineers building microservices architecture.
Reduced API latency by 60% through caching optimization.
Implemented CI/CD pipelines reducing deployment from 2 hours to 15 minutes.
Mentored 3 junior developers through code reviews and pair programming.

Skills

Python, TypeScript, Go, Rust, Java, React, FastAPI, Django, AWS, GCP, Kubernetes, Docker.
"""

    @pytest.mark.asyncio
    async def test_no_content_loss(self, manager):
        """Chunking should not lose significant content."""
        content_b64 = base64.b64encode(self.SAMPLE_TEXT.encode()).decode()
        
        chunks = await manager.process_file("test.txt", content_b64, DocumentType.RESUME)
        
        # Combine all chunk text
        all_text = " ".join([c.text for c in chunks])
        
        # Key content should be preserved
        assert "TechCorp" in all_text
        assert "microservices" in all_text
        assert "60%" in all_text
        assert "Python" in all_text
    
    @pytest.mark.asyncio
    async def test_section_boundaries_respected(self, manager):
        """Sections should not be mixed inappropriately."""
        content_b64 = base64.b64encode(self.SAMPLE_TEXT.encode()).decode()
        
        chunks = await manager.process_file("test.txt", content_b64, DocumentType.RESUME)
        
        # Experience section chunks should contain experience-related content
        experience_chunks = [c for c in chunks if c.section == "experience"]
        for chunk in experience_chunks:
            # Should contain TechCorp or job-related content
            if len(chunk.text) > 50:  # Ignore very short chunks
                assert "TechCorp" in chunk.text or "engineer" in chunk.text.lower() or "led" in chunk.text.lower()
    
    @pytest.mark.asyncio
    async def test_metadata_consistency(self, manager):
        """Chunk metadata should be consistent and complete."""
        content_b64 = base64.b64encode(self.SAMPLE_TEXT.encode()).decode()
        
        chunks = await manager.process_file("resume.txt", content_b64, DocumentType.RESUME)
        
        for chunk in chunks:
            # All required fields should be set
            assert chunk.id is not None
            assert chunk.text is not None
            assert chunk.document_type is not None
            assert chunk.section is not None
            assert chunk.level in ("parent", "child")
            assert chunk.start_char >= 0
            assert chunk.end_char > chunk.start_char
            
            # Metadata should include document_type
            assert "document_type" in chunk.metadata
            assert chunk.metadata["document_type"] == "resume"
            
            # Metadata should include source
            assert "source" in chunk.metadata
            assert chunk.metadata["source"] == "resume.txt"
