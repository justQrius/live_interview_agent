"""
Data models for the Memory Store.

These models represent structured candidate information extracted from documents.
All models are immutable dataclasses with JSON serialization support.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import uuid


class DocumentType(str, Enum):
    """Types of documents that can be uploaded."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    COMPANY_INFO = "company_info"
    INTERVIEWER_INFO = "interviewer_info"
    OTHER = "other"


class SkillProficiency(str, Enum):
    """Proficiency levels for skills."""
    EXPERT = "expert"
    PROFICIENT = "proficient"
    FAMILIAR = "familiar"
    LEARNING = "learning"


class ClaimType(str, Enum):
    """Types of claims made during interviews."""
    EXPERIENCE_YEARS = "experience_years"
    TEAM_SIZE = "team_size"
    METRIC_PERCENT = "metric_percent"
    METRIC_MONEY = "metric_money"
    SKILL_LEVEL = "skill_level"
    ACHIEVEMENT = "achievement"
    OTHER = "other"


@dataclass
class SkillEntry:
    """A single skill with proficiency information."""
    name: str
    years: Optional[int] = None
    proficiency: SkillProficiency = SkillProficiency.PROFICIENT
    last_used: Optional[str] = None
    context: Optional[str] = None  # Where this skill was used

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "years": self.years,
            "proficiency": self.proficiency.value if isinstance(self.proficiency, SkillProficiency) else self.proficiency,
            "last_used": self.last_used,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillEntry":
        proficiency = data.get("proficiency", "proficient")
        if isinstance(proficiency, str):
            try:
                proficiency = SkillProficiency(proficiency)
            except ValueError:
                proficiency = SkillProficiency.PROFICIENT
        return cls(
            name=data["name"],
            years=data.get("years"),
            proficiency=proficiency,
            last_used=data.get("last_used"),
            context=data.get("context"),
        )


@dataclass
class CareerEntry:
    """A single position in career timeline."""
    company: str
    role: str
    start_date: str
    end_date: Optional[str] = None  # None means "Present"
    highlights: List[str] = field(default_factory=list)
    metrics: List[str] = field(default_factory=list)
    location: Optional[str] = None
    is_current: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company,
            "role": self.role,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "highlights": self.highlights,
            "metrics": self.metrics,
            "location": self.location,
            "is_current": self.is_current,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CareerEntry":
        return cls(
            company=data["company"],
            role=data["role"],
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            highlights=data.get("highlights", []),
            metrics=data.get("metrics", []),
            location=data.get("location"),
            is_current=data.get("is_current", False),
        )


@dataclass
class Achievement:
    """A notable achievement with quantifiable impact."""
    description: str
    metrics: List[str] = field(default_factory=list)  # ["40% reduction", "$2M saved"]
    context: str = ""  # Which company/role
    tags: List[str] = field(default_factory=list)  # ["leadership", "technical", "scale"]
    impact_level: Optional[str] = None  # "high", "medium", "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "metrics": self.metrics,
            "context": self.context,
            "tags": self.tags,
            "impact_level": self.impact_level,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Achievement":
        return cls(
            description=data["description"],
            metrics=data.get("metrics", []),
            context=data.get("context", ""),
            tags=data.get("tags", []),
            impact_level=data.get("impact_level"),
        )


@dataclass
class Education:
    """Educational background entry."""
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    year: Optional[int] = None
    honors: Optional[str] = None
    gpa: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "institution": self.institution,
            "degree": self.degree,
            "field_of_study": self.field_of_study,
            "year": self.year,
            "honors": self.honors,
            "gpa": self.gpa,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Education":
        return cls(
            institution=data["institution"],
            degree=data["degree"],
            field_of_study=data.get("field_of_study"),
            year=data.get("year"),
            honors=data.get("honors"),
            gpa=data.get("gpa"),
        )


@dataclass
class ExtractedFacts:
    """All structured facts extracted from candidate documents."""
    skills: List[SkillEntry] = field(default_factory=list)
    timeline: List[CareerEntry] = field(default_factory=list)
    achievements: List[Achievement] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    total_experience_years: int = 0
    current_role: str = ""
    current_company: str = ""
    industries: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    document_id: Optional[str] = None
    extracted_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "timeline": [t.to_dict() for t in self.timeline],
            "achievements": [a.to_dict() for a in self.achievements],
            "education": [e.to_dict() for e in self.education],
            "certifications": self.certifications,
            "total_experience_years": self.total_experience_years,
            "current_role": self.current_role,
            "current_company": self.current_company,
            "industries": self.industries,
            "languages": self.languages,
            "document_id": self.document_id,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractedFacts":
        extracted_at = data.get("extracted_at")
        if extracted_at and isinstance(extracted_at, str):
            extracted_at = datetime.fromisoformat(extracted_at)

        return cls(
            skills=[SkillEntry.from_dict(s) for s in data.get("skills", [])],
            timeline=[CareerEntry.from_dict(t) for t in data.get("timeline", [])],
            achievements=[Achievement.from_dict(a) for a in data.get("achievements", [])],
            education=[Education.from_dict(e) for e in data.get("education", [])],
            certifications=data.get("certifications", []),
            total_experience_years=data.get("total_experience_years", 0),
            current_role=data.get("current_role", ""),
            current_company=data.get("current_company", ""),
            industries=data.get("industries", []),
            languages=data.get("languages", []),
            document_id=data.get("document_id"),
            extracted_at=extracted_at,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "ExtractedFacts":
        return cls.from_dict(json.loads(json_str))

    def merge_with(self, other: "ExtractedFacts") -> "ExtractedFacts":
        """Merge facts from another ExtractedFacts instance."""
        # Merge skills (deduplicate by name)
        skill_names = {s.name.lower() for s in self.skills}
        merged_skills = list(self.skills)
        for skill in other.skills:
            if skill.name.lower() not in skill_names:
                merged_skills.append(skill)
                skill_names.add(skill.name.lower())

        # Merge timeline (sort by start date)
        merged_timeline = list(self.timeline) + list(other.timeline)
        merged_timeline.sort(key=lambda x: x.start_date, reverse=True)

        # Merge achievements (deduplicate by description)
        achievement_descs = {a.description.lower() for a in self.achievements}
        merged_achievements = list(self.achievements)
        for ach in other.achievements:
            if ach.description.lower() not in achievement_descs:
                merged_achievements.append(ach)
                achievement_descs.add(ach.description.lower())

        # Merge education
        edu_keys = {(e.institution.lower(), e.degree.lower()) for e in self.education}
        merged_education = list(self.education)
        for edu in other.education:
            key = (edu.institution.lower(), edu.degree.lower())
            if key not in edu_keys:
                merged_education.append(edu)
                edu_keys.add(key)

        # Merge simple lists
        merged_certs = list(set(self.certifications + other.certifications))
        merged_industries = list(set(self.industries + other.industries))
        merged_languages = list(set(self.languages + other.languages))

        return ExtractedFacts(
            skills=merged_skills,
            timeline=merged_timeline,
            achievements=merged_achievements,
            education=merged_education,
            certifications=merged_certs,
            total_experience_years=max(self.total_experience_years, other.total_experience_years),
            current_role=self.current_role or other.current_role,
            current_company=self.current_company or other.current_company,
            industries=merged_industries,
            languages=merged_languages,
            extracted_at=datetime.now(),
        )


@dataclass
class STARStory:
    """A STAR-format story for behavioral interview questions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""  # "The Migration Crisis"
    situation: str = ""  # 2-3 sentences
    task: str = ""  # 1-2 sentences
    action: str = ""  # 3-5 sentences with specifics
    result: str = ""  # 1-2 sentences with metrics
    metrics: List[str] = field(default_factory=list)  # ["40% latency reduction", "zero downtime"]
    tags: List[str] = field(default_factory=list)  # ["leadership", "crisis", "technical", "scale"]
    source_company: str = ""
    source_role: str = ""
    opening_line: str = ""  # Suggested first sentence
    twenty_second_version: str = ""  # Compressed version
    full_version: str = ""  # Complete ~2 minute version
    confidence: float = 0.0  # How complete is this story (0-1)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "situation": self.situation,
            "task": self.task,
            "action": self.action,
            "result": self.result,
            "metrics": self.metrics,
            "tags": self.tags,
            "source_company": self.source_company,
            "source_role": self.source_role,
            "opening_line": self.opening_line,
            "twenty_second_version": self.twenty_second_version,
            "full_version": self.full_version,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "STARStory":
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        updated_at = data.get("updated_at")
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            situation=data.get("situation", ""),
            task=data.get("task", ""),
            action=data.get("action", ""),
            result=data.get("result", ""),
            metrics=data.get("metrics", []),
            tags=data.get("tags", []),
            source_company=data.get("source_company", ""),
            source_role=data.get("source_role", ""),
            opening_line=data.get("opening_line", ""),
            twenty_second_version=data.get("twenty_second_version", ""),
            full_version=data.get("full_version", ""),
            confidence=data.get("confidence", 0.0),
            created_at=created_at,
            updated_at=updated_at,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "STARStory":
        return cls.from_dict(json.loads(json_str))

    def get_full_story(self) -> str:
        """Return the full STAR story as a formatted string."""
        return f"""**{self.title}**

**Situation:** {self.situation}

**Task:** {self.task}

**Action:** {self.action}

**Result:** {self.result}

**Key Metrics:** {', '.join(self.metrics)}"""


@dataclass
class CandidateProfile:
    """Compact candidate profile for LLM prompt injection (~1000 tokens)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    profile_text: str = ""  # The ~1000 token summary
    current_role: str = ""
    total_experience_years: int = 0
    core_skills: List[str] = field(default_factory=list)
    key_achievements: List[str] = field(default_factory=list)
    target_role: str = ""
    target_company: str = ""
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    generated_at: Optional[datetime] = None
    source_documents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "profile_text": self.profile_text,
            "current_role": self.current_role,
            "total_experience_years": self.total_experience_years,
            "core_skills": self.core_skills,
            "key_achievements": self.key_achievements,
            "target_role": self.target_role,
            "target_company": self.target_company,
            "strengths": self.strengths,
            "gaps": self.gaps,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "source_documents": self.source_documents,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CandidateProfile":
        generated_at = data.get("generated_at")
        if generated_at and isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            profile_text=data.get("profile_text", ""),
            current_role=data.get("current_role", ""),
            total_experience_years=data.get("total_experience_years", 0),
            core_skills=data.get("core_skills", []),
            key_achievements=data.get("key_achievements", []),
            target_role=data.get("target_role", ""),
            target_company=data.get("target_company", ""),
            strengths=data.get("strengths", []),
            gaps=data.get("gaps", []),
            generated_at=generated_at,
            source_documents=data.get("source_documents", []),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "CandidateProfile":
        return cls.from_dict(json.loads(json_str))

    def get_prompt_injection(self) -> str:
        """Get the profile text for LLM prompt injection."""
        if self.profile_text:
            return self.profile_text

        # Generate from structured data if profile_text not set
        skills_str = ", ".join(self.core_skills[:10]) if self.core_skills else "Not specified"
        achievements_str = "\n".join(f"- {a}" for a in self.key_achievements[:5]) if self.key_achievements else "Not specified"

        return f"""## Candidate Profile

**Current Role**: {self.current_role or 'Not specified'}
**Experience**: {self.total_experience_years} years
**Target Position**: {self.target_role or 'Not specified'} at {self.target_company or 'Not specified'}

### Core Competencies
{skills_str}

### Key Achievements
{achievements_str}

### Strengths
{', '.join(self.strengths) if self.strengths else 'Not specified'}

### Areas to Address
{', '.join(self.gaps) if self.gaps else 'None identified'}"""


@dataclass
class SessionClaim:
    """A claim made during an interview session for consistency tracking."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    claim_text: str = ""  # The actual text containing the claim
    claim_value: str = ""  # The extracted value (e.g., "8 years")
    claim_type: ClaimType = ClaimType.OTHER
    context: str = ""  # Surrounding context
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "claim_text": self.claim_text,
            "claim_value": self.claim_value,
            "claim_type": self.claim_type.value if isinstance(self.claim_type, ClaimType) else self.claim_type,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionClaim":
        timestamp = data.get("timestamp")
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        claim_type = data.get("claim_type", "other")
        if isinstance(claim_type, str):
            try:
                claim_type = ClaimType(claim_type)
            except ValueError:
                claim_type = ClaimType.OTHER

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            session_id=data.get("session_id", ""),
            claim_text=data.get("claim_text", ""),
            claim_value=data.get("claim_value", ""),
            claim_type=claim_type,
            context=data.get("context", ""),
            timestamp=timestamp,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "SessionClaim":
        return cls.from_dict(json.loads(json_str))


@dataclass
class DocumentSummary:
    """Summary of an uploaded document."""
    document_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_type: DocumentType = DocumentType.OTHER
    filename: str = ""
    document_summary: str = ""  # ~200 words
    section_summaries: Dict[str, str] = field(default_factory=dict)  # section_name -> ~50 words each
    key_points: List[str] = field(default_factory=list)  # 5-10 bullet points
    uploaded_at: Optional[datetime] = None
    generated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type": self.document_type.value if isinstance(self.document_type, DocumentType) else self.document_type,
            "filename": self.filename,
            "document_summary": self.document_summary,
            "section_summaries": self.section_summaries,
            "key_points": self.key_points,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentSummary":
        uploaded_at = data.get("uploaded_at")
        if uploaded_at and isinstance(uploaded_at, str):
            uploaded_at = datetime.fromisoformat(uploaded_at)

        generated_at = data.get("generated_at")
        if generated_at and isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)

        doc_type = data.get("document_type", "other")
        if isinstance(doc_type, str):
            try:
                doc_type = DocumentType(doc_type)
            except ValueError:
                doc_type = DocumentType.OTHER

        return cls(
            document_id=data.get("document_id", str(uuid.uuid4())),
            document_type=doc_type,
            filename=data.get("filename", ""),
            document_summary=data.get("document_summary", ""),
            section_summaries=data.get("section_summaries", {}),
            key_points=data.get("key_points", []),
            uploaded_at=uploaded_at,
            generated_at=generated_at,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "DocumentSummary":
        return cls.from_dict(json.loads(json_str))
