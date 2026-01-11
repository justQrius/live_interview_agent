"""
Competency Mapper - Maps job requirements to candidate experience.

Creates a structured mapping showing:
- Each JD requirement (must-have vs nice-to-have)
- Evidence from resume
- Match strength (strong/moderate/weak/gap)
- Mitigation suggestions for gaps

Part of Phase 4: Interview Coach Evolution (STORY-061)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any, Dict

from ..memory.models import (
    ExtractedFacts,
    DocumentSummary,
    DocumentType,
    SkillEntry,
    Achievement,
)


logger = logging.getLogger(__name__)


class RequirementType(str, Enum):
    TECHNICAL_SKILL = "technical_skill"
    SOFT_SKILL = "soft_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"
    OTHER = "other"


class MatchStrength(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    GAP = "gap"


@dataclass
class CompetencyMapping:
    requirement: str
    requirement_type: RequirementType = RequirementType.OTHER
    is_required: bool = True
    evidence: Optional[str] = None
    metrics: List[str] = field(default_factory=list)
    emphasis_points: List[str] = field(default_factory=list)
    match_strength: MatchStrength = MatchStrength.GAP
    mitigation: Optional[str] = None
    source_context: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement": self.requirement,
            "requirement_type": self.requirement_type.value,
            "is_required": self.is_required,
            "evidence": self.evidence,
            "metrics": self.metrics,
            "emphasis_points": self.emphasis_points,
            "match_strength": self.match_strength.value,
            "mitigation": self.mitigation,
            "source_context": self.source_context,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CompetencyMapping":
        return cls(
            requirement=data.get("requirement", ""),
            requirement_type=RequirementType(data.get("requirement_type", "other")),
            is_required=data.get("is_required", True),
            evidence=data.get("evidence"),
            metrics=data.get("metrics", []),
            emphasis_points=data.get("emphasis_points", []),
            match_strength=MatchStrength(data.get("match_strength", "gap")),
            mitigation=data.get("mitigation"),
            source_context=data.get("source_context"),
        )


@dataclass
class CompetencyReport:
    mappings: List[CompetencyMapping] = field(default_factory=list)
    total_requirements: int = 0
    strong_matches: int = 0
    moderate_matches: int = 0
    weak_matches: int = 0
    gaps: int = 0
    critical_gaps: List[str] = field(default_factory=list)
    generated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "total_requirements": self.total_requirements,
            "strong_matches": self.strong_matches,
            "moderate_matches": self.moderate_matches,
            "weak_matches": self.weak_matches,
            "gaps": self.gaps,
            "critical_gaps": self.critical_gaps,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
    
    def to_markdown_table(self) -> str:
        lines = [
            "| Requirement | Type | Required | Match | Evidence | Emphasis |",
            "|-------------|------|----------|-------|----------|----------|",
        ]
        
        for m in self.mappings:
            required = "✓" if m.is_required else "○"
            match_icon = {
                MatchStrength.STRONG: "🟢",
                MatchStrength.MODERATE: "🟡",
                MatchStrength.WEAK: "🟠",
                MatchStrength.GAP: "🔴",
            }.get(m.match_strength, "⚪")
            
            evidence = (m.evidence[:50] + "...") if m.evidence and len(m.evidence) > 50 else (m.evidence or "-")
            emphasis = ", ".join(m.emphasis_points[:2]) if m.emphasis_points else "-"
            
            lines.append(
                f"| {m.requirement[:40]} | {m.requirement_type.value} | {required} | {match_icon} | {evidence} | {emphasis} |"
            )
        
        return "\n".join(lines)


MAPPING_PROMPT = """Analyze how this candidate's experience maps to the job requirements.

## Job Requirements
{jd_requirements}

## Candidate Experience
{candidate_facts}

For EACH requirement, provide a mapping with:
1. requirement: The specific requirement from JD
2. requirement_type: One of [technical_skill, soft_skill, experience, education, certification, other]
3. is_required: true if must-have, false if nice-to-have
4. evidence: Specific experience/skill from resume that matches (null if gap)
5. metrics: Array of quantified achievements related to this requirement
6. emphasis_points: 2-3 key points to emphasize when discussing this
7. match_strength: One of [strong, moderate, weak, gap]
8. mitigation: For gaps/weak matches, suggest how to address in interview

Match strength guidelines:
- strong: Direct experience with metrics, 3+ years
- moderate: Related experience, 1-2 years, or indirect evidence
- weak: Minimal experience, only conceptual knowledge
- gap: No evidence found

Return a JSON array of mapping objects:
[
  {{"requirement": "...", "requirement_type": "...", ...}},
  ...
]
"""


MITIGATION_STRATEGIES = {
    RequirementType.TECHNICAL_SKILL: [
        "Highlight transferable skills from similar technologies",
        "Mention self-study, courses, or side projects",
        "Emphasize quick learning ability with examples",
        "Connect to fundamentals you do have expertise in",
    ],
    RequirementType.SOFT_SKILL: [
        "Provide examples from different contexts",
        "Discuss how you've developed this skill",
        "Reference feedback or recognition received",
    ],
    RequirementType.EXPERIENCE: [
        "Emphasize quality and impact over quantity",
        "Highlight intensive experiences that accelerated learning",
        "Connect adjacent experiences that provide similar skills",
    ],
    RequirementType.EDUCATION: [
        "Highlight equivalent practical experience",
        "Mention relevant certifications or courses",
        "Emphasize continuous learning and self-improvement",
    ],
    RequirementType.CERTIFICATION: [
        "Mention if currently pursuing or planned",
        "Highlight equivalent experience or training",
        "Reference related certifications you do have",
    ],
}


class CompetencyMapper:
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None,
    ):
        self.llm_provider = llm_provider
        self.memory_store = memory_store
    
    def set_llm_provider(self, provider: Any) -> None:
        self.llm_provider = provider
    
    def set_memory_store(self, store: Any) -> None:
        self.memory_store = store
    
    async def map_competencies(
        self,
        jd_summary: DocumentSummary,
        facts: ExtractedFacts,
        force_regenerate: bool = False,
    ) -> CompetencyReport:
        if self.llm_provider:
            mappings = await self._map_with_llm(jd_summary, facts)
        else:
            logger.warning("No LLM provider, using rule-based mapping")
            mappings = self._map_with_rules(jd_summary, facts)
        
        for mapping in mappings:
            if mapping.match_strength in (MatchStrength.GAP, MatchStrength.WEAK):
                if not mapping.mitigation:
                    mapping.mitigation = self._generate_mitigation(mapping)
        
        report = self._generate_report(mappings)
        report.generated_at = datetime.now()
        
        return report
    
    async def _map_with_llm(
        self,
        jd_summary: DocumentSummary,
        facts: ExtractedFacts,
    ) -> List[CompetencyMapping]:
        jd_text = self._format_jd_requirements(jd_summary)
        facts_text = self._format_candidate_facts(facts)
        
        prompt = MAPPING_PROMPT.format(
            jd_requirements=jd_text,
            candidate_facts=facts_text,
        )
        
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            return self._parse_llm_response(full_response)
            
        except Exception as e:
            logger.error(f"LLM competency mapping failed: {e}")
            return self._map_with_rules(jd_summary, facts)
    
    def _parse_llm_response(self, response: str) -> List[CompetencyMapping]:
        mappings = []
        
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                
                for item in data:
                    if isinstance(item, dict) and item.get("requirement"):
                        try:
                            req_type = RequirementType(item.get("requirement_type", "other"))
                        except ValueError:
                            req_type = RequirementType.OTHER
                        
                        try:
                            strength = MatchStrength(item.get("match_strength", "gap"))
                        except ValueError:
                            strength = MatchStrength.GAP
                        
                        mapping = CompetencyMapping(
                            requirement=item.get("requirement", ""),
                            requirement_type=req_type,
                            is_required=item.get("is_required", True),
                            evidence=item.get("evidence"),
                            metrics=item.get("metrics", []),
                            emphasis_points=item.get("emphasis_points", []),
                            match_strength=strength,
                            mitigation=item.get("mitigation"),
                        )
                        mappings.append(mapping)
                        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse competency mappings JSON: {e}")
        
        return mappings
    
    def _map_with_rules(
        self,
        jd_summary: DocumentSummary,
        facts: ExtractedFacts,
    ) -> List[CompetencyMapping]:
        mappings = []
        
        requirements = self._extract_requirements(jd_summary)
        
        skill_index = self._build_skill_index(facts)
        achievement_index = self._build_achievement_index(facts)
        
        for req_text, req_type, is_required in requirements:
            mapping = self._match_requirement(
                req_text, req_type, is_required,
                skill_index, achievement_index, facts
            )
            mappings.append(mapping)
        
        return mappings
    
    def _extract_requirements(
        self,
        jd_summary: DocumentSummary,
    ) -> List[tuple]:
        requirements = []
        
        if not jd_summary or not jd_summary.key_points:
            return requirements
        
        required_keywords = ["must", "required", "essential", "minimum", "need"]
        preferred_keywords = ["preferred", "nice to have", "plus", "bonus", "ideal"]
        
        technical_keywords = [
            "python", "java", "javascript", "typescript", "react", "node",
            "aws", "gcp", "azure", "kubernetes", "docker", "sql", "nosql",
            "api", "rest", "graphql", "microservices", "ci/cd", "git",
        ]
        
        soft_skill_keywords = [
            "communication", "leadership", "team", "collaborate", "mentor",
            "problem", "analytical", "interpersonal", "presentation",
        ]
        
        experience_keywords = ["years", "experience", "background", "track record"]
        education_keywords = ["degree", "bachelor", "master", "phd", "university"]
        
        for point in jd_summary.key_points:
            point_lower = point.lower()
            
            is_required = (
                any(kw in point_lower for kw in required_keywords) or
                not any(kw in point_lower for kw in preferred_keywords)
            )
            
            if any(kw in point_lower for kw in technical_keywords):
                req_type = RequirementType.TECHNICAL_SKILL
            elif any(kw in point_lower for kw in soft_skill_keywords):
                req_type = RequirementType.SOFT_SKILL
            elif any(kw in point_lower for kw in experience_keywords):
                req_type = RequirementType.EXPERIENCE
            elif any(kw in point_lower for kw in education_keywords):
                req_type = RequirementType.EDUCATION
            else:
                req_type = RequirementType.OTHER
            
            requirements.append((point, req_type, is_required))
        
        return requirements
    
    def _build_skill_index(self, facts: ExtractedFacts) -> Dict[str, SkillEntry]:
        index = {}
        for skill in facts.skills:
            index[skill.name.lower()] = skill
            words = skill.name.lower().split()
            for word in words:
                if len(word) > 2:
                    index[word] = skill
        return index
    
    def _build_achievement_index(self, facts: ExtractedFacts) -> Dict[str, Achievement]:
        index = {}
        for ach in facts.achievements:
            words = ach.description.lower().split()
            for word in words:
                if len(word) > 3:
                    index[word] = ach
            for tag in ach.tags:
                index[tag.lower()] = ach
        return index
    
    def _match_requirement(
        self,
        req_text: str,
        req_type: RequirementType,
        is_required: bool,
        skill_index: Dict[str, SkillEntry],
        achievement_index: Dict[str, Achievement],
        facts: ExtractedFacts,
    ) -> CompetencyMapping:
        req_words = set(re.findall(r'\b\w+\b', req_text.lower()))
        
        matched_skills = []
        for word in req_words:
            if word in skill_index:
                matched_skills.append(skill_index[word])
        
        matched_achievements = []
        for word in req_words:
            if word in achievement_index:
                matched_achievements.append(achievement_index[word])
        
        evidence = None
        metrics = []
        emphasis_points = []
        
        if matched_skills:
            best_skill = max(matched_skills, key=lambda s: s.years or 0)
            years_str = f" ({best_skill.years} years)" if best_skill.years else ""
            evidence = f"{best_skill.name}{years_str}"
            if best_skill.context:
                emphasis_points.append(f"Used at {best_skill.context}")
        
        if matched_achievements:
            best_ach = matched_achievements[0]
            if not evidence:
                evidence = best_ach.description[:100]
            metrics.extend(best_ach.metrics)
            emphasis_points.append(best_ach.description[:50])
        
        if matched_skills and any(s.years and s.years >= 3 for s in matched_skills):
            strength = MatchStrength.STRONG
        elif matched_skills or matched_achievements:
            if matched_achievements and matched_achievements[0].metrics:
                strength = MatchStrength.STRONG
            elif matched_skills and any(s.years and s.years >= 1 for s in matched_skills):
                strength = MatchStrength.MODERATE
            else:
                strength = MatchStrength.WEAK
        else:
            strength = MatchStrength.GAP
        
        return CompetencyMapping(
            requirement=req_text,
            requirement_type=req_type,
            is_required=is_required,
            evidence=evidence,
            metrics=metrics[:3],
            emphasis_points=emphasis_points[:3],
            match_strength=strength,
        )
    
    def _generate_mitigation(self, mapping: CompetencyMapping) -> str:
        strategies = MITIGATION_STRATEGIES.get(
            mapping.requirement_type,
            MITIGATION_STRATEGIES[RequirementType.OTHER] if RequirementType.OTHER in MITIGATION_STRATEGIES else ["Prepare to discuss transferable skills and learning ability"]
        )
        
        if mapping.match_strength == MatchStrength.GAP:
            return strategies[0] if strategies else "Acknowledge the gap and emphasize willingness to learn quickly."
        else:
            return strategies[1] if len(strategies) > 1 else strategies[0] if strategies else "Provide concrete examples."
    
    def _generate_report(self, mappings: List[CompetencyMapping]) -> CompetencyReport:
        strong = sum(1 for m in mappings if m.match_strength == MatchStrength.STRONG)
        moderate = sum(1 for m in mappings if m.match_strength == MatchStrength.MODERATE)
        weak = sum(1 for m in mappings if m.match_strength == MatchStrength.WEAK)
        gaps = sum(1 for m in mappings if m.match_strength == MatchStrength.GAP)
        
        critical_gaps = [
            m.requirement for m in mappings
            if m.match_strength == MatchStrength.GAP and m.is_required
        ]
        
        return CompetencyReport(
            mappings=mappings,
            total_requirements=len(mappings),
            strong_matches=strong,
            moderate_matches=moderate,
            weak_matches=weak,
            gaps=gaps,
            critical_gaps=critical_gaps,
        )
    
    def _format_jd_requirements(self, jd_summary: DocumentSummary) -> str:
        lines = [jd_summary.document_summary] if jd_summary.document_summary else []
        
        if jd_summary.key_points:
            lines.append("\nKey Requirements:")
            for i, point in enumerate(jd_summary.key_points, 1):
                lines.append(f"{i}. {point}")
        
        return "\n".join(lines)
    
    def _format_candidate_facts(self, facts: ExtractedFacts) -> str:
        lines = [
            f"Current Role: {facts.current_role} at {facts.current_company}",
            f"Total Experience: {facts.total_experience_years} years",
            "",
            "Skills:",
        ]
        
        for skill in facts.skills[:15]:
            years_str = f" - {skill.years} years" if skill.years else ""
            lines.append(f"- {skill.name}{years_str}")
        
        if facts.achievements:
            lines.append("")
            lines.append("Key Achievements:")
            for ach in facts.achievements[:10]:
                metrics_str = f" [{', '.join(ach.metrics)}]" if ach.metrics else ""
                lines.append(f"- {ach.description}{metrics_str}")
        
        if facts.education:
            lines.append("")
            lines.append("Education:")
            for edu in facts.education:
                lines.append(f"- {edu.degree} from {edu.institution}")
        
        if facts.certifications:
            lines.append("")
            lines.append("Certifications:")
            for cert in facts.certifications[:5]:
                lines.append(f"- {cert}")
        
        return "\n".join(lines)
    
    def get_gaps_summary(self, report: CompetencyReport) -> str:
        if not report.critical_gaps and report.gaps == 0:
            return "No significant gaps identified. Strong alignment with job requirements."
        
        lines = ["## Gap Analysis", ""]
        
        if report.critical_gaps:
            lines.append("### Critical Gaps (Must-Have Requirements)")
            for gap in report.critical_gaps:
                lines.append(f"- ⚠️ {gap}")
            lines.append("")
        
        non_critical_gaps = [
            m for m in report.mappings
            if m.match_strength == MatchStrength.GAP and not m.is_required
        ]
        
        if non_critical_gaps:
            lines.append("### Nice-to-Have Gaps")
            for m in non_critical_gaps:
                lines.append(f"- {m.requirement}")
            lines.append("")
        
        lines.append("### Mitigation Strategies")
        for m in report.mappings:
            if m.match_strength in (MatchStrength.GAP, MatchStrength.WEAK) and m.mitigation:
                lines.append(f"- **{m.requirement[:40]}**: {m.mitigation}")
        
        return "\n".join(lines)
