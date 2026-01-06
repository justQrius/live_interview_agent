from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from protocol import ConfidenceLevel

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
    
    Heuristics based on Gemini embeddings (cosine distance):
    - < 0.3: High confidence (very close match)
    - < 0.5: Medium confidence (relevant)
    - >= 0.5: Low confidence (likely tangential or irrelevant)
    
    Args:
        distance: The distance score from ChromaDB (lower is better for cosine distance)
        
    Returns:
        ConfidenceLevel enum
    """
    if distance < 0.3:
        return ConfidenceLevel.HIGH
    elif distance < 0.5:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW
