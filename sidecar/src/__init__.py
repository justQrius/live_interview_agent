# Live Interview Agent - Python Sidecar
"""
Sidecar process for the Live Interview Agent.
Handles audio capture, VAD, STT, RAG, and LLM processing.
Communicates with Tauri UI via WebSocket on localhost:8765.
"""

__version__ = "0.1.0"
