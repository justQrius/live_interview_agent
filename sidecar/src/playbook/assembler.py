"""
Playbook Assembler - Assembles and exports complete interview playbooks.

Combines all playbook components:
- Questions with drafted answers
- Competency mapping
- STAR stories
- Candidate profile
- Positioning statements
- Cheat sheet

Exports to: Markdown, JSON, PDF-ready HTML

Part of Phase 4: Interview Coach Evolution (STORY-062)
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Any, Dict

from ..memory.models import (
    CandidateProfile,
    STARStory,
    DraftedAnswer,
    ExtractedFacts,
    DocumentSummary,
)
from .question_generator import (
    PlaybookQuestion,
    QuestionCategory,
    AnswerFramework,
)
from .competency_mapper import (
    CompetencyReport,
    CompetencyMapping,
    MatchStrength,
)


logger = logging.getLogger(__name__)


@dataclass
class PositioningStatements:
    """Elevator pitches at different lengths."""
    pitch_20s: str = ""  # ~50 words
    pitch_60s: str = ""  # ~150 words
    pitch_2min: str = ""  # ~300 words
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pitch_20s": self.pitch_20s,
            "pitch_60s": self.pitch_60s,
            "pitch_2min": self.pitch_2min,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositioningStatements":
        return cls(
            pitch_20s=data.get("pitch_20s", ""),
            pitch_60s=data.get("pitch_60s", ""),
            pitch_2min=data.get("pitch_2min", ""),
        )


@dataclass
class CheatSheet:
    """One-page quick reference for interview day."""
    key_talking_points: List[str] = field(default_factory=list)  # 5-7 points
    top_stories: List[Dict[str, str]] = field(default_factory=list)  # [{title, one_liner}]
    top_metrics: List[str] = field(default_factory=list)  # 3-5 metrics
    questions_to_ask: List[str] = field(default_factory=list)  # 3-5 questions
    pitfalls_to_avoid: List[str] = field(default_factory=list)  # 3-5 warnings
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_talking_points": self.key_talking_points,
            "top_stories": self.top_stories,
            "top_metrics": self.top_metrics,
            "questions_to_ask": self.questions_to_ask,
            "pitfalls_to_avoid": self.pitfalls_to_avoid,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheatSheet":
        return cls(
            key_talking_points=data.get("key_talking_points", []),
            top_stories=data.get("top_stories", []),
            top_metrics=data.get("top_metrics", []),
            questions_to_ask=data.get("questions_to_ask", []),
            pitfalls_to_avoid=data.get("pitfalls_to_avoid", []),
        )
    
    def to_markdown(self) -> str:
        """Generate one-page cheat sheet in markdown."""
        lines = [
            "# Interview Cheat Sheet",
            "",
            "## Key Talking Points",
        ]
        for point in self.key_talking_points[:7]:
            lines.append(f"- {point}")
        
        lines.extend(["", "## Top Stories to Tell"])
        for story in self.top_stories[:3]:
            lines.append(f"- **{story.get('title', 'Story')}**: {story.get('one_liner', '')}")
        
        lines.extend(["", "## Metrics to Remember"])
        for metric in self.top_metrics[:5]:
            lines.append(f"- {metric}")
        
        lines.extend(["", "## Questions to Ask"])
        for q in self.questions_to_ask[:5]:
            lines.append(f"- {q}")
        
        if self.pitfalls_to_avoid:
            lines.extend(["", "## Pitfalls to Avoid"])
            for pitfall in self.pitfalls_to_avoid[:5]:
                lines.append(f"- ⚠️ {pitfall}")
        
        return "\n".join(lines)


@dataclass
class Playbook:
    """Complete interview playbook document."""
    id: str = ""
    title: str = ""  # "Interview Playbook: {role} at {company}"
    role: str = ""
    company: str = ""
    generated_at: Optional[datetime] = None
    
    # Core content
    positioning: Optional[PositioningStatements] = None
    competency_report: Optional[CompetencyReport] = None
    questions: List[PlaybookQuestion] = field(default_factory=list)
    answers: Dict[str, DraftedAnswer] = field(default_factory=dict)  # question_id -> answer
    stories: List[STARStory] = field(default_factory=list)
    profile: Optional[CandidateProfile] = None
    
    # Derived content
    questions_to_ask: List[str] = field(default_factory=list)  # 5-10 questions for interviewer
    cheat_sheet: Optional[CheatSheet] = None
    
    # Metadata
    total_questions: int = 0
    total_stories: int = 0
    coverage_score: float = 0.0  # How well requirements are covered (0-1)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "role": self.role,
            "company": self.company,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "positioning": self.positioning.to_dict() if self.positioning else None,
            "competency_report": self.competency_report.to_dict() if self.competency_report else None,
            "questions": [q.to_dict() for q in self.questions],
            "answers": {k: v.to_dict() for k, v in self.answers.items()},
            "stories": [s.to_dict() for s in self.stories],
            "profile": self.profile.to_dict() if self.profile else None,
            "questions_to_ask": self.questions_to_ask,
            "cheat_sheet": self.cheat_sheet.to_dict() if self.cheat_sheet else None,
            "total_questions": self.total_questions,
            "total_stories": self.total_stories,
            "coverage_score": self.coverage_score,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Playbook":
        generated_at = data.get("generated_at")
        if generated_at and isinstance(generated_at, str):
            generated_at = datetime.fromisoformat(generated_at)
        
        positioning = data.get("positioning")
        if positioning:
            positioning = PositioningStatements.from_dict(positioning)
        
        cheat_sheet = data.get("cheat_sheet")
        if cheat_sheet:
            cheat_sheet = CheatSheet.from_dict(cheat_sheet)
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            role=data.get("role", ""),
            company=data.get("company", ""),
            generated_at=generated_at,
            positioning=positioning,
            competency_report=None,  # Complex nested, skip for now
            questions=[PlaybookQuestion.from_dict(q) for q in data.get("questions", [])],
            answers={k: DraftedAnswer.from_dict(v) for k, v in data.get("answers", {}).items()},
            stories=[STARStory.from_dict(s) for s in data.get("stories", [])],
            profile=CandidateProfile.from_dict(data["profile"]) if data.get("profile") else None,
            questions_to_ask=data.get("questions_to_ask", []),
            cheat_sheet=cheat_sheet,
            total_questions=data.get("total_questions", 0),
            total_stories=data.get("total_stories", 0),
            coverage_score=data.get("coverage_score", 0.0),
        )


# Prompts for LLM generation
POSITIONING_PROMPT = """Generate positioning statements (elevator pitches) for this candidate.

## Candidate Profile
{profile}

## Target Role
{role} at {company}

## Key Strengths
{strengths}

## Key Achievements
{achievements}

Generate three versions of an elevator pitch:

1. **20-second pitch** (~50 words): Ultra-concise hook. Who you are, what you do, why you're perfect for this role.

2. **60-second pitch** (~150 words): Expanded version with 1-2 specific achievements and clear value proposition.

3. **2-minute pitch** (~300 words): Full story arc: background, key experiences, why this role, what you bring.

Requirements:
- First person ("I")
- Natural and conversational, not robotic
- Include specific metrics where available
- Tailored to the target role
- Avoid cliches ("passionate", "team player", "go-getter")

Return as JSON:
{{
  "pitch_20s": "...",
  "pitch_60s": "...",
  "pitch_2min": "..."
}}
"""


QUESTIONS_TO_ASK_PROMPT = """Generate thoughtful questions for the candidate to ask the interviewer.

## Target Role
{role} at {company}

## Job Description Key Points
{jd_points}

## Company Context
{company_info}

## Candidate's Gaps to Probe
{gaps}

Generate 5-10 questions that:
1. Show genuine interest and research about the company
2. Reveal important information about the role/team
3. Subtly address any gaps (turn them into learning opportunities)
4. Are appropriate for the interview stage
5. Are NOT about salary, benefits, or time off

Categories to cover:
- Role and team dynamics
- Growth and learning opportunities
- Company culture and values
- Technical challenges and projects
- Success metrics

Return as JSON array:
["Question 1?", "Question 2?", ...]
"""


class PlaybookAssembler:
    """Assembles complete interview playbooks from components."""
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
    ):
        self.llm_provider = llm_provider
    
    def set_llm_provider(self, provider: Any) -> None:
        self.llm_provider = provider
    
    async def assemble(
        self,
        questions: List[PlaybookQuestion],
        answers: List[DraftedAnswer],
        competency_report: Optional[CompetencyReport] = None,
        stories: Optional[List[STARStory]] = None,
        profile: Optional[CandidateProfile] = None,
        jd_summary: Optional[DocumentSummary] = None,
        company_info: Optional[DocumentSummary] = None,
        role: str = "",
        company: str = "",
    ) -> Playbook:
        """
        Assemble a complete playbook from all components.
        
        Args:
            questions: Generated interview questions
            answers: Drafted answers for questions
            competency_report: JD requirement mapping
            stories: STAR stories extracted from resume
            profile: Candidate profile
            jd_summary: Job description summary
            company_info: Company information
            role: Target role name
            company: Target company name
            
        Returns:
            Complete Playbook ready for export
        """
        import uuid
        
        # Build answer lookup
        answers_dict = {a.question_id: a for a in answers}
        
        # Infer role/company from profile if not provided
        if not role and profile:
            role = profile.target_role or "Target Role"
        if not company and profile:
            company = profile.target_company or "Target Company"
        
        # Generate positioning statements
        positioning = await self._generate_positioning(
            profile, role, company
        )
        
        # Generate questions to ask interviewer
        questions_to_ask = await self._generate_questions_to_ask(
            role, company, jd_summary, company_info,
            profile.gaps if profile else []
        )
        
        # Generate cheat sheet
        cheat_sheet = self._generate_cheat_sheet(
            profile, stories or [], competency_report, questions_to_ask
        )
        
        # Calculate coverage score
        coverage_score = self._calculate_coverage(competency_report)
        
        playbook = Playbook(
            id=str(uuid.uuid4()),
            title=f"Interview Playbook: {role} at {company}",
            role=role,
            company=company,
            generated_at=datetime.now(),
            positioning=positioning,
            competency_report=competency_report,
            questions=questions,
            answers=answers_dict,
            stories=stories or [],
            profile=profile,
            questions_to_ask=questions_to_ask,
            cheat_sheet=cheat_sheet,
            total_questions=len(questions),
            total_stories=len(stories) if stories else 0,
            coverage_score=coverage_score,
        )
        
        return playbook
    
    async def _generate_positioning(
        self,
        profile: Optional[CandidateProfile],
        role: str,
        company: str,
    ) -> PositioningStatements:
        """Generate elevator pitches."""
        if not profile:
            return self._template_positioning(role, company)
        
        if self.llm_provider:
            try:
                return await self._positioning_with_llm(profile, role, company)
            except Exception as e:
                logger.error(f"LLM positioning generation failed: {e}")
        
        return self._template_positioning(role, company, profile)
    
    async def _positioning_with_llm(
        self,
        profile: CandidateProfile,
        role: str,
        company: str,
    ) -> PositioningStatements:
        """Generate positioning with LLM."""
        strengths = ", ".join(profile.strengths[:5]) if profile.strengths else "Not specified"
        achievements = "\n".join(f"- {a}" for a in profile.key_achievements[:5]) if profile.key_achievements else "Not specified"
        
        prompt = POSITIONING_PROMPT.format(
            profile=profile.get_prompt_injection(),
            role=role,
            company=company,
            strengths=strengths,
            achievements=achievements,
        )
        
        full_response = ""
        async for chunk in self.llm_provider.generate_response(
            prompt=prompt,
            context="",
            history=[]
        ):
            full_response += chunk
        
        return self._parse_positioning_response(full_response, profile, role, company)
    
    def _parse_positioning_response(
        self,
        response: str,
        profile: Optional[CandidateProfile],
        role: str,
        company: str,
    ) -> PositioningStatements:
        """Parse LLM response for positioning statements."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return PositioningStatements(
                    pitch_20s=data.get("pitch_20s", ""),
                    pitch_60s=data.get("pitch_60s", ""),
                    pitch_2min=data.get("pitch_2min", ""),
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse positioning JSON: {e}")
        
        return self._template_positioning(role, company, profile)
    
    def _template_positioning(
        self,
        role: str,
        company: str,
        profile: Optional[CandidateProfile] = None,
    ) -> PositioningStatements:
        """Generate template-based positioning statements."""
        if profile:
            current_role = profile.current_role or "experienced professional"
            years = profile.total_experience_years or "several"
            skills = ", ".join(profile.core_skills[:3]) if profile.core_skills else "relevant skills"
            achievement = profile.key_achievements[0] if profile.key_achievements else "driving impactful results"
        else:
            current_role = "experienced professional"
            years = "several"
            skills = "relevant skills"
            achievement = "driving impactful results"
        
        pitch_20s = f"I'm a {current_role} with {years} years of experience in {skills}. I'm excited about the {role} opportunity at {company} because it aligns perfectly with my background in {achievement}."
        
        pitch_60s = f"""I'm a {current_role} with {years} years of experience specializing in {skills}. 

In my career, I've focused on {achievement}. What excites me about the {role} position at {company} is the opportunity to bring this experience to a team that values innovation and impact.

I'm particularly drawn to how {company} approaches challenges in this space, and I believe my background would enable me to contribute meaningfully from day one."""
        
        pitch_2min = f"""I'm a {current_role} with {years} years of experience, currently focused on {skills}.

My career has been defined by a passion for {achievement}. I started my journey building foundational skills, and over time I've had the opportunity to tackle increasingly complex challenges.

One experience that stands out is when I took on a significant initiative that required both technical depth and cross-functional collaboration. The result was measurable impact that I'm proud of.

What draws me to the {role} position at {company} is the alignment between what I've been building toward and what your team is working on. I've researched how {company} approaches problems in this space, and I'm impressed by the thoughtfulness of your approach.

I believe I can contribute in several ways: bringing my experience with {skills}, applying lessons learned from previous challenges, and adding fresh perspective while learning from your team's expertise.

I'm genuinely excited about this opportunity and would love to discuss how my background could help {company} achieve its goals."""
        
        return PositioningStatements(
            pitch_20s=pitch_20s,
            pitch_60s=pitch_60s,
            pitch_2min=pitch_2min,
        )
    
    async def _generate_questions_to_ask(
        self,
        role: str,
        company: str,
        jd_summary: Optional[DocumentSummary],
        company_info: Optional[DocumentSummary],
        gaps: List[str],
    ) -> List[str]:
        """Generate questions for candidate to ask interviewer."""
        if self.llm_provider:
            try:
                return await self._questions_to_ask_with_llm(
                    role, company, jd_summary, company_info, gaps
                )
            except Exception as e:
                logger.error(f"LLM questions-to-ask generation failed: {e}")
        
        return self._template_questions_to_ask(role, company, gaps)
    
    async def _questions_to_ask_with_llm(
        self,
        role: str,
        company: str,
        jd_summary: Optional[DocumentSummary],
        company_info: Optional[DocumentSummary],
        gaps: List[str],
    ) -> List[str]:
        """Generate questions to ask with LLM."""
        jd_points = "\n".join(f"- {p}" for p in jd_summary.key_points[:10]) if jd_summary and jd_summary.key_points else "Not available"
        company_context = company_info.document_summary if company_info else "Not available"
        gaps_str = ", ".join(gaps[:5]) if gaps else "No significant gaps"
        
        prompt = QUESTIONS_TO_ASK_PROMPT.format(
            role=role,
            company=company,
            jd_points=jd_points,
            company_info=company_context,
            gaps=gaps_str,
        )
        
        full_response = ""
        async for chunk in self.llm_provider.generate_response(
            prompt=prompt,
            context="",
            history=[]
        ):
            full_response += chunk
        
        return self._parse_questions_to_ask_response(full_response, role, company, gaps)
    
    def _parse_questions_to_ask_response(
        self,
        response: str,
        role: str,
        company: str,
        gaps: List[str],
    ) -> List[str]:
        """Parse LLM response for questions to ask."""
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                if isinstance(data, list) and all(isinstance(q, str) for q in data):
                    return data[:10]
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse questions-to-ask JSON: {e}")
        
        return self._template_questions_to_ask(role, company, gaps)
    
    def _template_questions_to_ask(
        self,
        role: str,
        company: str,
        gaps: List[str],
    ) -> List[str]:
        """Generate template questions to ask interviewer."""
        questions = [
            f"What does success look like for the {role} position in the first 90 days?",
            f"How would you describe the team culture at {company}?",
            "What are the biggest challenges the team is currently facing?",
            "How does the team approach professional development and learning?",
            "Can you tell me about a recent project the team is proud of?",
            "What's the typical career path for someone in this role?",
            "How does the team collaborate with other departments?",
            f"What excites you most about working at {company}?",
        ]
        
        # Add gap-related questions
        for gap in gaps[:2]:
            questions.append(
                f"I'm interested in growing my skills in {gap}. What opportunities exist for that?"
            )
        
        return questions[:10]
    
    def _generate_cheat_sheet(
        self,
        profile: Optional[CandidateProfile],
        stories: List[STARStory],
        competency_report: Optional[CompetencyReport],
        questions_to_ask: List[str],
    ) -> CheatSheet:
        """Generate one-page cheat sheet."""
        # Key talking points from profile
        talking_points = []
        if profile:
            if profile.current_role:
                talking_points.append(f"Current: {profile.current_role} ({profile.total_experience_years} years)")
            talking_points.extend(profile.strengths[:3])
            if profile.key_achievements:
                talking_points.append(f"Key achievement: {profile.key_achievements[0][:50]}...")
        
        # Add strong competency matches
        if competency_report:
            strong_matches = [
                m.requirement[:40] for m in competency_report.mappings
                if m.match_strength == MatchStrength.STRONG
            ][:2]
            for match in strong_matches:
                talking_points.append(f"Strong fit: {match}")
        
        # Top stories with one-liners
        top_stories = []
        sorted_stories = sorted(stories, key=lambda s: s.confidence, reverse=True)[:3]
        for story in sorted_stories:
            one_liner = story.twenty_second_version or story.result[:80] if story.result else "See full story"
            top_stories.append({
                "title": story.title,
                "one_liner": one_liner,
            })
        
        # Top metrics from stories and profile
        top_metrics = []
        for story in stories[:5]:
            top_metrics.extend(story.metrics[:2])
        if profile and profile.key_achievements:
            # Extract metrics from achievements
            for ach in profile.key_achievements[:3]:
                metrics = re.findall(r'\d+[%$K-Za-z]*|\$[\d,]+', ach)
                top_metrics.extend(metrics[:1])
        top_metrics = list(dict.fromkeys(top_metrics))[:5]  # Dedupe, keep order
        
        # Pitfalls based on gaps
        pitfalls = []
        if profile and profile.gaps:
            for gap in profile.gaps[:3]:
                pitfalls.append(f"Don't oversell experience with {gap}")
        if competency_report:
            for mapping in competency_report.mappings:
                if mapping.match_strength == MatchStrength.GAP and mapping.is_required:
                    pitfalls.append(f"Prepare mitigation for: {mapping.requirement[:30]}")
                    if len(pitfalls) >= 5:
                        break
        
        return CheatSheet(
            key_talking_points=talking_points[:7],
            top_stories=top_stories,
            top_metrics=top_metrics,
            questions_to_ask=questions_to_ask[:5],
            pitfalls_to_avoid=pitfalls[:5],
        )
    
    def _calculate_coverage(
        self,
        competency_report: Optional[CompetencyReport],
    ) -> float:
        """Calculate how well candidate covers JD requirements."""
        if not competency_report or not competency_report.mappings:
            return 0.0
        
        total = len(competency_report.mappings)
        weights = {
            MatchStrength.STRONG: 1.0,
            MatchStrength.MODERATE: 0.7,
            MatchStrength.WEAK: 0.3,
            MatchStrength.GAP: 0.0,
        }
        
        score = sum(
            weights.get(m.match_strength, 0) * (1.5 if m.is_required else 1.0)
            for m in competency_report.mappings
        )
        
        max_score = sum(1.5 if m.is_required else 1.0 for m in competency_report.mappings)
        
        return round(score / max_score, 2) if max_score > 0 else 0.0
    
    def export_markdown(self, playbook: Playbook) -> str:
        """Export playbook to Markdown format."""
        lines = [
            f"# {playbook.title}",
            f"Generated: {playbook.generated_at.strftime('%Y-%m-%d %H:%M') if playbook.generated_at else 'Unknown'}",
            "",
            "---",
            "",
        ]
        
        # Executive Summary / Positioning
        if playbook.positioning:
            lines.extend([
                "## Executive Summary",
                "",
                "### Your Positioning",
                "",
                "**20-Second Pitch:**",
                playbook.positioning.pitch_20s,
                "",
                "**60-Second Pitch:**",
                playbook.positioning.pitch_60s,
                "",
                "**2-Minute Pitch:**",
                playbook.positioning.pitch_2min,
                "",
                "---",
                "",
            ])
        
        # Competency Mapping
        if playbook.competency_report:
            lines.extend([
                "## Competency Mapping",
                "",
                f"**Coverage Score:** {playbook.coverage_score * 100:.0f}%",
                "",
                playbook.competency_report.to_markdown_table(),
                "",
                "---",
                "",
            ])
        
        # Question Bank by Category
        lines.extend([
            "## Question Bank",
            "",
            f"Total Questions: {playbook.total_questions}",
            "",
        ])
        
        for category in QuestionCategory:
            category_qs = [q for q in playbook.questions if q.category == category]
            if category_qs:
                lines.extend([
                    f"### {category.value.title()} Questions ({len(category_qs)})",
                    "",
                ])
                for i, q in enumerate(category_qs, 1):
                    lines.append(f"**Q{i}: {q.question_text}**")
                    lines.append(f"*Why likely:* {q.why_likely}")
                    lines.append(f"*Framework:* {q.answer_framework.value}")
                    
                    answer = playbook.answers.get(q.id)
                    if answer and answer.suggested_answer:
                        lines.append("")
                        lines.append("*Suggested Answer:*")
                        lines.append(f"> {answer.suggested_answer}")
                        if answer.key_points:
                            lines.append("")
                            lines.append("*Key Points:*")
                            for point in answer.key_points:
                                lines.append(f"- {point}")
                    lines.append("")
        
        lines.append("---")
        lines.append("")
        
        # STAR Story Bank
        if playbook.stories:
            lines.extend([
                "## STAR Story Bank",
                "",
                f"Total Stories: {playbook.total_stories}",
                "",
                "| Title | Tags | Metrics | Confidence |",
                "|-------|------|---------|------------|",
            ])
            for story in playbook.stories:
                tags = ", ".join(story.tags[:3]) if story.tags else "-"
                metrics = ", ".join(story.metrics[:2]) if story.metrics else "-"
                conf = f"{story.confidence * 100:.0f}%"
                lines.append(f"| {story.title[:30]} | {tags} | {metrics} | {conf} |")
            
            lines.extend(["", "### Story Details", ""])
            for story in playbook.stories:
                lines.append(f"#### {story.title}")
                lines.append("")
                lines.append(story.get_full_story())
                lines.append("")
            
            lines.extend(["---", ""])
        
        # Gap Analysis
        if playbook.competency_report:
            gap_mappings = [
                m for m in playbook.competency_report.mappings
                if m.match_strength in (MatchStrength.GAP, MatchStrength.WEAK)
            ]
            if gap_mappings:
                lines.extend([
                    "## Gap Analysis",
                    "",
                ])
                for m in gap_mappings:
                    icon = "🔴" if m.match_strength == MatchStrength.GAP else "🟠"
                    required = "(Required)" if m.is_required else "(Nice-to-have)"
                    lines.append(f"### {icon} {m.requirement[:50]} {required}")
                    if m.mitigation:
                        lines.append(f"*Mitigation:* {m.mitigation}")
                    lines.append("")
                
                lines.extend(["---", ""])
        
        # Questions to Ask
        if playbook.questions_to_ask:
            lines.extend([
                "## Questions to Ask the Interviewer",
                "",
            ])
            for i, q in enumerate(playbook.questions_to_ask, 1):
                lines.append(f"{i}. {q}")
            lines.extend(["", "---", ""])
        
        # Cheat Sheet
        if playbook.cheat_sheet:
            lines.append(playbook.cheat_sheet.to_markdown())
        
        return "\n".join(lines)
    
    def export_json(self, playbook: Playbook) -> str:
        """Export playbook to JSON format."""
        return playbook.to_json()
    
    def export_html(self, playbook: Playbook) -> str:
        """Export playbook to HTML format (for PDF generation)."""
        markdown_content = self.export_markdown(playbook)
        
        # Simple markdown to HTML conversion for key elements
        html_content = markdown_content
        
        # Headers
        html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html_content, flags=re.MULTILINE)
        
        # Bold and italic
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
        html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
        
        # Lists
        html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
        
        # Blockquotes
        html_content = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_content, flags=re.MULTILINE)
        
        # Horizontal rules
        html_content = re.sub(r'^---$', r'<hr>', html_content, flags=re.MULTILINE)
        
        # Paragraphs (simple)
        html_content = re.sub(r'\n\n', r'</p><p>', html_content)
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{playbook.title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 15px 0;
            background: #f8f9fa;
            padding: 10px 15px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{ background: #f2f2f2; }}
        hr {{ border: none; border-top: 1px solid #eee; margin: 30px 0; }}
        .cheat-sheet {{
            background: #fffacd;
            padding: 20px;
            border-radius: 8px;
            page-break-before: always;
        }}
        @media print {{
            body {{ font-size: 12pt; }}
            .cheat-sheet {{ page-break-before: always; }}
        }}
    </style>
</head>
<body>
    <p>{html_content}</p>
</body>
</html>"""
