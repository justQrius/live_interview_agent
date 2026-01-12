"""
Consistency Tracker - Tracks factual claims to prevent contradictions.

Extracts factual claims (years of experience, metrics, etc.) from answers
and checks against previous claims in the session.

Part of Phase 4E: Interview Coaching (STORY-068)
"""

import re
import logging
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple

from src.storage.session_store import SessionHistoryStore

logger = logging.getLogger(__name__)


@dataclass
class FactClaim:
    """A specific factual claim extracted from text."""
    text: str          # Original text fragment
    claim_type: str    # Type (e.g. experience_years)
    value: str         # Normalized value


@dataclass
class Contradiction:
    """Represents a conflict between two claims."""
    claim_type: str
    existing_value: str
    new_value: str
    message: str
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "claim_type": self.claim_type,
            "existing": self.existing_value,
            "new": self.new_value,
            "message": self.message
        }


@dataclass
class ConsistencyResult:
    """Result of a consistency check."""
    new_claims: List[FactClaim]
    contradictions: List[Contradiction]


class ConsistencyTracker:
    """
    Tracks and validates factual consistency across a session.
    """
    
    # Patterns for extraction
    CLAIM_PATTERNS = [
        # Experience: "5 years of experience", "8+ years in Python"
        (r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)", "experience_years"),
        
        # Team Size: "led a team of 5", "managed 10 engineers"
        (r"(?:team|group|squad)\s+of\s+(\d+)", "team_size"),
        (r"managed\s+(\d+)", "team_size"),
        
        # Metrics: "40% improvement", "reduced latency by 50%"
        (r"(\d+(?:\.\d+)?)%\s+(?:improvement|reduction|increase|growth|boost)", "metric_percent"),
        
        # Money: "$1M revenue", "$500k budget"
        (r"\$(\d+(?:,\d+)?(?:\.\d+)?[KMBkmb]?)", "metric_money"),
        
        # Scale: "500k users", "1 million requests"
        (r"(\d+(?:,\d+)?(?:\.\d+)?[KMBkmb]?)\s+(?:users|requests|customers|clients)", "metric_scale"),
    ]
    
    def __init__(self, session_store: SessionHistoryStore):
        """
        Initialize the ConsistencyTracker.
        
        Args:
            session_store: Store for persisting session claims
        """
        self.store = session_store
        self.session_id: Optional[str] = None
        
    def start_session(self, session_id: str) -> None:
        """Set the current session ID."""
        self.session_id = session_id
        
    def extract_and_check(self, text: str) -> ConsistencyResult:
        """
        Extract claims from text and check for contradictions.
        
        Args:
            text: The text to analyze (e.g. generated answer)
            
        Returns:
            ConsistencyResult containing extracted claims and any contradictions
        """
        if not self.session_id:
            logger.warning("Consistency check requested but no session_id set")
            return ConsistencyResult([], [])
            
        new_claims = self._extract_claims(text)
        if not new_claims:
            return ConsistencyResult([], [])
            
        existing_claims = self.store.get_claims(self.session_id)
        contradictions = []
        
        for new_claim in new_claims:
            for existing in existing_claims:
                # Only compare if same type
                if existing["claim_type"] == new_claim.claim_type:
                    # Check for mismatch
                    if self._is_contradiction(existing["value"], new_claim.value, new_claim.claim_type):
                        # Create contradiction warning
                        # Avoid duplicates if multiple previous claims exist
                        msg = f"Potential contradiction: Previously mentioned {existing['value']}, now saying {new_claim.value}"
                        
                        # Only add if we haven't already flagged this specific pair (simplified)
                        contradictions.append(Contradiction(
                            claim_type=new_claim.claim_type,
                            existing_value=existing["value"],
                            new_value=new_claim.value,
                            message=msg
                        ))
                        break # Stop checking this new claim against history after first conflict
        
        # Store new claims
        timestamp = time.time()
        for claim in new_claims:
            self.store.add_claim(
                session_id=self.session_id,
                claim_type=claim.claim_type,
                value=claim.value,
                original_text=claim.text,
                timestamp=timestamp
            )
            
        if contradictions:
            logger.info(f"Found {len(contradictions)} consistency issues")
            
        return ConsistencyResult(new_claims, contradictions)
    
    def _extract_claims(self, text: str) -> List[FactClaim]:
        """Run regex patterns to extract claims."""
        claims = []
        for pattern, claim_type in self.CLAIM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1)
                full_text = match.group(0)
                
                # Normalize K/M/B suffixes
                value_norm = value.upper().replace(",", "")
                
                claims.append(FactClaim(
                    text=full_text,
                    claim_type=claim_type,
                    value=value_norm
                ))
        return claims
    
    def _is_contradiction(self, val1: str, val2: str, claim_type: str) -> bool:
        """
        Check if two values contradict each other.
        Returns True if they are significantly different.
        """
        if val1 == val2:
            return False
            
        # Try to parse numbers
        try:
            n1 = self._parse_number(val1)
            n2 = self._parse_number(val2)
            
            # If valid numbers, check relative difference
            if n1 is not None and n2 is not None:
                # If metric/money/scale, allow some variance (e.g. rounding)
                if claim_type in ("metric_scale", "metric_money", "metric_percent"):
                    # Allow 10% difference
                    diff = abs(n1 - n2)
                    avg = (n1 + n2) / 2
                    if avg > 0 and (diff / avg) < 0.15:
                        return False
                
                # For years/team size, stricter
                if claim_type in ("experience_years", "team_size"):
                    # Exact match required? Or allow +/- 1?
                    # "5 years" vs "6 years" might be contradictory or just updated.
                    # Let's flag if diff >= 20% or absolute > 1
                    diff = abs(n1 - n2)
                    if diff < 1.0: # Close enough
                        return False
                        
                return True
                
        except Exception:
            pass
            
        # Fallback string comparison (already checked equality)
        return True

    def _parse_number(self, val: str) -> Optional[float]:
        """Parse number string with optional K/M/B suffix."""
        if not val:
            return None
            
        # Remove currency symbols if any leaked in
        s = val.replace("$", "").replace(",", "")
        
        multiplier = 1.0
        if s.endswith("K"):
            multiplier = 1_000.0
            s = s[:-1]
        elif s.endswith("M"):
            multiplier = 1_000_000.0
            s = s[:-1]
        elif s.endswith("B"):
            multiplier = 1_000_000_000.0
            s = s[:-1]
            
        try:
            return float(s) * multiplier
        except ValueError:
            return None
    
    def get_preflight_constraints(self) -> Dict[str, Any]:
        """
        Get all established claims for preflight injection into LLM prompts.
        
        This allows the LLM to see what facts have been established in prior
        answers, enabling it to maintain consistency proactively.
        
        Returns:
            Dict containing established claims grouped by type with summary.
        """
        if not self.session_id:
            return {"claims": [], "summary": ""}
        
        existing_claims = self.store.get_claims(self.session_id)
        if not existing_claims:
            return {"claims": [], "summary": ""}
        
        # Group claims by type
        by_type: Dict[str, List[str]] = {}
        for claim in existing_claims:
            claim_type = claim.get("claim_type", "unknown")
            value = claim.get("value", "")
            if claim_type not in by_type:
                by_type[claim_type] = []
            if value not in by_type[claim_type]:  # Dedupe
                by_type[claim_type].append(value)
        
        # Build human-readable summary
        summaries = []
        type_labels = {
            "experience_years": "Years of experience",
            "team_size": "Team size",
            "metric_percent": "Percentage metrics",
            "metric_money": "Financial figures",
            "metric_scale": "Scale metrics"
        }
        
        for claim_type, values in by_type.items():
            label = type_labels.get(claim_type, claim_type)
            summaries.append(f"- {label}: {', '.join(values)}")
        
        summary_text = ""
        if summaries:
            summary_text = (
                "CONSISTENCY REQUIREMENTS - You have previously stated:\n" +
                "\n".join(summaries) +
                "\n\nMaintain consistency with these established facts."
            )
        
        return {
            "claims": existing_claims,
            "by_type": by_type,
            "summary": summary_text
        }
