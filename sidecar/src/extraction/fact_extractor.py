"""
Fact Extractor - LLM-based structured fact extraction from documents.

Extracts:
- Skills with years and proficiency
- Career timeline with highlights and metrics
- Achievements with quantified impact
- Education and certifications

Part of Phase 4: Interview Coach Evolution (STORY-055)
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Protocol, AsyncGenerator

from memory.models import (
    ExtractedFacts,
    SkillEntry,
    CareerEntry,
    Achievement,
    Education,
    DocumentType,
    SkillProficiency,
)


logger = logging.getLogger(__name__)


# Fact extraction prompt template
FACT_EXTRACTION_PROMPT = """You are analyzing a {document_type} to extract structured facts for interview preparation.

Extract the following information in JSON format:

1. **skills**: List of technical and soft skills with:
   - name: Skill name
   - years: Years of experience (if stated, otherwise null)
   - proficiency: "expert" (5+ years or lead), "proficient" (2-5 years), "familiar" (<2 years)
   - last_used: Company/role where most recently used
   - context: Brief context of how used

2. **career**: List of positions with:
   - company: Company name
   - role: Job title
   - start_date: Start date (format: YYYY-MM or YYYY)
   - end_date: End date (null if current)
   - is_current: true if current position
   - highlights: 2-3 key accomplishments
   - metrics: Quantified results (percentages, dollars, team sizes)
   - location: City/remote if mentioned

3. **achievements**: Notable accomplishments with:
   - description: What was achieved
   - metrics: Quantified impact ["40% reduction", "$2M saved"]
   - context: Company/project where achieved
   - tags: Categories ["leadership", "technical", "scale", "cost", "quality", "speed"]

4. **education**: List of degrees with:
   - institution: School name
   - degree: Degree type (BS, MS, PhD, etc.)
   - field_of_study: Major/field
   - year: Graduation year
   - honors: Honors/GPA if mentioned

5. **certifications**: List of certification names

6. **total_experience_years**: Total years of professional experience
7. **current_role**: Current job title
8. **current_company**: Current employer
9. **industries**: List of industries worked in
10. **languages**: Programming or spoken languages

Document:
---
{document_text}
---

Respond ONLY with valid JSON matching this structure:
{{
  "skills": [...],
  "career": [...],
  "achievements": [...],
  "education": [...],
  "certifications": [...],
  "total_experience_years": 0,
  "current_role": "",
  "current_company": "",
  "industries": [],
  "languages": []
}}"""


# JD-specific extraction prompt
JD_EXTRACTION_PROMPT = """You are analyzing a job description to extract requirements for interview preparation.

Extract the following information in JSON format:

1. **required_skills**: Skills explicitly required with:
   - name: Skill name
   - years: Years required (if stated)
   - proficiency: Required level
   - is_required: true if must-have, false if nice-to-have

2. **responsibilities**: Key job responsibilities

3. **qualifications**: Required qualifications (education, experience level)

4. **company_info**: Any company context mentioned

5. **role_level**: Seniority level (junior, mid, senior, staff, principal, etc.)

6. **team_info**: Team size, structure if mentioned

Job Description:
---
{document_text}
---

Respond ONLY with valid JSON."""


class FactExtractor:
    """
    Extracts structured facts from documents using LLM.
    
    Handles resumes, job descriptions, and other document types,
    producing structured data suitable for interview preparation.
    """
    
    # Maximum characters to send to LLM
    MAX_DOCUMENT_LENGTH = 15000
    
    def __init__(
        self, 
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None
    ):
        """
        Initialize the fact extractor.
        
        Args:
            llm_provider: LLM provider for generating extractions
            memory_store: Memory store for caching results
        """
        self.llm_provider = llm_provider
        self.memory_store = memory_store
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set or update the LLM provider."""
        self.llm_provider = provider
    
    def set_memory_store(self, store: Any) -> None:
        """Set or update the memory store."""
        self.memory_store = store
    
    async def extract_facts(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType,
        force_regenerate: bool = False
    ) -> ExtractedFacts:
        """
        Extract structured facts from a document.
        
        Args:
            document_id: Unique identifier for the document
            text: Full text content of the document
            document_type: Type of document (resume, JD, etc.)
            force_regenerate: If True, regenerate even if cached
            
        Returns:
            ExtractedFacts with structured data
        """
        # Check cache first
        if not force_regenerate and self.memory_store:
            cached = self.memory_store.get_facts_for_document(document_id)
            if cached:
                logger.info(f"Using cached facts for document {document_id}")
                return cached
        
        # Truncate text if too long
        truncated_text = text[:self.MAX_DOCUMENT_LENGTH]
        if len(text) > self.MAX_DOCUMENT_LENGTH:
            logger.warning(f"Document truncated from {len(text)} to {self.MAX_DOCUMENT_LENGTH} chars")
        
        # Extract facts
        if self.llm_provider:
            facts = await self._extract_with_llm(
                document_id, truncated_text, document_type
            )
        else:
            logger.warning("No LLM provider available, using regex extraction")
            facts = self._regex_extraction(
                document_id, truncated_text, document_type
            )
        
        # Cache result
        if self.memory_store:
            self.memory_store.save_facts(document_id, facts)
            logger.info(f"Saved facts for document {document_id}")
        
        return facts
    
    async def _extract_with_llm(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType
    ) -> ExtractedFacts:
        """Extract facts using LLM provider."""
        # Select appropriate prompt
        if document_type == DocumentType.JOB_DESCRIPTION:
            prompt = JD_EXTRACTION_PROMPT.format(document_text=text)
        else:
            prompt = FACT_EXTRACTION_PROMPT.format(
                document_type=self._format_document_type(document_type),
                document_text=text
            )
        
        # Collect streaming response
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            # Parse JSON response
            facts = self._parse_llm_response(full_response, document_id, document_type)
            return facts
            
        except Exception as e:
            logger.error(f"LLM fact extraction failed: {e}")
            # Fallback to regex extraction
            return self._regex_extraction(document_id, text, document_type)
    
    def _parse_llm_response(
        self,
        response: str,
        document_id: str,
        document_type: DocumentType
    ) -> ExtractedFacts:
        """Parse the LLM response into ExtractedFacts."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return self._dict_to_facts(data, document_id)
            else:
                logger.warning("No JSON found in LLM response")
                return ExtractedFacts(document_id=document_id)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return ExtractedFacts(document_id=document_id)
    
    def _dict_to_facts(self, data: Dict[str, Any], document_id: str) -> ExtractedFacts:
        """Convert parsed JSON dict to ExtractedFacts."""
        # Parse skills
        skills = []
        for skill_data in data.get("skills", []) or data.get("required_skills", []):
            if isinstance(skill_data, str):
                skills.append(SkillEntry(name=skill_data))
            elif isinstance(skill_data, dict):
                proficiency = skill_data.get("proficiency", "proficient")
                try:
                    prof_enum = SkillProficiency(proficiency.lower())
                except (ValueError, AttributeError):
                    prof_enum = SkillProficiency.PROFICIENT
                
                skills.append(SkillEntry(
                    name=skill_data.get("name", ""),
                    years=skill_data.get("years"),
                    proficiency=prof_enum,
                    last_used=skill_data.get("last_used"),
                    context=skill_data.get("context"),
                ))
        
        # Parse career timeline
        timeline = []
        for career_data in data.get("career", []):
            if isinstance(career_data, dict):
                timeline.append(CareerEntry(
                    company=career_data.get("company", ""),
                    role=career_data.get("role", ""),
                    start_date=career_data.get("start_date", ""),
                    end_date=career_data.get("end_date"),
                    highlights=career_data.get("highlights", []),
                    metrics=career_data.get("metrics", []),
                    location=career_data.get("location"),
                    is_current=career_data.get("is_current", False),
                ))
        
        # Parse achievements
        achievements = []
        for ach_data in data.get("achievements", []):
            if isinstance(ach_data, str):
                achievements.append(Achievement(description=ach_data))
            elif isinstance(ach_data, dict):
                achievements.append(Achievement(
                    description=ach_data.get("description", ""),
                    metrics=ach_data.get("metrics", []),
                    context=ach_data.get("context", ""),
                    tags=ach_data.get("tags", []),
                ))
        
        # Parse education
        education = []
        for edu_data in data.get("education", []):
            if isinstance(edu_data, str):
                education.append(Education(institution=edu_data, degree=""))
            elif isinstance(edu_data, dict):
                education.append(Education(
                    institution=edu_data.get("institution", ""),
                    degree=edu_data.get("degree", ""),
                    field_of_study=edu_data.get("field_of_study"),
                    year=edu_data.get("year"),
                    honors=edu_data.get("honors"),
                ))
        
        return ExtractedFacts(
            skills=skills,
            timeline=timeline,
            achievements=achievements,
            education=education,
            certifications=data.get("certifications", []),
            total_experience_years=data.get("total_experience_years", 0),
            current_role=data.get("current_role", ""),
            current_company=data.get("current_company", ""),
            industries=data.get("industries", []),
            languages=data.get("languages", []),
            document_id=document_id,
            extracted_at=datetime.now(),
        )
    
    def _regex_extraction(
        self,
        document_id: str,
        text: str,
        document_type: DocumentType
    ) -> ExtractedFacts:
        """Fallback regex-based extraction when LLM unavailable."""
        skills = self._extract_skills_regex(text)
        timeline = self._extract_timeline_regex(text)
        achievements = self._extract_achievements_regex(text)
        education = self._extract_education_regex(text)
        certifications = self._extract_certifications_regex(text)
        
        # Calculate total experience
        total_years = self._calculate_total_experience(timeline)
        
        # Get current role
        current_role = ""
        current_company = ""
        for entry in timeline:
            if entry.is_current or entry.end_date is None:
                current_role = entry.role
                current_company = entry.company
                break
        
        return ExtractedFacts(
            skills=skills,
            timeline=timeline,
            achievements=achievements,
            education=education,
            certifications=certifications,
            total_experience_years=total_years,
            current_role=current_role,
            current_company=current_company,
            document_id=document_id,
            extracted_at=datetime.now(),
        )
    
    def _extract_skills_regex(self, text: str) -> List[SkillEntry]:
        """Extract skills using regex patterns."""
        skills = []
        seen = set()
        
        # Common programming languages and technologies
        tech_patterns = [
            r'\b(Python|JavaScript|TypeScript|Java|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
            r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring|\.NET)\b',
            r'\b(AWS|GCP|Azure|Docker|Kubernetes|Terraform)\b',
            r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b',
            r'\b(Machine Learning|ML|AI|Deep Learning|NLP)\b',
            r'\b(Git|CI/CD|Agile|Scrum)\b',
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill_name = match if isinstance(match, str) else match[0]
                skill_lower = skill_name.lower()
                if skill_lower not in seen:
                    seen.add(skill_lower)
                    # Try to find years of experience
                    years = self._find_skill_years(text, skill_name)
                    proficiency = self._infer_proficiency(years)
                    skills.append(SkillEntry(
                        name=skill_name,
                        years=years,
                        proficiency=proficiency,
                    ))
        
        return skills[:20]  # Limit to 20 skills
    
    def _find_skill_years(self, text: str, skill: str) -> Optional[int]:
        """Find years of experience for a skill."""
        # Pattern: "5 years of Python" or "Python (5 years)"
        patterns = [
            rf'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?{re.escape(skill)}',
            rf'{re.escape(skill)}\s*[\(\[]?\s*(\d+)\+?\s*(?:years?|yrs?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass
        return None
    
    def _infer_proficiency(self, years: Optional[int]) -> SkillProficiency:
        """Infer proficiency from years of experience."""
        if years is None:
            return SkillProficiency.PROFICIENT
        elif years >= 5:
            return SkillProficiency.EXPERT
        elif years >= 2:
            return SkillProficiency.PROFICIENT
        else:
            return SkillProficiency.FAMILIAR
    
    def _extract_timeline_regex(self, text: str) -> List[CareerEntry]:
        """Extract career timeline using regex patterns."""
        timeline = []
        
        # Pattern for company and role with dates
        # Matches: "Senior Engineer at Google (2020 - Present)" or "Google - Senior Engineer, 2018-2020"
        patterns = [
            r'(?P<role>[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*(?:\s+Engineer|Developer|Manager|Lead|Director|VP|CTO|CEO)?)\s*(?:at|@|-|,)\s*(?P<company>[A-Z][a-zA-Z\s&]+?)[\s,\(\-]+(?P<start>\d{4})\s*[-–to]+\s*(?P<end>\d{4}|[Pp]resent)',
            r'(?P<company>[A-Z][a-zA-Z\s&]+?)\s*[-–]\s*(?P<role>[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*(?:\s+Engineer|Developer|Manager|Lead)?)\s*[\s,\(\-]+(?P<start>\d{4})\s*[-–to]+\s*(?P<end>\d{4}|[Pp]resent)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groupdict()
                end_date = groups.get('end')
                is_current = end_date and 'present' in end_date.lower()
                
                entry = CareerEntry(
                    company=groups.get('company', '').strip(),
                    role=groups.get('role', '').strip(),
                    start_date=groups.get('start', ''),
                    end_date=None if is_current else end_date,
                    is_current=is_current,
                )
                if entry.company and entry.role:
                    timeline.append(entry)
        
        return timeline[:10]  # Limit to 10 positions
    
    def _extract_achievements_regex(self, text: str) -> List[Achievement]:
        """Extract achievements using regex patterns."""
        achievements = []
        
        # Look for bullet points with action verbs and metrics
        action_patterns = [
            r'[•\-\*]\s*((?:Led|Built|Designed|Developed|Implemented|Reduced|Increased|Improved|Launched|Created|Managed|Delivered|Achieved|Spearheaded|Drove|Optimized)[^•\-\*\n]{20,200})',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                description = match.strip()
                metrics = self._extract_metrics_from_text(description)
                tags = self._infer_achievement_tags(description)
                
                achievements.append(Achievement(
                    description=description,
                    metrics=metrics,
                    tags=tags,
                ))
        
        return achievements[:15]  # Limit to 15 achievements
    
    def _extract_metrics_from_text(self, text: str) -> List[str]:
        """Extract quantified metrics from text."""
        metrics = []
        
        # Percentage improvements
        pct_matches = re.findall(r'(\d+%\s*(?:improvement|reduction|increase|growth)?)', text, re.IGNORECASE)
        metrics.extend(pct_matches)
        
        # Dollar amounts
        dollar_matches = re.findall(r'(\$[\d,.]+[KMB]?)', text)
        metrics.extend(dollar_matches)
        
        # Team sizes
        team_matches = re.findall(r'(team\s+of\s+\d+|\d+\s*(?:engineers?|developers?|people|members))', text, re.IGNORECASE)
        metrics.extend(team_matches)
        
        # Large numbers (users, requests, etc.)
        scale_matches = re.findall(r'(\d+[KMB]\+?\s*(?:users?|requests?|customers?|transactions?))', text, re.IGNORECASE)
        metrics.extend(scale_matches)
        
        return metrics[:5]
    
    def _infer_achievement_tags(self, text: str) -> List[str]:
        """Infer achievement category tags from text."""
        tags = []
        text_lower = text.lower()
        
        tag_patterns = {
            "leadership": ["led", "managed", "team", "mentored", "coordinated"],
            "technical": ["built", "designed", "implemented", "developed", "architected"],
            "scale": ["users", "requests", "traffic", "scale", "distributed"],
            "cost": ["cost", "saved", "$", "budget", "revenue"],
            "quality": ["quality", "reliability", "uptime", "99."],
            "speed": ["faster", "latency", "performance", "reduced time", "optimized"],
        }
        
        for tag, keywords in tag_patterns.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def _extract_education_regex(self, text: str) -> List[Education]:
        """Extract education using regex patterns."""
        education = []
        
        # Pattern for degrees
        degree_patterns = [
            r'(?P<degree>(?:B\.?S\.?|M\.?S\.?|Ph\.?D\.?|Bachelor|Master|MBA)(?:\s+(?:of|in)\s+)?(?:Science|Arts|Engineering|Computer Science|Business)?)\s*(?:from|,|-|at)?\s*(?P<institution>[A-Z][a-zA-Z\s]+(?:University|Institute|College))',
            r'(?P<institution>[A-Z][a-zA-Z\s]+(?:University|Institute|College))\s*[-,]\s*(?P<degree>(?:B\.?S\.?|M\.?S\.?|Ph\.?D\.?|Bachelor|Master|MBA))',
        ]
        
        for pattern in degree_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groupdict()
                
                # Try to find year
                year = None
                year_match = re.search(r'(\d{4})', text[match.end():match.end()+20])
                if year_match:
                    year = int(year_match.group(1))
                
                education.append(Education(
                    institution=groups.get('institution', '').strip(),
                    degree=groups.get('degree', '').strip(),
                    year=year,
                ))
        
        return education[:5]
    
    def _extract_certifications_regex(self, text: str) -> List[str]:
        """Extract certifications using regex patterns."""
        certifications = []
        
        # Common certification patterns
        cert_patterns = [
            r'(AWS\s+(?:Solutions?\s+Architect|Developer|SysOps|DevOps)(?:\s+(?:Associate|Professional))?)',
            r'(GCP\s+(?:Professional\s+)?(?:Cloud\s+(?:Architect|Engineer|Developer))?)',
            r'(Azure\s+(?:Administrator|Developer|Architect|Solutions?\s+Architect)?)',
            r'(Certified\s+(?:Kubernetes|Scrum\s+Master|Product\s+Owner|PMP))',
            r'((?:CISSP|CISM|CEH|CompTIA\s+\w+))',
        ]
        
        for pattern in cert_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                cert = match.strip()
                if cert and cert not in certifications:
                    certifications.append(cert)
        
        return certifications[:10]
    
    def _calculate_total_experience(self, timeline: List[CareerEntry]) -> int:
        """Calculate total years of experience from timeline."""
        if not timeline:
            return 0
        
        total_years = 0
        current_year = datetime.now().year
        
        for entry in timeline:
            try:
                start_year = int(entry.start_date[:4]) if entry.start_date else current_year
                end_year = current_year if entry.is_current or not entry.end_date else int(entry.end_date[:4])
                total_years += max(0, end_year - start_year)
            except (ValueError, IndexError):
                continue
        
        return min(total_years, 50)  # Cap at 50 years
    
    def _format_document_type(self, doc_type: DocumentType) -> str:
        """Format document type for prompt."""
        type_names = {
            DocumentType.RESUME: "resume/CV",
            DocumentType.JOB_DESCRIPTION: "job description",
            DocumentType.COMPANY_INFO: "company information",
            DocumentType.INTERVIEWER_INFO: "interviewer background",
            DocumentType.OTHER: "document",
        }
        return type_names.get(doc_type, "document")
    
    async def get_merged_facts(self) -> ExtractedFacts:
        """Get all facts merged from all documents."""
        if self.memory_store:
            return self.memory_store.get_all_facts()
        return ExtractedFacts()
