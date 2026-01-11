"""
Tests for Consistency Tracker (STORY-068).

Tests claim extraction, consistency checking, and persistence.
"""

import pytest
from unittest.mock import MagicMock
from src.coaching.consistency_tracker import ConsistencyTracker, FactClaim, Contradiction

@pytest.fixture
def mock_session_store():
    store = MagicMock()
    # In-memory storage for test
    claims_db = []
    
    def add_claim(session_id, claim_type, value, original_text, timestamp):
        claims_db.append({
            "session_id": session_id,
            "claim_type": claim_type,
            "value": value,
            "original_text": original_text,
            "timestamp": timestamp
        })
    store.add_claim.side_effect = add_claim
    
    def get_claims(session_id):
        return [c for c in claims_db if c["session_id"] == session_id]
    store.get_claims.side_effect = get_claims
    
    return store

def test_claim_extraction(mock_session_store):
    """Test regex extraction of claims."""
    tracker = ConsistencyTracker(mock_session_store)
    tracker.start_session("sess1")  # Fix: Start session
    text = "I have 5 years of experience and managed a team of 10."
    
    result = tracker.extract_and_check(text)
    claims = result.new_claims
    
    assert len(claims) == 2
    
    # Check years
    c1 = next(c for c in claims if c.claim_type == "experience_years")
    assert c1.value == "5"
    
    # Check team size
    c2 = next(c for c in claims if c.claim_type == "team_size")
    assert c2.value == "10"

def test_contradiction_detection(mock_session_store):
    """Test detection of conflicting claims."""
    tracker = ConsistencyTracker(mock_session_store)
    tracker.start_session("sess1")
    
    # First claim
    tracker.extract_and_check("I have 5 years of experience.")
    
    # Second claim (contradictory)
    result = tracker.extract_and_check("I have 8 years of experience.")
    
    assert len(result.contradictions) == 1
    c = result.contradictions[0]
    assert c.claim_type == "experience_years"
    assert c.existing_value == "5"
    assert c.new_value == "8"

def test_no_contradiction_same_value(mock_session_store):
    """Test that repeating the same claim is fine."""
    tracker = ConsistencyTracker(mock_session_store)
    tracker.start_session("sess1")
    
    tracker.extract_and_check("I have 5 years of experience.")
    result = tracker.extract_and_check("I have 5 years experience.")
    
    assert len(result.contradictions) == 0

def test_metric_tolerance(mock_session_store):
    """Test tolerance for approximate metrics."""
    tracker = ConsistencyTracker(mock_session_store)
    tracker.start_session("sess1")
    
    # 40% vs 42% (within 10-15% tolerance)
    tracker.extract_and_check("We saw a 40% improvement.")
    result = tracker.extract_and_check("It was about a 42% improvement.")
    
    assert len(result.contradictions) == 0
    
    # 40% vs 80% (contradiction)
    result = tracker.extract_and_check("Actually it was 80% improvement.")
    assert len(result.contradictions) == 1

def test_persistence(mock_session_store):
    """Test that claims are persisted to store."""
    tracker = ConsistencyTracker(mock_session_store)
    tracker.start_session("sess1")
    
    tracker.extract_and_check("I have 5 years of experience.")
    
    assert mock_session_store.add_claim.called
    stored = mock_session_store.get_claims("sess1")
    assert len(stored) == 1
    assert stored[0]["value"] == "5"
