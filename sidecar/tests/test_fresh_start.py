
import pytest
import sqlite3
import os
from unittest.mock import MagicMock, AsyncMock, patch
from src.server import SidecarServer, SessionStatus, Message, MessageType
from src.memory.store import MemoryStore, CandidateProfile
from src.storage.session_store import SessionHistoryStore

@pytest.fixture
def mock_stores(tmp_path):
    """Create temporary databases for testing."""
    memory_db = tmp_path / "test_memory.db"
    session_db = tmp_path / "test_sessions.db"
    
    # Initialize stores with temp paths
    mem_store = MemoryStore(str(memory_db))
    sess_store = SessionHistoryStore(str(session_db))
    
    return mem_store, sess_store, str(memory_db), str(session_db)

@pytest.mark.asyncio
async def test_fresh_start_on_stop(mock_stores):
    """
    Verify that MemoryStore and SessionStore are cleared when STOP_SESSION is handled.
    """
    mem_store, sess_store, mem_path, sess_path = mock_stores
    
    # 1. Setup Server with mocked dependencies
    server = SidecarServer()
    server.memory_store = mem_store
    server.session_store = sess_store
    server.context_manager = MagicMock()
    server.context_manager.clear_context = MagicMock()
    server._stop_audio_processing = AsyncMock()
    
    # 2. Add Dummy Data to Persistent Stores
    
    # Add a candidate profile
    profile = CandidateProfile(id="prof_1", profile_text="Test Profile")
    mem_store.save_profile(profile)
    
    # Add a session
    sess_id = sess_store.create_session()
    sess_store.add_transcription(sess_id, "User", "Hello", 1.0)
    
    # Verify data exists before stop
    assert mem_store.get_profile() is not None
    assert len(sess_store.list_sessions()) == 1
    
    # 3. Simulate STOP_SESSION message
    websocket = AsyncMock()
    message = Message(type=MessageType.STOP_SESSION)
    
    # Patch broadcast or send to avoid errors
    with patch.object(server, '_stop_audio_processing', new_callable=AsyncMock):
        await server._handle_stop_session(websocket, message)
    
    # 4. Verify Persistent Stores are CLEARED
    
    # Profile should be gone
    assert mem_store.get_profile() is None
    
    # Sessions should be gone
    assert len(sess_store.list_sessions()) == 0
    
    # Verify context manager was cleared (existing logic)
    server.context_manager.clear_context.assert_called_once()

    # Cleanup
    mem_store.close()
    sess_store.close()
