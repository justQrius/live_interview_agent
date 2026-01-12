"""
Session Exporter - Export session data to various formats.

Provides utilities to convert SessionData into JSON, Markdown, and plain text
formats for download, sharing, and archival.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from src.storage.session_store import SessionData


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "md"
    TEXT = "txt"


class SessionExporter:
    """
    Export session data to various formats.
    
    Supports:
    - JSON: Complete data with all fields
    - Markdown: Human-readable formatted document
    - Text: Simple transcript format
    """

    @staticmethod
    def export(session: SessionData, format: ExportFormat) -> str:
        """
        Export session data to specified format.
        
        Args:
            session: The session data to export
            format: The desired output format
            
        Returns:
            Formatted string content
            
        Raises:
            ValueError: If format is not supported
        """
        if format == ExportFormat.JSON:
            return SessionExporter._to_json(session)
        elif format == ExportFormat.MARKDOWN:
            return SessionExporter._to_markdown(session)
        elif format == ExportFormat.TEXT:
            return SessionExporter._to_text(session)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def _to_json(session: SessionData) -> str:
        """Export session as pretty-printed JSON."""
        data = {
            "id": session.id,
            "startedAt": session.started_at.isoformat() if session.started_at else None,
            "endedAt": session.ended_at.isoformat() if session.ended_at else None,
            "contextFiles": session.context_files,
            "transcriptions": session.transcriptions,
            "answers": session.answers,
            "metadata": session.metadata
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _to_markdown(session: SessionData) -> str:
        """Export session as formatted Markdown document."""
        lines: List[str] = []
        
        # Title
        lines.append("# Interview Session")
        lines.append("")
        
        # Metadata
        if session.started_at:
            date_str = session.started_at.strftime("%B %d, %Y %I:%M %p")
            lines.append(f"**Date**: {date_str}")
        
        # Duration
        duration_str = SessionExporter._format_duration(session.started_at, session.ended_at)
        lines.append(f"**Duration**: {duration_str}")
        
        # Context files
        if session.context_files:
            files_str = ", ".join(session.context_files)
            lines.append(f"**Context Files**: {files_str}")
        else:
            lines.append("**Context Files**: None")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Transcript section
        lines.append("## Transcript")
        lines.append("")
        
        if not session.transcriptions and not session.answers:
            lines.append("*No conversation recorded.*")
            lines.append("")
        else:
            # Combine and sort by timestamp
            events = SessionExporter._build_timeline(session)
            
            for event in events:
                if event["type"] == "transcription":
                    timestamp = SessionExporter._format_timestamp(event["timestamp"])
                    speaker = event["data"].get("speaker", "Unknown")
                    text = event["data"].get("text", "")
                    
                    lines.append(f"### [{timestamp}] {speaker}")
                    lines.append(text)
                    lines.append("")
                    
                elif event["type"] == "answer":
                    timestamp = SessionExporter._format_timestamp(event["timestamp"])
                    answer_text = event["data"].get("answer", "")
                    confidence = event["data"].get("confidence", "unknown")
                    latency = event["data"].get("latency_ms")
                    
                    lines.append(f"### [{timestamp}] AI Response")
                    lines.append(answer_text)
                    lines.append("")
                    
                    meta_parts = [f"**Confidence**: {confidence.capitalize()}"]
                    if latency:
                        meta_parts.append(f"**Latency**: {latency/1000:.1f}s")
                    lines.append(" | ".join(meta_parts))
                    lines.append("")
                    lines.append("---")
                    lines.append("")
        
        # Summary section
        lines.append("## Summary")
        lines.append("")
        
        total_questions = len(session.answers)
        lines.append(f"- **Total Questions**: {total_questions}")
        
        if session.answers:
            # Average latency
            latencies = [a.get("latency_ms", 0) for a in session.answers if a.get("latency_ms")]
            if latencies:
                avg_latency = sum(latencies) / len(latencies) / 1000
                lines.append(f"- **Average Latency**: {avg_latency:.1f}s")
            
            # Confidence breakdown
            high = sum(1 for a in session.answers if a.get("confidence") == "high")
            medium = sum(1 for a in session.answers if a.get("confidence") == "medium")
            low = sum(1 for a in session.answers if a.get("confidence") == "low")
            
            if total_questions > 0:
                if high:
                    lines.append(f"- **High Confidence**: {high} ({high*100//total_questions}%)")
                if medium:
                    lines.append(f"- **Medium Confidence**: {medium} ({medium*100//total_questions}%)")
                if low:
                    lines.append(f"- **Low Confidence**: {low} ({low*100//total_questions}%)")
        
        lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def _to_text(session: SessionData) -> str:
        """Export session as simple plain text transcript."""
        lines: List[str] = []
        
        # Header
        if session.started_at:
            date_str = session.started_at.strftime("%B %d, %Y")
            lines.append(f"Interview Session - {date_str}")
        else:
            lines.append("Interview Session")
        lines.append("")
        
        if not session.transcriptions and not session.answers:
            lines.append("(No conversation recorded)")
            return "\n".join(lines)
        
        # Build timeline
        events = SessionExporter._build_timeline(session)
        
        for event in events:
            timestamp = SessionExporter._format_timestamp(event["timestamp"])
            
            if event["type"] == "transcription":
                speaker = event["data"].get("speaker", "Unknown")
                text = event["data"].get("text", "")
                lines.append(f"[{timestamp}] {speaker}: {text}")
                
            elif event["type"] == "answer":
                answer_text = event["data"].get("answer", "")
                lines.append(f"[{timestamp}] Response: {answer_text}")
            
            lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def _build_timeline(session: SessionData) -> List[Dict[str, Any]]:
        """Build a sorted timeline of transcriptions and answers."""
        events: List[Dict[str, Any]] = []
        
        for t in session.transcriptions:
            events.append({
                "type": "transcription",
                "timestamp": t.get("timestamp", 0),
                "data": t
            })
        
        for a in session.answers:
            events.append({
                "type": "answer",
                "timestamp": a.get("timestamp", 0),
                "data": a
            })
        
        events.sort(key=lambda x: x["timestamp"])
        return events

    @staticmethod
    def _format_duration(start: datetime | None, end: datetime | None) -> str:
        """Format duration between two timestamps."""
        if not start:
            return "Unknown"
        if not end:
            return "In progress"
        
        delta = end - start
        total_minutes = int(delta.total_seconds() / 60)
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if minutes == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        return f"{hours} hour{'s' if hours > 1 else ''} {minutes} minutes"

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format timestamp in seconds as M:SS or H:MM:SS."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
