"""
Query Reformulator for expanding follow-up questions into standalone queries.

Uses conversation history to resolve pronouns and references, making
follow-up questions self-contained for better RAG retrieval.

Enhanced with:
- TopicStack: Track topics across all conversation turns (not just last)
- Multi-turn anaphora resolution: Resolve "that/it/this" across N turns
- LLM fallback: When templates fail, use LLM for complex reformulation
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Patterns that indicate a follow-up question
FOLLOW_UP_INDICATORS = [
    r"^(what about|how about)\s+",
    r"^(and|also)\s+(what|how|why|when|where)",
    r"^(can you|could you)\s+(elaborate|expand|explain more|tell me more)",
    r"^(tell me more|go on|continue)",
    r"^(what were|what are)\s+the\s+(results?|outcomes?)\??$",
    r"\b(that|this|it)\s*\??$",  # Ends with pronoun + optional ?
    # New: Ordinal/positional references
    r"(the first|the second|the earlier|the previous|go back to)",
    # New: Pronouns mid-sentence
    r"\b(that project|that experience|that role|this approach|that system)\b",
]

# Templates for expanding follow-ups
EXPANSION_TEMPLATES = {
    r"^what about\s+(.+?)\??$": 
        "What is your experience with {match} in relation to {prev_topic}?",
    r"^how about\s+(.+?)\??$": 
        "How do you handle {match} based on your experience with {prev_topic}?",
    r"^can you elaborate\??$": 
        "Can you elaborate on {prev_topic}?",
    r"^could you elaborate\??$": 
        "Could you elaborate on {prev_topic}?",
    r"^can you expand( on that)?\??$": 
        "Can you expand on {prev_topic}?",
    r"^could you expand( on that)?\??$": 
        "Could you expand on {prev_topic}?",
    r"^can you explain more\??$": 
        "Can you explain more about {prev_topic}?",
    r"^could you explain more\??$": 
        "Could you explain more about {prev_topic}?",
    r"^tell me more\??$": 
        "Tell me more about {prev_topic}.",
    r"^go on\??$": 
        "Please continue explaining {prev_topic}.",
    r"^continue\??$": 
        "Please continue explaining {prev_topic}.",
    r"^(what were|what are) the results?\??$": 
        "What were the results of {prev_topic}?",
    r"^(what were|what are) the outcomes?\??$": 
        "What were the outcomes of {prev_topic}?",
    r"^and (what|how|why)\s+(.+)$":
        "{match2} regarding {prev_topic}?",
    r"^also,?\s+(what|how|why)\s+(.+)$":
        "{match2} regarding {prev_topic}?",
    # New: "Why?" / "How?" standalone
    r"^why\??$":
        "Why regarding {prev_topic}?",
    r"^how\??$":
        "How regarding {prev_topic}?",
}

# Patterns for detecting ordinal references
ORDINAL_PATTERNS = [
    (r"(the first|first) (one|topic|question|thing)", 0),
    (r"(the second|second) (one|topic|question|thing)", 1),
    (r"(the third|third) (one|topic|question|thing)", 2),
    (r"(go back to the first|back to the first)", 0),
    (r"(the earlier|earlier) (one|topic|question|thing)", -2),  # Second to last
    (r"(the previous|previous) (one|topic|question|thing)", -1),  # Last one
]

# Anaphora patterns - pronouns that need resolution
ANAPHORA_PATTERNS = [
    r"\bthat (project|experience|role|system|approach|situation|challenge|problem)\b",
    r"\bthis (project|experience|role|system|approach|situation|challenge|problem)\b",
    r"\bthe (project|experience|role|system|approach)\b",  # "the project" often refers back
]

# LLM prompt for reformulation fallback
LLM_REFORMULATION_PROMPT = """You are a query reformulator for an interview assistant. Your task is to expand a follow-up question into a standalone question that can be used for document retrieval.

Conversation history (most recent last):
{history}

Current follow-up question: "{question}"

Rewrite this as a single, self-contained question that:
1. Resolves all pronouns (it, that, this) to their referents from history
2. Includes enough context to be understood without the conversation
3. Preserves the intent of the original question
4. Is concise but complete

Return ONLY the reformulated question, nothing else."""


@dataclass
class TopicEntry:
    """A topic extracted from a conversation turn."""
    topic: str
    turn_index: int
    question: str  # Original question for keyword matching
    keywords: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        # Extract keywords for matching
        if not self.keywords:
            self.keywords = self._extract_keywords(self.question)
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Extract significant keywords from text."""
        # Remove common words and extract nouns/verbs
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'your', 'you',
            'me', 'my', 'tell', 'about', 'what', 'how', 'why', 'when',
            'where', 'which', 'who', 'describe', 'explain', 'with', 'and',
            'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'by',
        }
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        return [w for w in words if w not in stop_words]


class TopicStack:
    """
    Maintains a stack of topics across conversation turns.
    
    Enables resolution of:
    - Ordinal references: "the first topic", "go back to the earlier one"
    - Keyword-based references: "that project" matching a previous project discussion
    """
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self._topics: List[TopicEntry] = []
    
    def push(self, topic: str, question: str, turn_index: int) -> None:
        """Add a topic to the stack."""
        entry = TopicEntry(topic=topic, turn_index=turn_index, question=question)
        self._topics.append(entry)
        
        # Trim if exceeds max size
        if len(self._topics) > self.max_size:
            self._topics = self._topics[-self.max_size:]
    
    def get_by_index(self, index: int) -> Optional[TopicEntry]:
        """Get topic by ordinal index (0=first, -1=last)."""
        if not self._topics:
            return None
        try:
            return self._topics[index]
        except IndexError:
            return None
    
    def get_latest(self) -> Optional[TopicEntry]:
        """Get the most recent topic."""
        return self._topics[-1] if self._topics else None
    
    def find_by_keywords(self, keywords: List[str], exclude_last: bool = False) -> Optional[TopicEntry]:
        """
        Find a topic that matches the given keywords.
        
        Args:
            keywords: Keywords to match against topic keywords
            exclude_last: If True, don't consider the most recent topic
            
        Returns:
            Best matching TopicEntry or None
        """
        if not self._topics or not keywords:
            return None
        
        topics_to_search = self._topics[:-1] if exclude_last and len(self._topics) > 1 else self._topics
        
        best_match: Optional[TopicEntry] = None
        best_score = 0
        
        for entry in reversed(topics_to_search):  # Prefer recent matches
            # Count keyword overlap
            overlap = len(set(keywords) & set(entry.keywords))
            # Boost score for recency
            recency_boost = 0.1 * (entry.turn_index / max(1, len(self._topics)))
            score = overlap + recency_boost
            
            if score > best_score:
                best_score = score
                best_match = entry
        
        return best_match if best_score > 0 else None
    
    def clear(self) -> None:
        """Clear all topics."""
        self._topics.clear()
    
    def __len__(self) -> int:
        return len(self._topics)


class QueryReformulator:
    """
    Expands follow-up questions into standalone queries.
    
    Uses a tiered approach:
    - Tier 1: Template-based expansion (<5ms) for common patterns
    - Tier 2: TopicStack + multi-turn anaphora (<20ms) for complex references  
    - Tier 3: LLM fallback (~150ms) when rules fail
    
    Uses conversation history to resolve references and pronouns,
    creating self-contained questions that can be used for RAG retrieval.
    """
    
    def __init__(
        self, 
        context_turns: int = 5,
        llm_provider: Optional[Any] = None,
        enable_llm_fallback: bool = True
    ):
        """
        Initialize the QueryReformulator.
        
        Args:
            context_turns: Number of previous turns to consider for context.
            llm_provider: Optional LLM provider for Tier 3 fallback.
            enable_llm_fallback: Whether to use LLM when templates fail.
        """
        self.context_turns = context_turns
        self.llm_provider = llm_provider
        self.enable_llm_fallback = enable_llm_fallback
        self.topic_stack = TopicStack(max_size=context_turns * 2)
    
    def set_llm_provider(self, provider: Any) -> None:
        """Set or update the LLM provider for fallback reformulation."""
        self.llm_provider = provider
    
    def reformulate_if_needed(
        self,
        current_question: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> Tuple[str, bool]:
        """
        Expand follow-up questions into standalone questions.
        
        Uses tiered approach:
        1. Template-based expansion (fast path)
        2. TopicStack + multi-turn anaphora resolution
        3. Returns original if no expansion possible (LLM is async-only)
        
        Args:
            current_question: The question to potentially reformulate.
            conversation_history: List of previous exchanges, each with
                'question' and 'answer' keys.
                
        Returns:
            Tuple of (reformulated_question, was_reformulated)
        """
        # Handle edge cases
        if not current_question:
            return current_question, False
        
        current_question = current_question.strip()
        if not current_question:
            return current_question, False
        
        # Normalize history
        history = conversation_history or []
        
        # Build topic stack from history
        self._build_topic_stack(history)
        
        # Check if it's a follow-up
        if not self._is_follow_up(current_question):
            return current_question, False
        
        # Need history to reformulate
        if not history:
            return current_question, False
        
        # Tier 1: Check for ordinal references first ("the first topic", "go back to...")
        ordinal_result = self._resolve_ordinal_reference(current_question)
        if ordinal_result:
            logger.info(f"Tier 1 (ordinal): '{current_question}' → '{ordinal_result}'")
            return ordinal_result, True
        
        # Tier 2: Multi-turn anaphora resolution ("that project" from 3 turns ago)
        anaphora_result = self._resolve_multi_turn_anaphora(current_question, history)
        if anaphora_result and anaphora_result != current_question:
            logger.info(f"Tier 2 (anaphora): '{current_question}' → '{anaphora_result}'")
            return anaphora_result, True
        
        # Tier 1 (standard): Template-based expansion using last exchange
        last_exchange = self._get_last_valid_exchange(history)
        if last_exchange:
            prev_topic = self._extract_topic(last_exchange)
            expanded = self._expand_with_template(current_question, prev_topic)
            
            if expanded and expanded != current_question:
                logger.info(f"Tier 1 (template): '{current_question}' → '{expanded}'")
                return expanded, True
        
        return current_question, False
    
    async def reformulate_if_needed_async(
        self,
        current_question: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> Tuple[str, bool]:
        """
        Async version with LLM fallback for complex reformulation.
        
        Uses tiered approach:
        1. Template-based expansion (fast path)
        2. TopicStack + multi-turn anaphora resolution
        3. LLM fallback when rules fail and LLM is available
        
        Args:
            current_question: The question to potentially reformulate.
            conversation_history: List of previous exchanges.
                
        Returns:
            Tuple of (reformulated_question, was_reformulated)
        """
        # Try sync methods first
        result, was_reformulated = self.reformulate_if_needed(
            current_question, conversation_history
        )
        
        if was_reformulated:
            return result, True
        
        # If it's a follow-up but sync methods didn't work, try LLM
        if (
            self._is_follow_up(current_question) 
            and self.enable_llm_fallback 
            and self.llm_provider
            and conversation_history
        ):
            llm_result = await self._llm_reformulate(current_question, conversation_history)
            if llm_result and llm_result != current_question:
                logger.info(f"Tier 3 (LLM): '{current_question}' → '{llm_result}'")
                return llm_result, True
        
        return current_question, False
    
    def _build_topic_stack(self, history: List[Dict[str, str]]) -> None:
        """Build topic stack from conversation history."""
        self.topic_stack.clear()
        
        recent = history[-self.context_turns:] if len(history) > self.context_turns else history
        
        for i, exchange in enumerate(recent):
            if isinstance(exchange, dict) and exchange.get("question"):
                question = exchange["question"]
                topic = self._extract_topic(exchange)
                self.topic_stack.push(topic, question, i)
    
    def _resolve_ordinal_reference(self, question: str) -> Optional[str]:
        """
        Resolve ordinal references like "the first topic" or "go back to earlier".
        
        Returns reformulated question or None if no ordinal reference found.
        """
        question_lower = question.lower()
        
        for pattern, index in ORDINAL_PATTERNS:
            if re.search(pattern, question_lower, re.IGNORECASE):
                topic_entry = self.topic_stack.get_by_index(index)
                if topic_entry:
                    # Replace the ordinal reference with the actual topic
                    reformulated = re.sub(
                        pattern,
                        topic_entry.topic,
                        question,
                        flags=re.IGNORECASE
                    )
                    return reformulated
        
        return None
    
    def _resolve_multi_turn_anaphora(
        self, 
        question: str, 
        history: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Resolve anaphoric references that may refer to topics from N turns ago.
        
        Handles cases like "How did that project end?" where "that project"
        refers to a project mentioned 3 turns ago.
        
        Returns reformulated question or None.
        """
        question_lower = question.lower()
        
        # Check for anaphora patterns
        for pattern in ANAPHORA_PATTERNS:
            match = re.search(pattern, question_lower, re.IGNORECASE)
            if match:
                # Extract the noun being referenced (e.g., "project" from "that project")
                anaphora_text = match.group(0)  # e.g., "that project"
                noun = match.group(1)  # e.g., "project"
                
                # Search topic stack for matching topic
                topic_entry = self.topic_stack.find_by_keywords(
                    [noun], 
                    exclude_last=False
                )
                
                if topic_entry and topic_entry.topic != "your previous response":
                    # Replace anaphora with resolved reference
                    replacement = f"the {topic_entry.topic}"
                    reformulated = re.sub(
                        pattern,
                        replacement,
                        question,
                        count=1,
                        flags=re.IGNORECASE
                    )
                    return reformulated
        
        # Check for simple pronoun endings (existing behavior, but search deeper)
        if re.search(r"\b(that|this|it)\s*\??$", question_lower):
            # Try to find a relevant topic from stack (not just last)
            # Look for keywords in the current question to match against history
            question_keywords = TopicEntry._extract_keywords(question)
            
            if question_keywords:
                topic_entry = self.topic_stack.find_by_keywords(question_keywords)
                if topic_entry:
                    reformulated = re.sub(
                        r"\b(that|this|it)(\s*\??)$",
                        f"{topic_entry.topic}\\2",
                        question,
                        flags=re.IGNORECASE
                    )
                    return reformulated
        
        return None
    
    async def _llm_reformulate(
        self,
        question: str,
        history: List[Dict[str, str]]
    ) -> Optional[str]:
        """
        Use LLM to reformulate when templates fail.
        
        Args:
            question: The follow-up question
            history: Conversation history
            
        Returns:
            Reformulated question or None on failure
        """
        if not self.llm_provider:
            return None
        
        try:
            # Format history for prompt
            history_lines = []
            recent = history[-self.context_turns:]
            for exchange in recent:
                q = exchange.get("question", "")
                a = exchange.get("answer", "")[:200]  # Truncate long answers
                if q:
                    history_lines.append(f"Q: {q}")
                if a:
                    history_lines.append(f"A: {a}...")
            
            history_str = "\n".join(history_lines) if history_lines else "No previous history."
            
            prompt = LLM_REFORMULATION_PROMPT.format(
                history=history_str,
                question=question
            )
            
            # Generate response
            response_text = ""
            async for chunk in self.llm_provider.generate_response(prompt, "", []):
                response_text += chunk
                # Limit response length - we only need a short question
                if len(response_text) > 300:
                    break
            
            # Clean up response
            reformulated = response_text.strip()
            
            # Basic validation - should look like a question
            if reformulated and len(reformulated) > 10:
                # Remove any preamble the LLM might add
                if ":" in reformulated and reformulated.index(":") < 30:
                    reformulated = reformulated.split(":", 1)[1].strip()
                
                # Ensure it ends with ?
                if not reformulated.endswith("?"):
                    reformulated += "?"
                
                return reformulated
            
        except Exception as e:
            logger.warning(f"LLM reformulation failed: {e}")
        
        return None
    
    def _is_follow_up(self, text: str) -> bool:
        """
        Check if text is a follow-up question.
        
        Args:
            text: The question text.
            
        Returns:
            True if it matches follow-up patterns.
        """
        text_lower = text.lower().strip()
        
        for pattern in FOLLOW_UP_INDICATORS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def _get_last_valid_exchange(
        self,
        history: List[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Get the most recent exchange with a valid question.
        
        Args:
            history: List of conversation exchanges.
            
        Returns:
            Most recent valid exchange or None.
        """
        # Look through recent history (limited by context_turns)
        recent = history[-self.context_turns:] if len(history) > self.context_turns else history
        
        # Go through in reverse to find most recent valid
        for exchange in reversed(recent):
            if isinstance(exchange, dict) and exchange.get("question"):
                return exchange
        
        return None
    
    def _extract_topic(self, exchange: Dict[str, str]) -> str:
        """
        Extract the main topic from a conversation exchange.
        
        Enhanced with more patterns and fallback strategies.
        
        Args:
            exchange: Dictionary with 'question' and optionally 'answer'.
            
        Returns:
            Extracted topic string.
        """
        question = exchange.get("question", "")
        
        if not question:
            return "your previous response"
        
        # Pattern 1: "about X"
        match = re.search(r"about\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Pattern 2: "Tell me about/Describe/Explain X"
        match = re.search(
            r"^(?:tell me about|describe|explain|walk me through)\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # Pattern 3: "your X experience/skills"
        match = re.search(
            r"your\s+(.+?)\s+(experience|skills?|background|work|role|project)",
            question,
            re.IGNORECASE
        )
        if match:
            return f"your {match.group(1)} {match.group(2)}"
        
        # Pattern 4: "How do you X" / "What is your X" / "What was your X"
        match = re.search(
            r"(?:how do you|what (?:is|was|are|were) your)\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # Pattern 5: "experience with X" / "work on X"
        match = re.search(
            r"(?:experience with|work on|worked on|involvement in)\s+(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            return match.group(1).strip()
        
        # Pattern 6: "the X project/system/architecture"
        match = re.search(
            r"the\s+(\w+(?:\s+\w+)?)\s+(project|system|architecture|platform|service)",
            question,
            re.IGNORECASE
        )
        if match:
            return f"the {match.group(1)} {match.group(2)}"
        
        # Pattern 7: Extract noun phrases after question words
        match = re.search(
            r"(?:what|how|why|when|where)\s+(?:is|are|was|were|did|do|does|would|could)\s+(?:your\s+)?(.+?)(?:\?|$)",
            question,
            re.IGNORECASE
        )
        if match:
            topic = match.group(1).strip()
            # Avoid generic topics
            if len(topic) > 5 and topic not in ("that", "this", "it", "they", "them"):
                return topic
        
        # Fallback: Use significant part of question
        # Remove question words and extract remainder
        cleaned = re.sub(
            r"^(what|how|why|when|where|can you|could you|tell me|please)\s+",
            "",
            question,
            flags=re.IGNORECASE
        ).strip()
        
        if cleaned and len(cleaned) > 10 and cleaned != question:
            return cleaned[:100]  # Limit length
        
        return "your previous response"
    
    def _expand_with_template(self, question: str, prev_topic: str) -> str:
        """
        Expand a follow-up question using templates.
        
        Args:
            question: The follow-up question.
            prev_topic: The topic from the previous exchange.
            
        Returns:
            Expanded question or original if no template matches.
        """
        question_stripped = question.strip()
        question_lower = question_stripped.lower()
        
        for pattern, template in EXPANSION_TEMPLATES.items():
            match = re.match(pattern, question_lower, re.IGNORECASE)
            if match:
                # Build replacement dict
                replacements = {"prev_topic": prev_topic}
                
                # Add any captured groups - preserve original case from input
                groups = match.groups()
                if groups:
                    # Get original text with preserved case
                    orig_match = re.match(pattern, question_stripped, re.IGNORECASE)
                    orig_groups = orig_match.groups() if orig_match else groups
                    replacements["match"] = orig_groups[0] if orig_groups[0] else ""
                    if len(orig_groups) > 1:
                        replacements["match2"] = orig_groups[1] if orig_groups[1] else ""
                
                try:
                    expanded = template.format(**replacements)
                    # Capitalize first letter
                    if expanded:
                        expanded = expanded[0].upper() + expanded[1:]
                    return expanded
                except (KeyError, IndexError):
                    continue
        
        # No template matched, try generic expansion
        return self._generic_expansion(question, prev_topic)
    
    def _generic_expansion(self, question: str, prev_topic: str) -> str:
        """
        Generic expansion for follow-ups that don't match specific templates.
        
        Args:
            question: The follow-up question.
            prev_topic: The topic from the previous exchange.
            
        Returns:
            Expanded question.
        """
        question_lower = question.lower().strip()
        
        # Handle "What about X?" pattern
        match = re.match(r"^what about\s+(.+?)\??$", question_lower)
        if match:
            subject = match.group(1)
            return f"What is your experience with {subject} in relation to {prev_topic}?"
        
        # Handle "How about X?" pattern
        match = re.match(r"^how about\s+(.+?)\??$", question_lower)
        if match:
            subject = match.group(1)
            return f"How do you handle {subject} based on your experience with {prev_topic}?"
        
        # Handle pronoun endings
        if re.search(r"\b(that|this|it)\s*\??$", question_lower):
            # Replace the pronoun with the topic
            expanded = re.sub(
                r"\b(that|this|it)(\s*\??)$",
                f"{prev_topic}\\2",
                question,
                flags=re.IGNORECASE
            )
            return expanded
        
        return question
