"""
Playbook Answer Drafter - Generates suggested answers for interview questions.

Generates answers that are:
- Grounded in user's resume/experience
- Use appropriate frameworks (STAR for behavioral, etc.)
- 100-200 words (45-90 seconds spoken)
- Include 3-5 key points with metrics

Part of Phase 4: Interview Coach Evolution (STORY-060)
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional, List, Any, Dict

from ..memory.models import (
    CandidateProfile,
    STARStory,
    DraftedAnswer,
    ExtractedFacts,
)
from .question_generator import (
    PlaybookQuestion,
    QuestionCategory,
    AnswerFramework,
)


logger = logging.getLogger(__name__)


FRAMEWORK_GUIDELINES = {
    AnswerFramework.STAR: {
        "name": "STAR Method",
        "structure": "Situation (15%) → Task (10%) → Action (60%) → Result (15%)",
        "tips": [
            "Start with a brief context (when, where, what challenge)",
            "Focus most time on YOUR specific actions",
            "End with quantified results and impact",
        ],
    },
    AnswerFramework.CONCEPT_EXAMPLE: {
        "name": "Concept-Example",
        "structure": "Explain Concept → Real Example → Trade-offs",
        "tips": [
            "Define the concept clearly first",
            "Give a concrete example from your experience",
            "Discuss pros/cons or considerations",
        ],
    },
    AnswerFramework.PASSION_FIT: {
        "name": "Passion-Fit",
        "structure": "Personal Interest → Company Alignment → Mutual Value",
        "tips": [
            "Show genuine enthusiasm",
            "Connect your values to company mission",
            "Explain what you bring and what you'll gain",
        ],
    },
    AnswerFramework.PROBLEM_SOLUTION: {
        "name": "Problem-Solution",
        "structure": "Context → Approach → Outcome",
        "tips": [
            "Describe the hypothetical situation clearly",
            "Walk through your thought process",
            "End with expected outcome and learnings",
        ],
    },
    AnswerFramework.DIRECT: {
        "name": "Direct Response",
        "structure": "Answer → Support → Close",
        "tips": [
            "Give a direct answer first",
            "Provide supporting evidence",
            "End with a forward-looking statement",
        ],
    },
}


ANSWER_PROMPT = """Generate a suggested interview answer for this question.

## Question
{question}

## Question Category
{category}

## Answer Framework
Use the {framework} framework:
{framework_structure}

## Candidate's Background
{candidate_context}

## Relevant STAR Story (if applicable)
{star_story}

## Requirements
1. Answer in first person ("I")
2. 100-200 words (45-90 seconds when spoken)
3. Use the {framework} framework structure
4. ONLY use facts from the provided context - do NOT invent details
5. Include specific metrics and numbers where available
6. Sound natural and conversational, not robotic
7. Avoid cliches like "team player", "go-getter", "passionate"

Return a JSON object with:
{{
  "suggested_answer": "The complete answer text...",
  "key_points": ["point 1", "point 2", "point 3"],
  "opening_line": "The suggested first sentence",
  "metrics_used": ["40% improvement", "$2M saved"]
}}
"""


BATCH_ANSWER_PROMPT = """Generate suggested interview answers for these questions.

## Candidate's Background
{candidate_context}

## Available STAR Stories
{stories_summary}

## Questions to Answer
{questions}

For EACH question, generate an answer following the specified framework.

Requirements for ALL answers:
1. First person ("I")
2. 100-200 words each
3. Use ONLY facts from candidate's background
4. Include metrics where available
5. Sound natural, avoid cliches

Return a JSON array:
[
  {{
    "question_id": "...",
    "suggested_answer": "...",
    "key_points": ["...", "...", "..."],
    "opening_line": "...",
    "story_id": "story_id or null",
    "metrics_used": ["..."]
  }},
  ...
]
"""


class AnswerDrafter:
    WORDS_PER_SECOND = 2.5
    MIN_WORDS = 100
    MAX_WORDS = 200
    MIN_KEY_POINTS = 3
    MAX_KEY_POINTS = 5
    
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
    
    async def draft_answer(
        self,
        question: PlaybookQuestion,
        profile: Optional[CandidateProfile] = None,
        stories: Optional[List[STARStory]] = None,
        facts: Optional[ExtractedFacts] = None,
    ) -> DraftedAnswer:
        relevant_story = None
        if question.category == QuestionCategory.BEHAVIORAL and stories:
            relevant_story = self._find_best_story(question, stories)
        
        candidate_context = self._build_candidate_context(profile, facts)
        story_context = self._format_story(relevant_story) if relevant_story else "No specific story selected."
        framework = question.answer_framework
        framework_info = FRAMEWORK_GUIDELINES.get(framework, FRAMEWORK_GUIDELINES[AnswerFramework.STAR])
        
        if self.llm_provider:
            answer = await self._generate_with_llm(
                question, candidate_context, story_context, framework, framework_info
            )
        else:
            logger.warning("No LLM provider, using template-based answer generation")
            answer = self._generate_template_answer(
                question, profile, relevant_story, framework
            )
        
        if relevant_story:
            answer.story_id = relevant_story.id
            answer.story_title = relevant_story.title
            answer.grounded_in.append(f"STAR Story: {relevant_story.title}")
        
        answer.question_id = question.id
        answer.framework_used = framework.value
        answer.word_count = len(answer.suggested_answer.split())
        answer.estimated_duration_seconds = int(answer.word_count / self.WORDS_PER_SECOND)
        answer.created_at = datetime.now()
        
        return answer
    
    async def draft_answers_batch(
        self,
        questions: List[PlaybookQuestion],
        profile: Optional[CandidateProfile] = None,
        stories: Optional[List[STARStory]] = None,
        facts: Optional[ExtractedFacts] = None,
    ) -> List[DraftedAnswer]:
        if not self.llm_provider or len(questions) <= 3:
            answers = []
            for q in questions:
                answer = await self.draft_answer(q, profile, stories, facts)
                answers.append(answer)
            return answers
        
        candidate_context = self._build_candidate_context(profile, facts)
        stories_summary = self._format_stories_summary(stories) if stories else "No stories available."
        questions_text = self._format_questions_for_batch(questions)
        
        prompt = BATCH_ANSWER_PROMPT.format(
            candidate_context=candidate_context,
            stories_summary=stories_summary,
            questions=questions_text,
        )
        
        full_response = ""
        try:
            async for chunk in self.llm_provider.generate_response(
                prompt=prompt,
                context="",
                history=[]
            ):
                full_response += chunk
            
            answers = self._parse_batch_response(full_response, questions, stories)
            return answers
            
        except Exception as e:
            logger.error(f"Batch answer generation failed: {e}")
            answers = []
            for q in questions:
                answer = await self.draft_answer(q, profile, stories, facts)
                answers.append(answer)
            return answers
    
    async def _generate_with_llm(
        self,
        question: PlaybookQuestion,
        candidate_context: str,
        story_context: str,
        framework: AnswerFramework,
        framework_info: Dict[str, Any],
    ) -> DraftedAnswer:
        prompt = ANSWER_PROMPT.format(
            question=question.question_text,
            category=question.category.value,
            framework=framework_info["name"],
            framework_structure=framework_info["structure"],
            candidate_context=candidate_context,
            star_story=story_context,
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
            logger.error(f"LLM answer generation failed: {e}")
            return self._generate_template_answer(question, None, None, framework)
    
    def _parse_llm_response(self, response: str) -> DraftedAnswer:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                key_points = data.get("key_points", [])[:self.MAX_KEY_POINTS]
                while len(key_points) < self.MIN_KEY_POINTS:
                    key_points.append("Key point to remember")
                
                return DraftedAnswer(
                    suggested_answer=data.get("suggested_answer", ""),
                    key_points=key_points,
                    opening_line=data.get("opening_line", ""),
                    metrics_used=data.get("metrics_used", []),
                    confidence=0.8,
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse answer JSON: {e}")
        
        return DraftedAnswer(
            suggested_answer=response[:500] if response else "",
            key_points=["Review and customize this answer"],
            confidence=0.3,
        )
    
    def _parse_batch_response(
        self,
        response: str,
        questions: List[PlaybookQuestion],
        stories: Optional[List[STARStory]],
    ) -> List[DraftedAnswer]:
        answers = []
        question_map = {q.id: q for q in questions}
        story_map = {s.id: s for s in stories} if stories else {}
        
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                data = json.loads(json_match.group())
                
                for answer_data in data:
                    if isinstance(answer_data, dict):
                        question_id = answer_data.get("question_id", "")
                        question = question_map.get(question_id)
                        
                        if not question:
                            continue
                        
                        key_points = answer_data.get("key_points", [])[:self.MAX_KEY_POINTS]
                        while len(key_points) < self.MIN_KEY_POINTS:
                            key_points.append("Key point to remember")
                        
                        story_id = answer_data.get("story_id")
                        story = story_map.get(story_id) if story_id else None
                        
                        answer = DraftedAnswer(
                            question_id=question_id,
                            suggested_answer=answer_data.get("suggested_answer", ""),
                            key_points=key_points,
                            opening_line=answer_data.get("opening_line", ""),
                            story_id=story_id,
                            story_title=story.title if story else None,
                            framework_used=question.answer_framework.value,
                            metrics_used=answer_data.get("metrics_used", []),
                            confidence=0.8,
                            created_at=datetime.now(),
                        )
                        answer.word_count = len(answer.suggested_answer.split())
                        answer.estimated_duration_seconds = int(answer.word_count / self.WORDS_PER_SECOND)
                        answers.append(answer)
                        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse batch answers JSON: {e}")
        
        answered_ids = {a.question_id for a in answers}
        for q in questions:
            if q.id not in answered_ids:
                answers.append(DraftedAnswer(
                    question_id=q.id,
                    suggested_answer="Answer generation failed. Please draft manually.",
                    key_points=["Draft your own answer"],
                    framework_used=q.answer_framework.value,
                    confidence=0.0,
                    created_at=datetime.now(),
                ))
        
        return answers
    
    def _find_best_story(
        self,
        question: PlaybookQuestion,
        stories: List[STARStory],
    ) -> Optional[STARStory]:
        if not stories:
            return None
        
        question_lower = question.question_text.lower()
        question_tags = set(question.tags)
        
        keyword_to_tag = {
            "lead": "leadership", "manage": "leadership", "team": "teamwork",
            "conflict": "conflict", "disagree": "conflict",
            "fail": "failure", "mistake": "failure", "wrong": "failure",
            "challenge": "problem_solving", "difficult": "problem_solving", "problem": "problem_solving",
            "deadline": "deadline", "pressure": "deadline", "urgent": "deadline",
            "learn": "learning", "new": "adaptability", "change": "adaptability",
            "mentor": "mentoring", "teach": "mentoring",
            "innovate": "innovation", "improve": "innovation", "create": "innovation",
            "scale": "scale", "grow": "scale",
            "customer": "customer", "client": "customer",
            "communicate": "communication", "present": "communication",
        }
        
        relevant_tags = set()
        for keyword, tag in keyword_to_tag.items():
            if keyword in question_lower:
                relevant_tags.add(tag)
        
        relevant_tags.update(question_tags)
        
        scored_stories = []
        for story in stories:
            score = story.confidence
            story_tags = set(story.tags)
            matching_tags = len(story_tags & relevant_tags)
            score += matching_tags * 0.25
            if story.metrics:
                score += 0.1 * min(len(story.metrics), 3)
            if story.opening_line:
                score += 0.05
            
            scored_stories.append((score, story))
        
        scored_stories.sort(key=lambda x: x[0], reverse=True)
        
        if scored_stories and scored_stories[0][0] > 0.3:
            return scored_stories[0][1]
        
        return None
    
    def _build_candidate_context(
        self,
        profile: Optional[CandidateProfile],
        facts: Optional[ExtractedFacts],
    ) -> str:
        if profile and profile.profile_text:
            return profile.profile_text
        
        if profile:
            return profile.get_prompt_injection()
        
        if facts:
            lines = [
                f"Current Role: {facts.current_role} at {facts.current_company}",
                f"Experience: {facts.total_experience_years} years",
                "",
                "Key Skills:",
            ]
            for skill in facts.skills[:10]:
                years_str = f" ({skill.years} years)" if skill.years else ""
                lines.append(f"- {skill.name}{years_str}")
            
            if facts.achievements:
                lines.append("")
                lines.append("Key Achievements:")
                for ach in facts.achievements[:5]:
                    metrics_str = f" [{', '.join(ach.metrics)}]" if ach.metrics else ""
                    lines.append(f"- {ach.description}{metrics_str}")
            
            return "\n".join(lines)
        
        return "Candidate background not available. Generate a generic answer structure."
    
    def _format_story(self, story: STARStory) -> str:
        return f"""**{story.title}**

Situation: {story.situation}
Task: {story.task}
Action: {story.action}
Result: {story.result}

Key Metrics: {', '.join(story.metrics) if story.metrics else 'None specified'}
Opening Line: {story.opening_line or 'Not specified'}"""
    
    def _format_stories_summary(self, stories: List[STARStory]) -> str:
        if not stories:
            return "No stories available."
        
        lines = []
        for story in stories[:10]:
            tags_str = ", ".join(story.tags[:5]) if story.tags else "general"
            lines.append(f"- [{story.id}] {story.title} (tags: {tags_str})")
        
        return "\n".join(lines)
    
    def _format_questions_for_batch(self, questions: List[PlaybookQuestion]) -> str:
        lines = []
        for i, q in enumerate(questions, 1):
            framework = FRAMEWORK_GUIDELINES.get(
                q.answer_framework,
                FRAMEWORK_GUIDELINES[AnswerFramework.STAR]
            )
            lines.append(f"""
{i}. Question ID: {q.id}
   Question: {q.question_text}
   Category: {q.category.value}
   Framework: {framework['name']} - {framework['structure']}
""")
        return "\n".join(lines)
    
    def _generate_template_answer(
        self,
        question: PlaybookQuestion,
        profile: Optional[CandidateProfile],
        story: Optional[STARStory],
        framework: AnswerFramework,
    ) -> DraftedAnswer:
        if story and framework == AnswerFramework.STAR:
            answer_text = f"""In my role at {story.source_company or 'my previous company'}, {story.situation.lower() if story.situation else 'I faced a challenging situation.'}

My responsibility was to {story.task.lower() if story.task else 'address this challenge effectively.'}

I took several key actions: {story.action if story.action else 'I analyzed the problem, developed a plan, and executed it systematically.'}

The result was significant: {story.result if story.result else 'We achieved our goals successfully.'} {f"Key metrics included {', '.join(story.metrics)}." if story.metrics else ''}"""
            
            key_points = [
                f"Context: {story.situation[:50]}..." if story.situation else "Set the context briefly",
                f"Your role: {story.task[:50]}..." if story.task else "Explain your specific responsibility",
                "Focus on YOUR actions (use 'I', not 'we')",
            ]
            if story.metrics:
                key_points.append(f"Metrics: {', '.join(story.metrics[:2])}")
            key_points.append("End with impact and learnings")
            
            return DraftedAnswer(
                suggested_answer=answer_text,
                key_points=key_points[:5],
                opening_line=story.opening_line or f"Let me share an experience from {story.source_company or 'my career'}.",
                confidence=0.6,
            )
        
        framework_info = FRAMEWORK_GUIDELINES.get(framework, FRAMEWORK_GUIDELINES[AnswerFramework.STAR])
        
        role = profile.current_role if profile else "my current role"
        experience = profile.total_experience_years if profile else "several"
        
        answer_text = f"""With {experience} years of experience in {role}, I can speak to this from direct experience.

{framework_info['tips'][0] if framework_info['tips'] else 'Let me provide context.'}

In my approach, I focus on understanding the core challenge first, then developing a structured plan to address it. I've found that clear communication and measurable goals are essential.

The outcomes have consistently been positive, with improvements in both efficiency and team satisfaction."""
        
        return DraftedAnswer(
            suggested_answer=answer_text,
            key_points=framework_info["tips"][:3] + ["Customize with your specific experience"],
            opening_line=f"Based on my {experience} years in {role}...",
            confidence=0.4,
        )
    
    def get_framework_guidance(self, framework: AnswerFramework) -> Dict[str, Any]:
        return FRAMEWORK_GUIDELINES.get(framework, FRAMEWORK_GUIDELINES[AnswerFramework.STAR])
