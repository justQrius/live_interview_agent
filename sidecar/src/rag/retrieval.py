from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from src.protocol import ConfidenceLevel

@dataclass
class RetrievalResult:
    """
    Represents a single retrieved document chunk with scoring.
    """
    text: str
    distance: float
    confidence: ConfidenceLevel
    metadata: Dict[str, Any] = field(default_factory=dict)

def confidence_from_distance(distance: float) -> ConfidenceLevel:
    """
    Map vector distance to a confidence level.
    
    Heuristics based on cosine distance (lower is better):
    - < 0.35: High confidence (very close match)
    - < 0.65: Medium confidence (relevant)
    - >= 0.65: Low confidence (likely tangential or irrelevant)
    
    Args:
        distance: The distance score from ChromaDB (lower is better for cosine distance)
        
    Returns:
        ConfidenceLevel enum
    """
    if distance < 0.35:
        return ConfidenceLevel.HIGH
    elif distance < 0.65:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
