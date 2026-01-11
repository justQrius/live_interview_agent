"""
Answer Structure Suggester.

Provides real-time recommended answer structures (e.g. STAR, PREP)
based on the detected question type.

Part of Phase 4E: Interview Coaching (STORY-067)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


@dataclass
class StructureSection:
    name: str
    percentage: str
    description: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "percentage": self.percentage,
            "description": self.description
        }


@dataclass
class StructureHint:
    name: str
    sections: List[StructureSection]
    tips: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sections": [s.to_dict() for s in self.sections],
            "tips": self.tips
        }


class StructureSuggester:
    """
    Determines and provides the best answer structure for a question.
    """
    
    # Pre-defined structures
    STRUCTURES = {
        "behavioral": StructureHint(
            name="STAR Method",
            sections=[
                StructureSection("Situation", "15%", "Set the scene briefly"),
                StructureSection("Task", "10%", "Your specific responsibility"),
                StructureSection("Action", "60%", "What YOU did (be specific)"),
                StructureSection("Result", "15%", "Quantified outcome + learning"),
            ],
            tips=[
                "Focus on YOUR actions ('I', not 'We')",
                "Include at least one specific metric",
                "End with what you learned"
            ]
        ),
        "technical": StructureHint(
            name="Concept-Example-Tradeoff",
            sections=[
                StructureSection("Concept", "20%", "Explain the core idea"),
                StructureSection("Example", "50%", "Your real experience/application"),
                StructureSection("Tradeoffs", "30%", "Nuances, pros & cons"),
            ],
            tips=[
                "Start with a high-level definition",
                "Ground it in a real project you've built",
                "Show depth by discussing limitations"
            ]
        ),
        "motivation": StructureHint(
            name="Past-Future-Bridge",
            sections=[
                StructureSection("The Past", "30%", "What you've learned/achieved"),
                StructureSection("The Future", "30%", "What you're looking for now"),
                StructureSection("The Bridge", "40%", "Why this specific role fits"),
            ],
            tips=[
                "Connect your history to their mission",
                "Show research about the company",
                "Be authentic about your goals"
            ]
        ),
        "situational": StructureHint(
            name="Framework-Hypothesis",
            sections=[
                StructureSection("Clarify", "10%", "Ask scoping questions"),
                StructureSection("Framework", "20%", "How you'd approach it"),
                StructureSection("Hypothesis", "70%", "Your proposed solution steps"),
            ],
            tips=[
                "State your assumptions clearly",
                "Break the problem down first",
                "Think out loud as you solve"
            ]
        ),
        "general": StructureHint(
            name="Direct-Support-Close",
            sections=[
                StructureSection("Direct Answer", "20%", "Yes/No + Thesis"),
                StructureSection("Supporting Points", "60%", "2-3 reasons or examples"),
                StructureSection("Close", "20%", "Summary / Tie-back"),
            ],
            tips=[
                "Don't bury the lede - answer first",
                "Use 'first, second, third' structure",
                "Keep it concise"
            ]
        ),
    }
    
    def suggest_structure(self, question: str, classification_type: str) -> StructureHint:
        """
        Get the recommended structure for a question.
        
        Args:
            question: The question text
            classification_type: Type from QuestionDetector (e.g. interview_question)
            
        Returns:
            StructureHint object
        """
        subtype = self._detect_subtype(question, classification_type)
        return self.STRUCTURES.get(subtype, self.STRUCTURES["general"])
    
    def _detect_subtype(self, question: str, classification_type: str) -> str:
        """Classify question into subtypes (behavioral, technical, etc)."""
        text = question.lower()
        
        # Priority 1: Behavioral (Tell me about a time...)
        if any(p in text for p in [
            "tell me about", "describe a time", "give me an example", 
            "share an experience", "walk me through", "situation when"
        ]):
            return "behavioral"
            
        # Priority 2: Motivation (Why this role?)
        if any(p in text for p in [
            "why do you want", "why this role", "why us", "why are you leaving",
            "interested in", "passionate about", "career goals", "five years"
        ]):
            return "motivation"
            
        # Priority 3: Situational (Imagine if...)
        if any(p in text for p in [
            "imagine", "suppose", "hypothetically", "how would you handle",
            "what would you do if"
        ]):
            return "situational"
            
        # Priority 4: Technical (Design/How does X work?)
        # Use a broad list of technical keywords commonly found in system design/coding
        if any(p in text for p in [
            "design", "architecture", "database", "scale", "latency", "throughput",
            "algorithm", "complexity", "api", "microservices", "distributed",
            "cap theorem", "acid", "react", "python", "aws", "cloud", "docker",
            "kubernetes", "system", "code", "debug", "optimize", "cache"
        ]):
            return "technical"
            
        # Also check "What is" / "How does" for technical concepts
        if text.startswith(("what is", "how does", "explain")):
            # If it's short and contains technical-ish words, assume technical
            # This is heuristic and might catch general questions too
            return "technical"
            
        return "general"
