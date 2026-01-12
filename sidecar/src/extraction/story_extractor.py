"""
STAR Story Extractor - Extract behavioral interview stories from resume.

Extracts:
- 8-12 STAR story candidates
- Complete S-T-A-R structure for each
- Tags for question matching
- Opening lines and compressed versions

Part of Phase 4: Interview Coach Evolution (STORY-056)
"""

import json
import logging
import re
import uuid
from datetime import datetime
from typing import Optional, List, Any, Dict

from src.memory.models import (
    STARStory,
    ExtractedFacts,
    Achievement,
    CareerEntry,
)


logger = logging.getLogger(__name__)


# Common story tags
STORY_TAGS = [
    "leadership", "conflict", "teamwork", "failure", "success",
    "scale", "innovation", "customer", "technical", "deadline",
    "learning", "mentoring", "cross_functional", "ambiguity",
    "problem_solving", "communication", "initiative", "adaptability"
]


# Story extraction prompt
STORY_EXTRACTION_PROMPT = """You are helping a job candidate prepare STAR stories for behavioral interviews.

Based on these career achievements and experience, identify 8-12 compelling STAR stories.

Career Information:
---
{career_info}
---

Achievements:
---
{achievements}
---

For EACH story, provide a complete JSON object with:
- title: A short memorable name like "The Migration Crisis" or "Scaling Under Pressure"
- situation: 2-3 sentences describing the context and challenge
- task: 1-2 sentences about your specific responsibility
- action: 3-5 sentences detailing the specific actions YOU took (use first person)
- result: 1-2 sentences with quantified outcomes (metrics, percentages, impact)
- metrics: Array of specific numbers/percentages from the story
- tags: Array from {tags}
- source_company: Company where this happened
- source_role: Role when this happened
- opening_line: An engaging first sentence to start this story (first person)
- twenty_second_version: The complete story compressed into 2-3 sentences
- confidence: 0.0-1.0 rating of how complete and usable this story is

IMPORTANT:
- Focus on achievements with quantifiable results
- Each story should demonstrate a different skill/competency
- Use first person ("I led...", "I designed...")
- Be specific about actions, not vague
- Include actual metrics where available

Return a JSON array of story objects:
[
  {{"title": "...", "situation": "...", ...}},
  ...
]"""


# Fallback prompt for generating stories from sparse data
SPARSE_STORY_PROMPT = """Based on this limited career information, generate 3-5 STAR story frameworks.
Even with limited data, create plausible story structures the candidate can flesh out.

Career Information:
{career_info}

Return JSON array of stories with the same structure, but mark confidence as 0.3-0.5 for incomplete stories."""


class StoryExtractor:
    """
    Extracts STAR-format stories from resume data.
    
    Uses LLM to identify and structure behavioral interview stories
    from career achievements and experience.
    """
    
    # Target number of stories
    MIN_STORIES = 3
    MAX_STORIES = 12
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        memory_store: Optional[Any] = None
    ):
        """
        Initialize the story extractor.
        
        Args:
            llm_provider: LLM provider for generating stories
            memory_store: Memory store for saving stories
        """
        self.llm_provider = llm_provider
        self.memory_store = memory_store
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set or update the LLM provider."""
        self.llm_provider = provider
    
    def set_memory_store(self, store: Any) -> None:
        """Set or update the memory store."""
        self.memory_store = store
    
    async def extract_stories(
        self,
        facts: ExtractedFacts,
        force_regenerate: bool = False
    ) -> List[STARStory]:
        """
        Extract STAR stories from extracted facts.
        
        Args:
            facts: Extracted facts from resume
            force_regenerate: If True, regenerate even if stories exist
            
        Returns:
            List of STARStory objects
        """
        # Check for existing stories
        if not force_regenerate and self.memory_store:
            existing = self.memory_store.get_all_stories()
            if existing:
                logger.info(f"Using {len(existing)} existing stories")
                return existing
        
        # Build context from facts
        career_info = self._format_career_info(facts)
        achievements_info = self._format_achievements(facts)
        
        # Determine if we have enough data
        has_rich_data = (
            len(facts.achievements) >= 3 or 
            len(facts.timeline) >= 2
        )
        
        # Extract stories
        if self.llm_provider:
            stories = await self._extract_with_llm(
                career_info, achievements_info, has_rich_data
            )
        else:
            logger.warning("No LLM provider, using basic story generation")
            stories = self._generate_basic_stories(facts)
        
        # Save stories to memory store
        if self.memory_store:
            for story in stories:
                self.memory_store.save_story(story)
            logger.info(f"Saved {len(stories)} stories to memory store")
        
        return stories
    
    async def _extract_with_llm(
        self,
        career_info: str,
        achievements_info: str,
        has_rich_data: bool
    ) -> List[STARStory]:
        """Extract stories using LLM."""
        # Select appropriate prompt
        if has_rich_data:
            prompt = STORY_EXTRACTION_PROMPT.format(
                career_info=career_info,
                achievements=achievements_info,
                tags=STORY_TAGS
            )
        else:
            prompt = SPARSE_STORY_PROMPT.format(career_info=career_info)
        
        # Collect response
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            # Parse stories
            stories = self._parse_llm_response(full_response)
            return stories
            
        except Exception as e:
            logger.error(f"LLM story extraction failed: {e}")
            return []
    
    def _parse_llm_response(self, response: str) -> List[STARStory]:
        """Parse LLM response into STARStory objects."""
        stories = []
        
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                
                for story_data in data:
                    if isinstance(story_data, dict):
                        story = self._dict_to_story(story_data)
                        if story:
                            stories.append(story)
            else:
                logger.warning("No JSON array found in LLM response")
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse stories JSON: {e}")
        
        return stories[:self.MAX_STORIES]
    
    def _dict_to_story(self, data: Dict[str, Any]) -> Optional[STARStory]:
        """Convert a dictionary to a STARStory object."""
        try:
            return STARStory(
                id=str(uuid.uuid4()),
                title=data.get("title", "Untitled Story"),
                situation=data.get("situation", ""),
                task=data.get("task", ""),
                action=data.get("action", ""),
                result=data.get("result", ""),
                metrics=data.get("metrics", []),
                tags=self._validate_tags(data.get("tags", [])),
                source_company=data.get("source_company", ""),
                source_role=data.get("source_role", ""),
                opening_line=data.get("opening_line", ""),
                twenty_second_version=data.get("twenty_second_version", ""),
                full_version=self._build_full_version(data),
                confidence=min(1.0, max(0.0, data.get("confidence", 0.5))),
                created_at=datetime.now(),
            )
        except Exception as e:
            logger.warning(f"Failed to create story: {e}")
            return None
    
    def _validate_tags(self, tags: List[str]) -> List[str]:
        """Validate and normalize story tags."""
        valid_tags = []
        for tag in tags:
            if isinstance(tag, str):
                normalized = tag.lower().strip().replace(" ", "_")
                if normalized in STORY_TAGS:
                    valid_tags.append(normalized)
                elif normalized:  # Keep custom tags too
                    valid_tags.append(normalized)
        return valid_tags[:10]  # Max 10 tags
    
    def _build_full_version(self, data: Dict[str, Any]) -> str:
        """Build a full narrative version of the story."""
        parts = []
        
        if data.get("situation"):
            parts.append(f"**Situation:** {data['situation']}")
        if data.get("task"):
            parts.append(f"**Task:** {data['task']}")
        if data.get("action"):
            parts.append(f"**Action:** {data['action']}")
        if data.get("result"):
            parts.append(f"**Result:** {data['result']}")
        
        return "\n\n".join(parts)
    
    def _format_career_info(self, facts: ExtractedFacts) -> str:
        """Format career timeline for prompt."""
        lines = []
        
        lines.append(f"Current Role: {facts.current_role} at {facts.current_company}")
        lines.append(f"Total Experience: {facts.total_experience_years} years")
        lines.append("")
        lines.append("Career Timeline:")
        
        for entry in facts.timeline[:5]:  # Top 5 positions
            end = entry.end_date or "Present"
            lines.append(f"- {entry.role} at {entry.company} ({entry.start_date} - {end})")
            for highlight in entry.highlights[:3]:
                lines.append(f"  * {highlight}")
            for metric in entry.metrics[:2]:
                lines.append(f"  * {metric}")
        
        return "\n".join(lines)
    
    def _format_achievements(self, facts: ExtractedFacts) -> str:
        """Format achievements for prompt."""
        lines = []
        
        for i, ach in enumerate(facts.achievements[:15], 1):
            lines.append(f"{i}. {ach.description}")
            if ach.metrics:
                lines.append(f"   Metrics: {', '.join(ach.metrics)}")
            if ach.context:
                lines.append(f"   Context: {ach.context}")
            if ach.tags:
                lines.append(f"   Tags: {', '.join(ach.tags)}")
        
        return "\n".join(lines) if lines else "No specific achievements extracted."
    
    def _generate_basic_stories(self, facts: ExtractedFacts) -> List[STARStory]:
        """Generate basic story frameworks without LLM."""
        stories = []
        
        # Create a story from each major achievement
        for i, ach in enumerate(facts.achievements[:8]):
            story = STARStory(
                id=str(uuid.uuid4()),
                title=self._generate_title(ach.description),
                situation=f"At {ach.context or 'my previous company'}, we faced a challenge.",
                task="I was responsible for addressing this situation.",
                action=ach.description,
                result=f"Result: {', '.join(ach.metrics) if ach.metrics else 'Positive outcome achieved.'}",
                metrics=ach.metrics,
                tags=ach.tags or self._infer_tags(ach.description),
                source_company=ach.context.split(" ")[0] if ach.context else "",
                opening_line=f"Let me tell you about when {ach.description[:50].lower()}...",
                twenty_second_version=ach.description,
                confidence=0.4,  # Lower confidence for basic extraction
                created_at=datetime.now(),
            )
            stories.append(story)
        
        # Create stories from career highlights
        for entry in facts.timeline[:3]:
            for highlight in entry.highlights[:2]:
                story = STARStory(
                    id=str(uuid.uuid4()),
                    title=self._generate_title(highlight),
                    situation=f"While working as {entry.role} at {entry.company}...",
                    task="I needed to address a key challenge.",
                    action=highlight,
                    result=f"Metrics: {', '.join(entry.metrics) if entry.metrics else 'Successfully delivered.'}",
                    metrics=entry.metrics,
                    tags=self._infer_tags(highlight),
                    source_company=entry.company,
                    source_role=entry.role,
                    opening_line=f"During my time at {entry.company}, {highlight[:40].lower()}...",
                    twenty_second_version=highlight,
                    confidence=0.3,
                    created_at=datetime.now(),
                )
                stories.append(story)
        
        return stories[:self.MAX_STORIES]
    
    def _generate_title(self, description: str) -> str:
        """Generate a story title from description."""
        # Extract key action verbs and nouns
        words = description.split()[:6]
        
        # Common title patterns
        if any(w.lower() in ["led", "managed", "coordinated"] for w in words):
            return "The Leadership Challenge"
        elif any(w.lower() in ["built", "designed", "created", "developed"] for w in words):
            return "Building the Solution"
        elif any(w.lower() in ["reduced", "improved", "optimized"] for w in words):
            return "The Optimization Story"
        elif any(w.lower() in ["migrated", "transformed", "modernized"] for w in words):
            return "The Transformation"
        elif any(w.lower() in ["scaled", "grew", "expanded"] for w in words):
            return "Scaling Up"
        else:
            return f"The {words[0].title()} Story" if words else "Untitled Story"
    
    def _infer_tags(self, text: str) -> List[str]:
        """Infer story tags from text."""
        tags = []
        text_lower = text.lower()
        
        tag_keywords = {
            "leadership": ["led", "managed", "team", "coordinated", "mentored"],
            "technical": ["built", "designed", "implemented", "developed", "architected"],
            "scale": ["scale", "million", "traffic", "users", "distributed"],
            "innovation": ["new", "innovative", "first", "pioneered", "introduced"],
            "problem_solving": ["solved", "fixed", "debugged", "resolved", "addressed"],
            "deadline": ["deadline", "urgent", "time-sensitive", "rapid", "fast"],
            "cross_functional": ["cross-functional", "teams", "stakeholders", "collaborated"],
            "customer": ["customer", "client", "user", "feedback"],
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags[:5]
    
    async def get_stories_for_question(
        self,
        question: str,
        question_type: str = "behavioral"
    ) -> List[STARStory]:
        """
        Get relevant stories for a behavioral question.
        
        Args:
            question: The interview question
            question_type: Type of question (behavioral, situational, etc.)
            
        Returns:
            List of relevant stories sorted by relevance
        """
        if not self.memory_store:
            return []
        
        all_stories = self.memory_store.get_all_stories()
        
        # Simple keyword matching for now
        # (Could be enhanced with embeddings later)
        question_lower = question.lower()
        
        # Map question keywords to tags
        keyword_to_tag = {
            "lead": "leadership",
            "manage": "leadership",
            "team": "teamwork",
            "conflict": "conflict",
            "disagree": "conflict",
            "fail": "failure",
            "mistake": "failure",
            "challenge": "problem_solving",
            "difficult": "problem_solving",
            "deadline": "deadline",
            "pressure": "deadline",
            "learn": "learning",
            "new": "adaptability",
            "change": "adaptability",
        }
        
        relevant_tags = []
        for keyword, tag in keyword_to_tag.items():
            if keyword in question_lower:
                relevant_tags.append(tag)
        
        # Score and sort stories
        scored_stories = []
        for story in all_stories:
            score = story.confidence  # Base score is confidence
            
            # Boost for matching tags
            matching_tags = len(set(story.tags) & set(relevant_tags))
            score += matching_tags * 0.2
            
            scored_stories.append((score, story))
        
        # Sort by score descending
        scored_stories.sort(key=lambda x: x[0], reverse=True)
        
        return [story for _, story in scored_stories[:5]]
