"""
Candidate Profile Generator - Creates compact LLM-injectable profiles.

Generates a ~1000 token candidate profile from extracted facts and stories,
suitable for injection into every LLM prompt to maintain consistent context.

Part of Phase 4: Interview Coach Evolution (STORY-057)
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict

from memory.models import (
    CandidateProfile,
    ExtractedFacts,
    DocumentSummary,
    STARStory,
    SkillEntry,
    Achievement,
    SkillProficiency,
    DocumentType,
)


logger = logging.getLogger(__name__)


# Profile template for consistent formatting
PROFILE_TEMPLATE = """## Candidate Profile

**Current Role**: {current_role}
**Total Experience**: {total_years} years
**Industries**: {industries}

### Core Competencies
{skills_section}

### Career Trajectory
{career_section}

### Key Achievements
{achievements_section}

### Target Role
{target_role_section}

### Positioning
{positioning_statement}
"""


# Approximate tokens per character ratio (conservative estimate)
TOKENS_PER_CHAR = 0.25


class ProfileGenerator:
    """
    Generates compact candidate profiles for LLM prompt injection.
    
    Aggregates facts, summaries, and stories into a consistent ~1000 token
    profile that can be injected into every LLM call.
    """
    
    # Token limits
    MAX_TOKENS = 1000
    MAX_CHARS = int(MAX_TOKENS / TOKENS_PER_CHAR)  # ~4000 chars
    
    # Section limits
    MAX_SKILLS = 8
    MAX_ACHIEVEMENTS = 5
    MAX_CAREER_ENTRIES = 4
    MAX_STORIES = 3
    
    def __init__(
        self,
        memory_store: Optional[Any] = None
    ):
        """
        Initialize the profile generator.
        
        Args:
            memory_store: Memory store for retrieving and saving profiles
        """
        self.memory_store = memory_store
    
    def set_memory_store(self, store: Any) -> None:
        """Set or update the memory store."""
        self.memory_store = store
    
    def generate(
        self,
        facts: ExtractedFacts,
        summaries: Optional[List[DocumentSummary]] = None,
        stories: Optional[List[STARStory]] = None,
        target_role: str = "",
        target_company: str = "",
        force_regenerate: bool = False
    ) -> CandidateProfile:
        """
        Generate a candidate profile from extracted data.
        
        Args:
            facts: Extracted facts from resume and other documents
            summaries: Optional list of document summaries for context
            stories: Optional list of STAR stories for context
            target_role: Target job role (from JD)
            target_company: Target company name
            force_regenerate: If True, regenerate even if cached
            
        Returns:
            CandidateProfile with formatted profile_text
        """
        # Check cache first
        if not force_regenerate and self.memory_store:
            cached = self.memory_store.get_profile()
            if cached:
                logger.info("Using cached candidate profile")
                return cached
        
        # Extract and prioritize information
        top_skills = self._prioritize_skills(facts.skills, self.MAX_SKILLS)
        top_achievements = self._prioritize_achievements(facts.achievements, self.MAX_ACHIEVEMENTS)
        
        # Identify strengths and gaps
        strengths = self._identify_strengths(facts, stories)
        gaps = self._identify_gaps(facts, target_role) if target_role else []
        
        # Build sections
        skills_section = self._format_skills_section(top_skills)
        career_section = self._format_career_section(facts.timeline[:self.MAX_CAREER_ENTRIES])
        achievements_section = self._format_achievements_section(top_achievements)
        target_role_section = self._format_target_role_section(
            target_role, target_company, summaries
        )
        positioning_statement = self._generate_positioning_statement(
            facts, target_role, strengths
        )
        
        # Format profile text
        profile_text = PROFILE_TEMPLATE.format(
            current_role=facts.current_role or "Not specified",
            total_years=facts.total_experience_years,
            industries=", ".join(facts.industries[:4]) if facts.industries else "Not specified",
            skills_section=skills_section,
            career_section=career_section,
            achievements_section=achievements_section,
            target_role_section=target_role_section,
            positioning_statement=positioning_statement,
        )
        
        # Truncate if needed to stay under token limit
        profile_text = self._truncate_to_limit(profile_text)
        
        # Build source documents list
        source_docs = []
        if facts.document_id:
            source_docs.append(facts.document_id)
        if summaries:
            source_docs.extend([s.document_id for s in summaries])
        
        # Create profile object
        profile = CandidateProfile(
            id=str(uuid.uuid4()),
            profile_text=profile_text,
            current_role=facts.current_role,
            total_experience_years=facts.total_experience_years,
            core_skills=[s.name for s in top_skills],
            key_achievements=[a.description[:100] for a in top_achievements],
            target_role=target_role,
            target_company=target_company,
            strengths=strengths,
            gaps=gaps,
            generated_at=datetime.now(),
            source_documents=source_docs,
        )
        
        # Save to memory store
        if self.memory_store:
            self.memory_store.save_profile(profile)
            logger.info("Saved generated profile to memory store")
        
        return profile
    
    def get_profile_for_prompt(self) -> str:
        """
        Get the current profile text ready for LLM prompt injection.
        
        Returns:
            Profile text string, or empty string if no profile exists
        """
        if self.memory_store:
            profile = self.memory_store.get_profile()
            if profile:
                return profile.get_prompt_injection()
        return ""
    
    def regenerate_profile(
        self,
        target_role: str = "",
        target_company: str = ""
    ) -> Optional[CandidateProfile]:
        """
        Regenerate profile from stored facts.
        
        Useful when facts have been updated or target role has changed.
        
        Args:
            target_role: Target job role
            target_company: Target company name
            
        Returns:
            New CandidateProfile or None if no facts available
        """
        if not self.memory_store:
            logger.warning("No memory store available for regeneration")
            return None
        
        # Get all facts
        facts = self.memory_store.get_all_facts()
        if not facts or (not facts.skills and not facts.timeline):
            logger.warning("No facts available for profile generation")
            return None
        
        # Get summaries and stories
        summaries = self.memory_store.get_all_document_summaries()
        stories = self.memory_store.get_all_stories()
        
        return self.generate(
            facts=facts,
            summaries=summaries,
            stories=stories,
            target_role=target_role,
            target_company=target_company,
            force_regenerate=True
        )
    
    def _prioritize_skills(
        self,
        skills: List[SkillEntry],
        limit: int
    ) -> List[SkillEntry]:
        """
        Prioritize skills by proficiency and years of experience.
        
        Args:
            skills: List of skills to prioritize
            limit: Maximum number of skills to return
            
        Returns:
            Top skills sorted by priority
        """
        if not skills:
            return []
        
        # Score each skill
        scored_skills = []
        for skill in skills:
            score = 0
            
            # Proficiency score
            proficiency_scores = {
                SkillProficiency.EXPERT: 3,
                SkillProficiency.PROFICIENT: 2,
                SkillProficiency.FAMILIAR: 1,
                SkillProficiency.LEARNING: 0,
            }
            if isinstance(skill.proficiency, SkillProficiency):
                score += proficiency_scores.get(skill.proficiency, 1)
            else:
                # Handle string proficiency
                prof_str = str(skill.proficiency).lower()
                if "expert" in prof_str:
                    score += 3
                elif "proficient" in prof_str:
                    score += 2
                elif "familiar" in prof_str:
                    score += 1
            
            # Years bonus
            if skill.years:
                score += min(skill.years / 2, 3)  # Cap at 3 points
            
            # Context bonus (has usage context)
            if skill.context:
                score += 0.5
            
            scored_skills.append((score, skill))
        
        # Sort by score descending
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        
        return [skill for _, skill in scored_skills[:limit]]
    
    def _prioritize_achievements(
        self,
        achievements: List[Achievement],
        limit: int
    ) -> List[Achievement]:
        """
        Prioritize achievements by impact and metrics.
        
        Args:
            achievements: List of achievements to prioritize
            limit: Maximum number of achievements to return
            
        Returns:
            Top achievements sorted by priority
        """
        if not achievements:
            return []
        
        # Score each achievement
        scored_achievements = []
        for ach in achievements:
            score = 0
            
            # Metrics boost (has quantifiable impact)
            ach_metrics = ach.metrics or []
            score += len(ach_metrics) * 0.5
            
            # Tags boost
            ach_tags = ach.tags or []
            high_value_tags = ["leadership", "scale", "cost", "revenue"]
            matching_tags = len(set(ach_tags) & set(high_value_tags))
            score += matching_tags * 0.3
            
            # Impact level
            if ach.impact_level == "high":
                score += 2
            elif ach.impact_level == "medium":
                score += 1
            
            # Length bonus (more detailed is usually better)
            if len(ach.description) > 50:
                score += 0.5
            
            scored_achievements.append((score, ach))
        
        # Sort by score descending
        scored_achievements.sort(key=lambda x: x[0], reverse=True)
        
        return [ach for _, ach in scored_achievements[:limit]]
    
    def _identify_strengths(
        self,
        facts: ExtractedFacts,
        stories: Optional[List[STARStory]] = None
    ) -> List[str]:
        """
        Identify candidate strengths from facts and stories.
        
        Args:
            facts: Extracted facts
            stories: Optional STAR stories
            
        Returns:
            List of strength descriptions
        """
        strengths = []
        
        # Experience-based strengths
        if facts.total_experience_years >= 10:
            strengths.append("Extensive industry experience")
        elif facts.total_experience_years >= 5:
            strengths.append("Strong professional foundation")
        
        # Skill-based strengths
        expert_skills = [
            s for s in facts.skills 
            if s.proficiency == SkillProficiency.EXPERT or 
            (s.years and s.years >= 5)
        ]
        if len(expert_skills) >= 3:
            top_expert_names = [s.name for s in expert_skills[:3]]
            strengths.append(f"Expert-level proficiency in {', '.join(top_expert_names)}")
        
        # Achievement-based strengths
        leadership_achievements = [
            a for a in facts.achievements
            if "leadership" in (a.tags or []) or "led" in a.description.lower()
        ]
        if leadership_achievements:
            strengths.append("Proven leadership and team management")
        
        scale_achievements = [
            a for a in facts.achievements
            if "scale" in (a.tags or []) or any(m for m in (a.metrics or []) if "M" in m or "million" in m.lower())
        ]
        if scale_achievements:
            strengths.append("Experience building at scale")
        
        # Story-based strengths
        if stories:
            story_tags = set()
            for story in stories:
                story_tags.update(story.tags)
            
            if "problem_solving" in story_tags:
                strengths.append("Strong problem-solving abilities")
            if "innovation" in story_tags:
                strengths.append("Track record of innovation")
        
        return strengths[:5]  # Cap at 5 strengths
    
    def _identify_gaps(
        self,
        facts: ExtractedFacts,
        target_role: str
    ) -> List[str]:
        """
        Identify potential gaps based on target role.
        
        This is a simple heuristic - could be enhanced with JD matching later.
        
        Args:
            facts: Extracted facts
            target_role: Target job role
            
        Returns:
            List of potential gap areas
        """
        gaps = []
        target_lower = target_role.lower()
        
        # Check for common role requirements
        if "senior" in target_lower or "lead" in target_lower:
            if facts.total_experience_years < 5:
                gaps.append("May need to emphasize leadership experience")
        
        if "manager" in target_lower:
            has_management = any(
                "manage" in a.description.lower() or "led" in a.description.lower()
                for a in facts.achievements
            )
            if not has_management:
                gaps.append("Highlight any team leadership experience")
        
        # Keep gaps list short and actionable
        return gaps[:3]
    
    def _format_skills_section(self, skills: List[SkillEntry]) -> str:
        """Format skills for profile section."""
        if not skills:
            return "Skills information not available."
        
        lines = []
        for skill in skills:
            proficiency = skill.proficiency
            if isinstance(proficiency, SkillProficiency):
                prof_str = proficiency.value.capitalize()
            else:
                prof_str = str(proficiency).capitalize()
            
            if skill.years:
                lines.append(f"- **{skill.name}**: {prof_str} ({skill.years}+ years)")
            else:
                lines.append(f"- **{skill.name}**: {prof_str}")
        
        return "\n".join(lines)
    
    def _format_career_section(self, timeline: List) -> str:
        """Format career timeline for profile section."""
        if not timeline:
            return "Career history not available."
        
        lines = []
        for entry in timeline:
            end_date = entry.end_date or "Present"
            lines.append(f"- **{entry.role}** at {entry.company} ({entry.start_date} - {end_date})")
            
            # Add top highlights if available
            for highlight in entry.highlights[:2]:
                # Truncate long highlights
                if len(highlight) > 80:
                    highlight = highlight[:77] + "..."
                lines.append(f"  - {highlight}")
        
        return "\n".join(lines)
    
    def _format_achievements_section(self, achievements: List[Achievement]) -> str:
        """Format achievements for profile section."""
        if not achievements:
            return "No specific achievements documented."
        
        lines = []
        for ach in achievements:
            # Truncate long descriptions
            description = ach.description
            if len(description) > 120:
                description = description[:117] + "..."
            
            ach_metrics = ach.metrics or []
            if ach_metrics:
                metrics_str = ", ".join(ach_metrics[:2])
                lines.append(f"- {description} ({metrics_str})")
            else:
                lines.append(f"- {description}")
        
        return "\n".join(lines)
    
    def _format_target_role_section(
        self,
        target_role: str,
        target_company: str,
        summaries: Optional[List[DocumentSummary]] = None
    ) -> str:
        """Format target role section."""
        if not target_role:
            return "Target role not specified."
        
        lines = []
        
        if target_company:
            lines.append(f"Pursuing **{target_role}** at **{target_company}**")
        else:
            lines.append(f"Pursuing **{target_role}** position")
        
        # Add JD insights if available
        if summaries:
            jd_summaries = [
                s for s in summaries 
                if s.document_type == DocumentType.JOB_DESCRIPTION
            ]
            if jd_summaries and jd_summaries[0].key_points:
                lines.append("\nKey requirements to address:")
                for point in jd_summaries[0].key_points[:3]:
                    lines.append(f"- {point}")
        
        return "\n".join(lines)
    
    def _generate_positioning_statement(
        self,
        facts: ExtractedFacts,
        target_role: str,
        strengths: List[str]
    ) -> str:
        """Generate a brief positioning statement."""
        if not facts.current_role:
            return "Candidate positioning will be refined with more information."
        
        # Build a concise positioning statement
        parts = []
        
        # Current role context
        parts.append(f"Experienced {facts.current_role}")
        
        if facts.current_company:
            parts.append(f"currently at {facts.current_company}")
        
        # Experience
        if facts.total_experience_years:
            parts.append(f"with {facts.total_experience_years} years of experience")
        
        # Primary strength
        if strengths:
            parts.append(f"known for {strengths[0].lower()}")
        
        statement = " ".join(parts) + "."
        
        # Target context
        if target_role:
            statement += f" Well-positioned for {target_role} opportunities."
        
        return statement
    
    def _truncate_to_limit(self, text: str) -> str:
        """
        Truncate text to stay under token limit.
        
        Uses a conservative character limit as a proxy for tokens.
        
        Args:
            text: Profile text to truncate
            
        Returns:
            Truncated text
        """
        if len(text) <= self.MAX_CHARS:
            return text
        
        logger.warning(f"Profile text ({len(text)} chars) exceeds limit, truncating")
        
        # Find a good break point near the limit
        truncated = text[:self.MAX_CHARS]
        
        # Try to break at a paragraph boundary
        last_newline = truncated.rfind("\n\n")
        if last_newline > self.MAX_CHARS * 0.8:
            truncated = truncated[:last_newline]
        
        return truncated + "\n\n*[Profile truncated for token limit]*"
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for given text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return int(len(text) * TOKENS_PER_CHAR)
    
    def get_profile_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current profile.
        
        Returns:
            Dictionary with profile statistics
        """
        if not self.memory_store:
            return {"error": "No memory store available"}
        
        profile = self.memory_store.get_profile()
        if not profile:
            return {"error": "No profile generated"}
        
        return {
            "id": profile.id,
            "current_role": profile.current_role,
            "experience_years": profile.total_experience_years,
            "num_skills": len(profile.core_skills),
            "num_achievements": len(profile.key_achievements),
            "num_strengths": len(profile.strengths),
            "num_gaps": len(profile.gaps),
            "profile_chars": len(profile.profile_text),
            "estimated_tokens": self.estimate_tokens(profile.profile_text),
            "generated_at": profile.generated_at.isoformat() if profile.generated_at else None,
            "source_documents": len(profile.source_documents),
        }
