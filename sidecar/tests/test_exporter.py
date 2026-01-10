"""
Tests for Session Exporter utilities.

Following TDD: tests written first, then implementation.
"""

import json
import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage.session_store import SessionData
from storage.exporter import SessionExporter, ExportFormat


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_export_format_values(self):
        """ExportFormat should have expected values."""
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.MARKDOWN.value == "md"
        assert ExportFormat.TEXT.value == "txt"


class TestSessionExporterJSON:
    """Tests for JSON export format."""

    @pytest.fixture
    def sample_session(self):
        """Create a sample session for testing."""
        return SessionData(
            id="sess_test123",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=datetime(2026, 1, 9, 15, 15, 0),
            context_files=["resume.pdf", "job_description.txt"],
            transcriptions=[
                {
                    "speaker": "Interviewer",
                    "text": "Tell me about yourself.",
                    "timestamp": 0.0,
                    "confidence": 0.95
                },
                {
                    "speaker": "User",
                    "text": "I'm a software engineer...",
                    "timestamp": 5.0,
                    "confidence": 0.92
                }
            ],
            answers=[
                {
                    "question": "Tell me about yourself.",
                    "answer": "I'm a software engineer with 5 years of experience...",
                    "confidence": "high",
                    "timestamp": 5.0,
                    "latency_ms": 1200
                }
            ]
        )

    def test_json_export_valid_json(self, sample_session):
        """JSON export should produce valid JSON."""
        result = SessionExporter.export(sample_session, ExportFormat.JSON)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_export_contains_all_fields(self, sample_session):
        """JSON export should contain all session fields."""
        result = SessionExporter.export(sample_session, ExportFormat.JSON)
        parsed = json.loads(result)
        
        assert parsed["id"] == "sess_test123"
        assert "startedAt" in parsed
        assert "endedAt" in parsed
        assert parsed["contextFiles"] == ["resume.pdf", "job_description.txt"]
        assert len(parsed["transcriptions"]) == 2
        assert len(parsed["answers"]) == 1

    def test_json_export_timestamps_as_iso(self, sample_session):
        """JSON export should format timestamps as ISO strings."""
        result = SessionExporter.export(sample_session, ExportFormat.JSON)
        parsed = json.loads(result)
        
        # Should be ISO format strings
        assert "2026-01-09" in parsed["startedAt"]
        assert "2026-01-09" in parsed["endedAt"]

    def test_json_export_pretty_printed(self, sample_session):
        """JSON export should be pretty-printed for readability."""
        result = SessionExporter.export(sample_session, ExportFormat.JSON)
        # Pretty-printed JSON has newlines and indentation
        assert "\n" in result
        assert "  " in result


class TestSessionExporterMarkdown:
    """Tests for Markdown export format."""

    @pytest.fixture
    def sample_session(self):
        """Create a sample session for testing."""
        return SessionData(
            id="sess_test123",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=datetime(2026, 1, 9, 15, 15, 0),
            context_files=["resume.pdf"],
            transcriptions=[
                {
                    "speaker": "Interviewer",
                    "text": "Tell me about yourself.",
                    "timestamp": 0.0,
                    "confidence": 0.95
                }
            ],
            answers=[
                {
                    "question": "Tell me about yourself.",
                    "answer": "I'm a software engineer with 5 years of experience...",
                    "confidence": "high",
                    "timestamp": 5.0,
                    "latency_ms": 1200
                }
            ]
        )

    def test_markdown_export_has_title(self, sample_session):
        """Markdown export should have a title header."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        assert "# Interview Session" in result

    def test_markdown_export_has_metadata(self, sample_session):
        """Markdown export should include session metadata."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        
        assert "**Date**:" in result
        assert "**Duration**:" in result
        assert "**Context Files**:" in result
        assert "resume.pdf" in result

    def test_markdown_export_has_transcript_section(self, sample_session):
        """Markdown export should have transcript section."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        
        assert "## Transcript" in result or "## Conversation" in result

    def test_markdown_export_includes_speaker_labels(self, sample_session):
        """Markdown export should include speaker labels."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        
        assert "Interviewer" in result

    def test_markdown_export_includes_ai_responses(self, sample_session):
        """Markdown export should include AI responses with confidence."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        
        assert "I'm a software engineer" in result
        assert "high" in result.lower() or "High" in result

    def test_markdown_export_has_summary(self, sample_session):
        """Markdown export should have a summary section."""
        result = SessionExporter.export(sample_session, ExportFormat.MARKDOWN)
        
        assert "## Summary" in result or "Total" in result or "questions" in result.lower()


class TestSessionExporterText:
    """Tests for plain text export format."""

    @pytest.fixture
    def sample_session(self):
        """Create a sample session for testing."""
        return SessionData(
            id="sess_test123",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=datetime(2026, 1, 9, 15, 15, 0),
            context_files=["resume.pdf"],
            transcriptions=[
                {
                    "speaker": "Interviewer",
                    "text": "Tell me about yourself.",
                    "timestamp": 0.0,
                    "confidence": 0.95
                },
                {
                    "speaker": "User",
                    "text": "I have 5 years of experience.",
                    "timestamp": 30.0,
                    "confidence": 0.90
                }
            ],
            answers=[
                {
                    "question": "Tell me about yourself.",
                    "answer": "I'm a software engineer...",
                    "confidence": "high",
                    "timestamp": 5.0,
                    "latency_ms": 1200
                }
            ]
        )

    def test_text_export_has_header(self, sample_session):
        """Text export should have a header with date."""
        result = SessionExporter.export(sample_session, ExportFormat.TEXT)
        
        assert "Interview Session" in result or "Session" in result
        assert "2026" in result

    def test_text_export_has_timestamps(self, sample_session):
        """Text export should include timestamps."""
        result = SessionExporter.export(sample_session, ExportFormat.TEXT)
        
        # Timestamps like [0:00] or 0:00
        assert "0:00" in result or "[0:00]" in result

    def test_text_export_includes_speakers(self, sample_session):
        """Text export should include speaker labels."""
        result = SessionExporter.export(sample_session, ExportFormat.TEXT)
        
        assert "Interviewer" in result

    def test_text_export_includes_content(self, sample_session):
        """Text export should include transcription content."""
        result = SessionExporter.export(sample_session, ExportFormat.TEXT)
        
        assert "Tell me about yourself" in result

    def test_text_export_simple_format(self, sample_session):
        """Text export should be simple without markdown formatting."""
        result = SessionExporter.export(sample_session, ExportFormat.TEXT)
        
        # Should not have markdown headers
        assert "##" not in result
        assert "**" not in result


class TestSessionExporterEdgeCases:
    """Tests for edge cases in export."""

    def test_empty_session(self):
        """Export should handle empty sessions gracefully."""
        session = SessionData(
            id="sess_empty",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=None,
            context_files=[],
            transcriptions=[],
            answers=[]
        )
        
        # Should not raise
        json_result = SessionExporter.export(session, ExportFormat.JSON)
        md_result = SessionExporter.export(session, ExportFormat.MARKDOWN)
        txt_result = SessionExporter.export(session, ExportFormat.TEXT)
        
        assert json_result is not None
        assert md_result is not None
        assert txt_result is not None

    def test_special_characters(self):
        """Export should handle special characters."""
        session = SessionData(
            id="sess_special",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=datetime(2026, 1, 9, 15, 0, 0),
            context_files=["résumé.pdf"],
            transcriptions=[
                {
                    "speaker": "Interviewer",
                    "text": "What's your experience with \"Python\"?\nAnd C++?",
                    "timestamp": 0.0,
                    "confidence": 0.95
                }
            ],
            answers=[]
        )
        
        # JSON should handle escaping
        json_result = SessionExporter.export(session, ExportFormat.JSON)
        parsed = json.loads(json_result)
        assert "Python" in parsed["transcriptions"][0]["text"]
        
        # Markdown should preserve content
        md_result = SessionExporter.export(session, ExportFormat.MARKDOWN)
        assert "Python" in md_result

    def test_no_ended_at(self):
        """Export should handle sessions without end time."""
        session = SessionData(
            id="sess_ongoing",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=None,
            context_files=[],
            transcriptions=[],
            answers=[]
        )
        
        md_result = SessionExporter.export(session, ExportFormat.MARKDOWN)
        # Should indicate in progress or handle gracefully
        assert "In progress" in md_result or "Duration" in md_result

    def test_large_session(self):
        """Export should handle large sessions efficiently."""
        transcriptions = [
            {
                "speaker": "Interviewer" if i % 2 == 0 else "User",
                "text": f"This is message number {i}.",
                "timestamp": float(i * 10),
                "confidence": 0.9
            }
            for i in range(100)
        ]
        
        session = SessionData(
            id="sess_large",
            started_at=datetime(2026, 1, 9, 14, 0, 0),
            ended_at=datetime(2026, 1, 9, 15, 0, 0),
            context_files=["resume.pdf"],
            transcriptions=transcriptions,
            answers=[]
        )
        
        # Should complete without error
        json_result = SessionExporter.export(session, ExportFormat.JSON)
        md_result = SessionExporter.export(session, ExportFormat.MARKDOWN)
        txt_result = SessionExporter.export(session, ExportFormat.TEXT)
        
        # Verify all transcriptions included
        parsed = json.loads(json_result)
        assert len(parsed["transcriptions"]) == 100

    def test_unsupported_format_raises(self):
        """Export should raise for unsupported formats."""
        session = SessionData(
            id="sess_test",
            started_at=datetime(2026, 1, 9, 14, 30, 0),
            ended_at=None,
            context_files=[],
            transcriptions=[],
            answers=[]
        )
        
        with pytest.raises(ValueError):
            SessionExporter.export(session, "invalid_format")  # type: ignore
