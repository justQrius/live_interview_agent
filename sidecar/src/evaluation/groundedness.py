"""
Groundedness evaluation for RAG answers.

Provides RAGAS-style metrics for evaluating how well generated answers
are grounded in the provided context. Uses a lightweight LLM call
for semantic evaluation.

Key Metrics:
- Groundedness Score: How well claims in the answer are supported by context (0-1)
- Context Utilization: What percentage of provided context was actually used (0-1)
- Faithfulness: Whether the answer contradicts any context (boolean + details)
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GroundednessResult:
    """Result of groundedness evaluation."""
    
    # Overall groundedness score (0-1, where 1 = fully grounded)
    score: float
    
    # Individual claim assessments
    claims: List[Dict[str, Any]] = field(default_factory=list)
    
    # Number of claims found in the answer
    claim_count: int = 0
    
    # Number of claims supported by context
    supported_count: int = 0
    
    # Number of claims that appear fabricated
    unsupported_count: int = 0
    
    # Specific issues found (for debugging/improvement)
    issues: List[str] = field(default_factory=list)
    
    # Raw LLM response (for debugging)
    raw_response: Optional[str] = None
    
    # Evaluation latency in ms
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "claim_count": self.claim_count,
            "supported_count": self.supported_count,
            "unsupported_count": self.unsupported_count,
            "issues": self.issues,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ContextUtilizationResult:
    """Result of context utilization analysis."""
    
    # Percentage of context chunks that were referenced (0-1)
    utilization_rate: float
    
    # Which chunks were likely used
    used_chunks: List[int] = field(default_factory=list)
    
    # Which chunks were not referenced
    unused_chunks: List[int] = field(default_factory=list)
    
    # Overlap analysis
    overlap_details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "utilization_rate": self.utilization_rate,
            "used_chunk_count": len(self.used_chunks),
            "unused_chunk_count": len(self.unused_chunks),
            "used_chunks": self.used_chunks,
        }


# Prompt for groundedness evaluation (optimized for speed)
GROUNDEDNESS_EVAL_PROMPT = """You are a fact-checker evaluating if an interview answer is grounded in the provided context.

## Context (Source Documents)
{context}

## Answer to Evaluate
{answer}

## Task
Identify factual claims in the answer and check if each is supported by the context.

A "claim" is any specific statement about:
- Companies, roles, or job titles
- Dates, durations, or timeframes
- Metrics, percentages, or numbers
- Technologies, skills, or tools
- Achievements or outcomes
- Teams, projects, or responsibilities

For each claim, determine if it's:
- SUPPORTED: Directly stated or clearly implied in context
- UNSUPPORTED: Cannot be verified from context (potentially fabricated)
- PARTIAL: Some aspects supported, others not

## Response Format (JSON only)
{{
  "claims": [
    {{"claim": "worked at Google for 3 years", "status": "SUPPORTED", "evidence": "Resume shows Google 2020-2023"}},
    {{"claim": "led a team of 15 engineers", "status": "UNSUPPORTED", "evidence": "Resume mentions 'team lead' but no team size"}}
  ],
  "overall_score": 0.85,
  "issues": ["Team size not verifiable from context"]
}}

Return ONLY valid JSON. No other text."""


class GroundednessEvaluator:
    """
    Evaluates answer groundedness using LLM-based semantic analysis.
    
    Designed for async, non-blocking evaluation that runs in the background
    after answer generation completes.
    """
    
    def __init__(
        self,
        llm_provider: Optional[Any] = None,
        fast_model: str = "gemini-2.0-flash-lite",
        timeout_seconds: float = 10.0,
    ):
        """
        Initialize the groundedness evaluator.
        
        Args:
            llm_provider: Optional LLM provider for evaluation calls.
                         If not provided, will attempt to use a lightweight model.
            fast_model: Model to use for evaluation (should be fast/cheap).
            timeout_seconds: Maximum time for evaluation before returning default.
        """
        self._llm_provider = llm_provider
        self._fast_model = fast_model
        self._timeout = timeout_seconds
        self._enabled = True
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set the LLM provider for evaluation calls."""
        self._llm_provider = provider
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable evaluation."""
        self._enabled = enabled
    
    async def evaluate_groundedness(
        self,
        answer: str,
        context: str,
        question: Optional[str] = None,
    ) -> GroundednessResult:
        """
        Evaluate how well an answer is grounded in the provided context.
        
        This is designed to run asynchronously in the background after
        answer generation, so it doesn't add latency to the user experience.
        
        Args:
            answer: The generated answer to evaluate.
            context: The context that was provided to the LLM.
            question: Optional - the original question (for context).
            
        Returns:
            GroundednessResult with scores and claim analysis.
        """
        import time
        start_time = time.time()
        
        # Quick validation
        if not answer or not context:
            return GroundednessResult(
                score=1.0 if not answer else 0.0,
                issues=["Empty answer or context"],
            )
        
        if not self._enabled:
            return GroundednessResult(
                score=-1.0,  # Indicates evaluation was skipped
                issues=["Evaluation disabled"],
            )
        
        try:
            result = await asyncio.wait_for(
                self._evaluate_with_llm(answer, context),
                timeout=self._timeout
            )
            result.latency_ms = (time.time() - start_time) * 1000
            return result
            
        except asyncio.TimeoutError:
            logger.warning(f"Groundedness evaluation timed out after {self._timeout}s")
            return GroundednessResult(
                score=-1.0,
                issues=["Evaluation timed out"],
                latency_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            logger.error(f"Groundedness evaluation failed: {e}")
            return GroundednessResult(
                score=-1.0,
                issues=[f"Evaluation error: {str(e)}"],
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    async def _evaluate_with_llm(
        self,
        answer: str,
        context: str,
    ) -> GroundednessResult:
        """
        Perform LLM-based groundedness evaluation.
        
        Uses a fast, cheap model to analyze claims in the answer.
        """
        if not self._llm_provider:
            # Fallback to heuristic evaluation if no LLM available
            return self._evaluate_heuristic(answer, context)
        
        prompt = GROUNDEDNESS_EVAL_PROMPT.format(
            context=context[:8000],  # Limit context size for speed
            answer=answer[:2000],    # Limit answer size
        )
        
        try:
            # Use generate_answer for simpler interface (non-streaming)
            if hasattr(self._llm_provider, 'generate_answer'):
                response = await self._llm_provider.generate_answer(
                    prompt=prompt,
                    context="",  # Context already in prompt
                    history=[],
                )
            else:
                # Fallback: collect streaming response
                response_parts = []
                async for chunk in self._llm_provider.generate_response(
                    prompt=prompt,
                    context="",
                    history=[],
                ):
                    response_parts.append(chunk)
                response = "".join(response_parts)
            
            return self._parse_evaluation_response(response)
            
        except Exception as e:
            logger.error(f"LLM evaluation call failed: {e}")
            # Fallback to heuristic
            return self._evaluate_heuristic(answer, context)
    
    def _parse_evaluation_response(self, response: str) -> GroundednessResult:
        """Parse the LLM's JSON response into a GroundednessResult."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            data = json.loads(json_match.group())
            
            claims = data.get("claims", [])
            supported = sum(1 for c in claims if c.get("status") == "SUPPORTED")
            unsupported = sum(1 for c in claims if c.get("status") == "UNSUPPORTED")
            
            # Use LLM's score if provided, otherwise calculate
            score = data.get("overall_score")
            if score is None:
                score = supported / len(claims) if claims else 1.0
            
            return GroundednessResult(
                score=float(score),
                claims=claims,
                claim_count=len(claims),
                supported_count=supported,
                unsupported_count=unsupported,
                issues=data.get("issues", []),
                raw_response=response,
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
            return GroundednessResult(
                score=-1.0,
                issues=[f"Parse error: {str(e)}"],
                raw_response=response,
            )
    
    def _evaluate_heuristic(
        self,
        answer: str,
        context: str,
    ) -> GroundednessResult:
        """
        Fast heuristic-based groundedness check (no LLM required).
        
        Uses text overlap and pattern matching for quick estimation.
        Less accurate than LLM but runs in <5ms.
        """
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        # Extract potential claims (numbers, proper nouns, etc.)
        number_pattern = r'\b\d+(?:\.\d+)?%?\b'
        answer_numbers = set(re.findall(number_pattern, answer))
        context_numbers = set(re.findall(number_pattern, context))
        
        # Check number grounding
        supported_numbers = answer_numbers & context_numbers
        unsupported_numbers = answer_numbers - context_numbers
        
        # Extract capitalized phrases (potential company/tech names)
        cap_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        answer_caps = set(re.findall(cap_pattern, answer))
        context_caps = set(re.findall(cap_pattern, context))
        
        # Exclude common words
        common_words = {"I", "The", "This", "That", "When", "What", "How", "Where", 
                       "In", "At", "For", "As", "My", "We", "Our", "They"}
        answer_caps -= common_words
        context_caps -= common_words
        
        supported_caps = answer_caps & context_caps
        unsupported_caps = answer_caps - context_caps
        
        # Calculate heuristic score
        total_claims = len(answer_numbers) + len(answer_caps)
        supported_claims = len(supported_numbers) + len(supported_caps)
        
        if total_claims == 0:
            score = 1.0  # No specific claims to verify
        else:
            score = supported_claims / total_claims
        
        issues = []
        if unsupported_numbers:
            issues.append(f"Unverified numbers: {unsupported_numbers}")
        if len(unsupported_caps) > 3:
            issues.append(f"Unverified entities: {list(unsupported_caps)[:5]}")
        
        return GroundednessResult(
            score=score,
            claim_count=total_claims,
            supported_count=supported_claims,
            unsupported_count=len(unsupported_numbers) + len(unsupported_caps),
            issues=issues,
        )
    
    def analyze_context_utilization(
        self,
        answer: str,
        context_chunks: List[str],
    ) -> ContextUtilizationResult:
        """
        Analyze how much of the provided context was actually used.
        
        This is a fast, synchronous check using text overlap.
        
        Args:
            answer: The generated answer.
            context_chunks: List of context chunks that were provided.
            
        Returns:
            ContextUtilizationResult with utilization metrics.
        """
        if not context_chunks:
            return ContextUtilizationResult(utilization_rate=1.0)
        
        answer_lower = answer.lower()
        answer_words = set(answer_lower.split())
        
        used_chunks = []
        unused_chunks = []
        overlap_details = []
        
        for i, chunk in enumerate(context_chunks):
            chunk_lower = chunk.lower()
            chunk_words = set(chunk_lower.split())
            
            # Calculate word overlap
            overlap = answer_words & chunk_words
            # Remove common words for more meaningful overlap
            stopwords = {"the", "a", "an", "is", "are", "was", "were", "i", "we", 
                        "to", "and", "of", "in", "for", "on", "with", "at", "by"}
            meaningful_overlap = overlap - stopwords
            
            overlap_ratio = len(meaningful_overlap) / len(chunk_words) if chunk_words else 0
            
            overlap_details.append({
                "chunk_index": i,
                "overlap_words": len(meaningful_overlap),
                "chunk_words": len(chunk_words),
                "overlap_ratio": round(overlap_ratio, 3),
            })
            
            # Consider chunk "used" if >10% meaningful word overlap
            if overlap_ratio > 0.10:
                used_chunks.append(i)
            else:
                unused_chunks.append(i)
        
        utilization_rate = len(used_chunks) / len(context_chunks)
        
        return ContextUtilizationResult(
            utilization_rate=utilization_rate,
            used_chunks=used_chunks,
            unused_chunks=unused_chunks,
            overlap_details=overlap_details,
        )
