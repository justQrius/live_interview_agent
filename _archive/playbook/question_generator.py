"""
Playbook Question Generator - Generates tailored interview questions.

Generates 20+ interview questions across categories:
- Behavioral (6-8 questions)
- Technical (4-6 questions)
- Motivation (3-4 questions)
- Situational (3-4 questions)
- Curveball (2-3 questions)

Part of Phase 4: Interview Coach Evolution (STORY-059)
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Any, Dict

from ..memory.models import (
    ExtractedFacts,
    CandidateProfile,
    DocumentSummary,
    DocumentType,
)


logger = logging.getLogger(__name__)


class QuestionCategory(str, Enum):
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    MOTIVATION = "motivation"
    SITUATIONAL = "situational"
    CURVEBALL = "curveball"


class QuestionDifficulty(str, Enum):
    STANDARD = "standard"
    CHALLENGING = "challenging"
    CURVEBALL = "curveball"


class AnswerFramework(str, Enum):
    STAR = "STAR"
    CONCEPT_EXAMPLE = "Concept-Example"
    PASSION_FIT = "Passion-Fit"
    PROBLEM_SOLUTION = "Problem-Solution"
    DIRECT = "Direct"


class SeniorityLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"


@dataclass
class PlaybookQuestion:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question_text: str = ""
    category: QuestionCategory = QuestionCategory.BEHAVIORAL
    why_likely: str = ""
    jd_requirement: str = ""
    difficulty: QuestionDifficulty = QuestionDifficulty.STANDARD
    answer_framework: AnswerFramework = AnswerFramework.STAR
    tags: List[str] = field(default_factory=list)
    suggested_stories: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question_text": self.question_text,
            "category": self.category.value,
            "why_likely": self.why_likely,
            "jd_requirement": self.jd_requirement,
            "difficulty": self.difficulty.value,
            "answer_framework": self.answer_framework.value,
            "tags": self.tags,
            "suggested_stories": self.suggested_stories,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaybookQuestion":
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            question_text=data.get("question_text", ""),
            category=QuestionCategory(data.get("category", "behavioral")),
            why_likely=data.get("why_likely", ""),
            jd_requirement=data.get("jd_requirement", ""),
            difficulty=QuestionDifficulty(data.get("difficulty", "standard")),
            answer_framework=AnswerFramework(data.get("answer_framework", "STAR")),
            tags=data.get("tags", []),
            suggested_stories=data.get("suggested_stories", []),
            created_at=created_at,
        )


QUESTION_TEMPLATES = {
    QuestionCategory.BEHAVIORAL: [
        "Tell me about a time when you {competency}.",
        "Describe a situation where you had to {competency}.",
        "Give me an example of how you {competency}.",
        "Walk me through a challenging situation where you {competency}.",
        "Can you share an experience where you {competency}?",
    ],
    QuestionCategory.TECHNICAL: [
        "How would you approach {technical_problem}?",
        "Explain your experience with {technology}.",
        "Walk me through how you would design {system}.",
        "What's your approach to {technical_challenge}?",
        "How have you used {technology} in production?",
    ],
    QuestionCategory.MOTIVATION: [
        "Why are you interested in this role?",
        "What attracts you to {company}?",
        "Where do you see yourself in 5 years?",
        "What motivates you in your work?",
        "Why are you leaving your current position?",
    ],
    QuestionCategory.SITUATIONAL: [
        "How would you handle {situation}?",
        "What would you do if {scenario}?",
        "Imagine you're faced with {challenge}. How would you approach it?",
        "If you had to {task}, how would you prioritize?",
    ],
    QuestionCategory.CURVEBALL: [
        "What's the biggest mistake you've made professionally?",
        "Tell me about a project that failed.",
        "What's your greatest weakness?",
        "Describe a time when you disagreed with your manager.",
        "Why shouldn't we hire you?",
    ],
}


GENERATION_PROMPT = """Generate tailored interview questions for this candidate applying to this role.

## Candidate Profile
{candidate_profile}

## Job Requirements
{jd_requirements}

## Company Context
{company_info}

## Role Level
{role_level}

## Identified Gaps
{identified_gaps}

Generate questions in these categories with the specified counts:
- BEHAVIORAL (6-8 questions): Based on required competencies like leadership, teamwork, problem-solving
- TECHNICAL (4-6 questions): Based on required skills and technologies
- MOTIVATION (3-4 questions): About interest in company/role and career goals
- SITUATIONAL (3-4 questions): Hypothetical scenarios appropriate for {role_level} level
- CURVEBALL (2-3 questions): Targeting the identified gaps and potential weak spots

For EACH question, return a JSON object with:
- question_text: The actual interview question
- category: One of [behavioral, technical, motivation, situational, curveball]
- why_likely: Brief explanation of why an interviewer would ask this (1-2 sentences)
- jd_requirement: Which specific JD requirement or skill this tests
- difficulty: One of [standard, challenging, curveball]
- answer_framework: One of [STAR, Concept-Example, Passion-Fit, Problem-Solution, Direct]
- tags: Array of 2-4 relevant tags

IMPORTANT:
- Questions must be SPECIFIC to this candidate and role, not generic
- Reference actual technologies, skills, or requirements from the JD
- Curveball questions should probe genuine gaps between candidate and JD
- Adjust complexity based on role level (junior questions simpler, senior more strategic)

Return a JSON array of question objects:
[
  {{"question_text": "...", "category": "behavioral", ...}},
  ...
]
"""


CATEGORY_COUNTS = {
    QuestionCategory.BEHAVIORAL: (6, 8),
    QuestionCategory.TECHNICAL: (4, 6),
    QuestionCategory.MOTIVATION: (3, 4),
    QuestionCategory.SITUATIONAL: (3, 4),
    QuestionCategory.CURVEBALL: (2, 3),
}


class QuestionGenerator:
    MIN_QUESTIONS = 20
    MAX_QUESTIONS = 30
    
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
    
    async def generate(
        self,
        profile: Optional[CandidateProfile] = None,
        facts: Optional[ExtractedFacts] = None,
        jd_summary: Optional[DocumentSummary] = None,
        company_info: Optional[DocumentSummary] = None,
        role_level: SeniorityLevel = SeniorityLevel.MID,
        force_regenerate: bool = False,
    ) -> List[PlaybookQuestion]:
        """
        Generate tailored interview questions based on candidate and job context.
        
        Args:
            profile: Candidate profile with strengths and gaps
            facts: Extracted facts from resume
            jd_summary: Job description summary with requirements
            company_info: Optional company information
            role_level: Seniority level for question calibration
            force_regenerate: If True, regenerate even if cached
            
        Returns:
            List of PlaybookQuestion objects (20+ questions)
        """
        if self.llm_provider:
            questions = await self._generate_with_llm(
                profile, facts, jd_summary, company_info, role_level
            )
        else:
            logger.warning("No LLM provider, using template-based generation")
            questions = self._generate_from_templates(
                profile, facts, jd_summary, role_level
            )
        
        questions = self._deduplicate_questions(questions)
        questions = self._ensure_category_balance(questions)
        
        if len(questions) < self.MIN_QUESTIONS:
            additional = self._generate_fallback_questions(
                self.MIN_QUESTIONS - len(questions),
                role_level
            )
            questions.extend(additional)
        
        for q in questions:
            q.created_at = datetime.now()
        
        return questions[:self.MAX_QUESTIONS]
    
    async def _generate_with_llm(
        self,
        profile: Optional[CandidateProfile],
        facts: Optional[ExtractedFacts],
        jd_summary: Optional[DocumentSummary],
        company_info: Optional[DocumentSummary],
        role_level: SeniorityLevel,
    ) -> List[PlaybookQuestion]:
        profile_text = self._format_profile(profile, facts)
        jd_text = self._format_jd(jd_summary)
        company_text = self._format_company(company_info)
        gaps_text = self._format_gaps(profile)
        
        prompt = GENERATION_PROMPT.format(
            candidate_profile=profile_text,
            jd_requirements=jd_text,
            company_info=company_text,
            role_level=role_level.value,
            identified_gaps=gaps_text,
        )
        
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            questions = self._parse_llm_response(full_response)
            return questions
            
        except Exception as e:
            logger.error(f"LLM question generation failed: {e}")
            return self._generate_from_templates(profile, facts, jd_summary, role_level)
    
    def _parse_llm_response(self, response: str) -> List[PlaybookQuestion]:
        questions = []
        
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                
                for q_data in data:
                    if isinstance(q_data, dict) and q_data.get("question_text"):
                        try:
                            category = QuestionCategory(q_data.get("category", "behavioral"))
                        except ValueError:
                            category = QuestionCategory.BEHAVIORAL
                        
                        try:
                            difficulty = QuestionDifficulty(q_data.get("difficulty", "standard"))
                        except ValueError:
                            difficulty = QuestionDifficulty.STANDARD
                        
                        try:
                            framework = AnswerFramework(q_data.get("answer_framework", "STAR"))
                        except ValueError:
                            framework = self._infer_framework(category)
                        
                        question = PlaybookQuestion(
                            question_text=q_data.get("question_text", ""),
                            category=category,
                            why_likely=q_data.get("why_likely", ""),
                            jd_requirement=q_data.get("jd_requirement", ""),
                            difficulty=difficulty,
                            answer_framework=framework,
                            tags=q_data.get("tags", []),
                        )
                        questions.append(question)
            else:
                logger.warning("No JSON array found in LLM response")
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse questions JSON: {e}")
        
        return questions
    
    def _generate_from_templates(
        self,
        profile: Optional[CandidateProfile],
        facts: Optional[ExtractedFacts],
        jd_summary: Optional[DocumentSummary],
        role_level: SeniorityLevel,
    ) -> List[PlaybookQuestion]:
        questions = []
        
        competencies = self._extract_competencies(jd_summary)
        technologies = self._extract_technologies(facts, jd_summary)
        
        for i, comp in enumerate(competencies[:8]):
            template = QUESTION_TEMPLATES[QuestionCategory.BEHAVIORAL][i % len(QUESTION_TEMPLATES[QuestionCategory.BEHAVIORAL])]
            questions.append(PlaybookQuestion(
                question_text=template.format(competency=comp.lower()),
                category=QuestionCategory.BEHAVIORAL,
                why_likely=f"Tests {comp} which is listed in the job requirements.",
                jd_requirement=comp,
                difficulty=QuestionDifficulty.STANDARD,
                answer_framework=AnswerFramework.STAR,
                tags=["behavioral", comp.lower().replace(" ", "_")],
            ))
        
        for i, tech in enumerate(technologies[:6]):
            template = QUESTION_TEMPLATES[QuestionCategory.TECHNICAL][i % len(QUESTION_TEMPLATES[QuestionCategory.TECHNICAL])]
            questions.append(PlaybookQuestion(
                question_text=template.format(
                    technology=tech,
                    technical_problem=f"solving a {tech}-related challenge",
                    technical_challenge=f"optimizing {tech} performance",
                    system=f"a system using {tech}",
                ),
                category=QuestionCategory.TECHNICAL,
                why_likely=f"{tech} is a key requirement for this role.",
                jd_requirement=tech,
                difficulty=QuestionDifficulty.STANDARD,
                answer_framework=AnswerFramework.CONCEPT_EXAMPLE,
                tags=["technical", tech.lower().replace(" ", "_")],
            ))
        
        for template in QUESTION_TEMPLATES[QuestionCategory.MOTIVATION][:4]:
            company_name = "our company"
            if jd_summary and jd_summary.key_points:
                company_name = "this company"
            questions.append(PlaybookQuestion(
                question_text=template.format(company=company_name),
                category=QuestionCategory.MOTIVATION,
                why_likely="Standard motivation question to assess cultural fit.",
                jd_requirement="Cultural fit",
                difficulty=QuestionDifficulty.STANDARD,
                answer_framework=AnswerFramework.PASSION_FIT,
                tags=["motivation", "culture"],
            ))
        
        situations = self._generate_situational_scenarios(role_level)
        for situation in situations[:4]:
            template = QUESTION_TEMPLATES[QuestionCategory.SITUATIONAL][0]
            questions.append(PlaybookQuestion(
                question_text=template.format(situation=situation),
                category=QuestionCategory.SITUATIONAL,
                why_likely=f"Tests judgment and decision-making at {role_level.value} level.",
                jd_requirement="Problem solving",
                difficulty=QuestionDifficulty.CHALLENGING,
                answer_framework=AnswerFramework.PROBLEM_SOLUTION,
                tags=["situational", role_level.value],
            ))
        
        gaps = profile.gaps if profile else []
        for i, gap in enumerate(gaps[:3]):
            questions.append(PlaybookQuestion(
                question_text=f"How would you address your limited experience with {gap}?",
                category=QuestionCategory.CURVEBALL,
                why_likely=f"Probes potential weakness: {gap}",
                jd_requirement=gap,
                difficulty=QuestionDifficulty.CURVEBALL,
                answer_framework=AnswerFramework.DIRECT,
                tags=["curveball", "gap"],
            ))
        
        for template in QUESTION_TEMPLATES[QuestionCategory.CURVEBALL][:3 - len(gaps)]:
            questions.append(PlaybookQuestion(
                question_text=template,
                category=QuestionCategory.CURVEBALL,
                why_likely="Standard curveball to test self-awareness and honesty.",
                jd_requirement="Self-awareness",
                difficulty=QuestionDifficulty.CURVEBALL,
                answer_framework=AnswerFramework.STAR,
                tags=["curveball", "self_awareness"],
            ))
        
        return questions
    
    def _extract_competencies(self, jd_summary: Optional[DocumentSummary]) -> List[str]:
        default_competencies = [
            "led a team", "handled conflict", "managed stakeholders",
            "delivered under pressure", "overcame a technical challenge",
            "mentored others", "drove innovation", "improved a process"
        ]
        
        if not jd_summary or not jd_summary.key_points:
            return default_competencies
        
        competencies = []
        competency_keywords = {
            "leadership": "led a team or project",
            "collaboration": "collaborated with cross-functional teams",
            "problem": "solved a complex problem",
            "communication": "communicated with stakeholders",
            "deadline": "delivered under tight deadlines",
            "mentor": "mentored junior team members",
            "innovation": "introduced an innovative solution",
            "scale": "scaled a system or process",
        }
        
        for point in jd_summary.key_points:
            point_lower = point.lower()
            for keyword, competency in competency_keywords.items():
                if keyword in point_lower and competency not in competencies:
                    competencies.append(competency)
        
        while len(competencies) < 8:
            for dc in default_competencies:
                if dc not in competencies:
                    competencies.append(dc)
                    break
            else:
                break
        
        return competencies[:8]
    
    def _extract_technologies(
        self,
        facts: Optional[ExtractedFacts],
        jd_summary: Optional[DocumentSummary],
    ) -> List[str]:
        technologies = set()
        
        if facts:
            for skill in facts.skills[:10]:
                technologies.add(skill.name)
        
        if jd_summary:
            for point in jd_summary.key_points or []:
                tech_patterns = [
                    r'\b(Python|JavaScript|TypeScript|Java|C\+\+|Go|Rust|Ruby)\b',
                    r'\b(React|Angular|Vue|Node\.js|Django|Flask|Spring)\b',
                    r'\b(AWS|GCP|Azure|Kubernetes|Docker|Terraform)\b',
                    r'\b(PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch)\b',
                ]
                for pattern in tech_patterns:
                    matches = re.findall(pattern, point, re.IGNORECASE)
                    technologies.update(matches)
        
        return list(technologies)[:10]
    
    def _generate_situational_scenarios(self, role_level: SeniorityLevel) -> List[str]:
        level_scenarios = {
            SeniorityLevel.JUNIOR: [
                "you're stuck on a bug and your senior is unavailable",
                "you realize your code has a bug that went to production",
                "you disagree with a code review comment",
                "you need to learn a new technology quickly",
            ],
            SeniorityLevel.MID: [
                "two team members have conflicting approaches",
                "you need to push back on unrealistic deadlines",
                "you discover a security vulnerability in production",
                "requirements change significantly mid-sprint",
            ],
            SeniorityLevel.SENIOR: [
                "you need to make a critical architecture decision quickly",
                "your team is resistant to a necessary change",
                "you need to balance technical debt against feature delivery",
                "a junior engineer is struggling and affecting team velocity",
            ],
            SeniorityLevel.STAFF: [
                "two engineering teams have incompatible approaches",
                "you need to influence without direct authority",
                "leadership wants a direction you believe is wrong",
                "you need to deprecate a system that teams depend on",
            ],
            SeniorityLevel.LEAD: [
                "your team's morale is low after a failed project",
                "you need to deliver difficult feedback to an underperformer",
                "stakeholders have conflicting priorities",
                "you need to make a hiring decision between two strong candidates",
            ],
            SeniorityLevel.MANAGER: [
                "you need to let someone go for performance reasons",
                "your team disagrees with a company-wide policy",
                "budget cuts require reducing your team",
                "a high performer is about to leave",
            ],
        }
        
        return level_scenarios.get(role_level, level_scenarios[SeniorityLevel.MID])
    
    def _format_profile(
        self,
        profile: Optional[CandidateProfile],
        facts: Optional[ExtractedFacts],
    ) -> str:
        if profile and profile.profile_text:
            return profile.profile_text
        
        if facts:
            lines = [
                f"Current Role: {facts.current_role} at {facts.current_company}",
                f"Experience: {facts.total_experience_years} years",
                f"Skills: {', '.join(s.name for s in facts.skills[:10])}",
            ]
            return "\n".join(lines)
        
        return "Candidate profile not available."
    
    def _format_jd(self, jd_summary: Optional[DocumentSummary]) -> str:
        if not jd_summary:
            return "Job description not available."
        
        lines = [jd_summary.document_summary]
        if jd_summary.key_points:
            lines.append("\nKey Requirements:")
            for point in jd_summary.key_points[:10]:
                lines.append(f"- {point}")
        
        return "\n".join(lines)
    
    def _format_company(self, company_info: Optional[DocumentSummary]) -> str:
        if not company_info:
            return "Company information not available."
        
        return company_info.document_summary
    
    def _format_gaps(self, profile: Optional[CandidateProfile]) -> str:
        if not profile or not profile.gaps:
            return "No significant gaps identified."
        
        return ", ".join(profile.gaps)
    
    def _infer_framework(self, category: QuestionCategory) -> AnswerFramework:
        framework_map = {
            QuestionCategory.BEHAVIORAL: AnswerFramework.STAR,
            QuestionCategory.TECHNICAL: AnswerFramework.CONCEPT_EXAMPLE,
            QuestionCategory.MOTIVATION: AnswerFramework.PASSION_FIT,
            QuestionCategory.SITUATIONAL: AnswerFramework.PROBLEM_SOLUTION,
            QuestionCategory.CURVEBALL: AnswerFramework.STAR,
        }
        return framework_map.get(category, AnswerFramework.STAR)
    
    def _deduplicate_questions(self, questions: List[PlaybookQuestion]) -> List[PlaybookQuestion]:
        seen = set()
        unique = []
        
        for q in questions:
            normalized = q.question_text.lower().strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique.append(q)
        
        return unique
    
    def _ensure_category_balance(
        self,
        questions: List[PlaybookQuestion]
    ) -> List[PlaybookQuestion]:
        by_category: Dict[QuestionCategory, List[PlaybookQuestion]] = {
            cat: [] for cat in QuestionCategory
        }
        
        for q in questions:
            by_category[q.category].append(q)
        
        balanced = []
        for category, (min_count, max_count) in CATEGORY_COUNTS.items():
            category_qs = by_category.get(category, [])
            balanced.extend(category_qs[:max_count])
        
        return balanced
    
    def _generate_fallback_questions(
        self,
        count: int,
        role_level: SeniorityLevel,
    ) -> List[PlaybookQuestion]:
        fallback = [
            ("Tell me about yourself.", QuestionCategory.BEHAVIORAL),
            ("Why do you want this job?", QuestionCategory.MOTIVATION),
            ("What are your strengths?", QuestionCategory.BEHAVIORAL),
            ("Where do you see yourself in 5 years?", QuestionCategory.MOTIVATION),
            ("Describe a challenging project you worked on.", QuestionCategory.BEHAVIORAL),
            ("How do you stay current with technology trends?", QuestionCategory.TECHNICAL),
            ("How do you handle disagreements with colleagues?", QuestionCategory.SITUATIONAL),
            ("What's your approach to learning new technologies?", QuestionCategory.TECHNICAL),
        ]
        
        questions = []
        for text, category in fallback[:count]:
            questions.append(PlaybookQuestion(
                question_text=text,
                category=category,
                why_likely="Common interview question.",
                jd_requirement="General",
                difficulty=QuestionDifficulty.STANDARD,
                answer_framework=self._infer_framework(category),
                tags=["general"],
            ))
        
        return questions
    
    def get_questions_by_category(
        self,
        questions: List[PlaybookQuestion],
        category: QuestionCategory,
    ) -> List[PlaybookQuestion]:
        return [q for q in questions if q.category == category]
    
    def get_question_stats(
        self,
        questions: List[PlaybookQuestion],
    ) -> Dict[str, Any]:
        by_category = {}
        by_difficulty = {}
        
        for q in questions:
            cat = q.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            
            diff = q.difficulty.value
            by_difficulty[diff] = by_difficulty.get(diff, 0) + 1
        
        return {
            "total": len(questions),
            "by_category": by_category,
            "by_difficulty": by_difficulty,
        }
