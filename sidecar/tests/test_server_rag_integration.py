import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import json
import asyncio

# Add sidecar to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.server import SidecarServer
from src.protocol import Message, MessageType

@pytest.mark.asyncio
class TestServerRagIntegration:
    @pytest.fixture
    def mock_vector_store(self):
        with patch("src.server.VectorStore") as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            yield instance

    @pytest.fixture
    def mock_context_manager(self):
        with patch("src.server.ContextManager") as mock_cls:
            instance = MagicMock()
            # Setup process_file to return some chunks count (default)
            instance.process_file = AsyncMock(return_value=2)
            # Setup get_all_chunks to return chunks
            chunk1 = MagicMock()
            chunk1.text = "chunk1 content"
            chunk2 = MagicMock()
            chunk2.text = "chunk2 content"
            instance.get_all_chunks.return_value = [chunk1, chunk2]
            
            mock_cls.return_value = instance
            yield instance

    @pytest_asyncio.fixture
    async def server(self):
        # We need to mock Audio things to prevent server startup failure or errors
        with patch("src.server.SpeakerRecognizer"),              patch("src.server.GeminiSTTProvider"),              patch("src.server.VADProcessor"),              patch("src.server.AudioCapture"),              patch("src.server.ModelWarmer"):
            s = SidecarServer()
            yield s
            await s.stop()

    async def test_start_session_initializes_vector_store(self, server, mock_vector_store):
        websocket = AsyncMock()
        
        message = Message(
            type=MessageType.START_SESSION,
            data={"apiKey": "test-key"}
        )
        
        # Patch _start_audio_processing and _init_rag_background to avoid side effects
        with patch.object(server, "_start_audio_processing", new_callable=AsyncMock),              patch.object(server, "_init_rag_background", new_callable=AsyncMock) as mock_init_rag:
            await server._handle_start_session(websocket, message)
            
            # Verify RAG initialization was scheduled
            mock_init_rag.assert_called_with("test-key")


    async def test_stop_session_preserves_vector_store(self, server, mock_vector_store):
        """
        Verify that STOP_SESSION preserves vector store for quick restart.
        
        The server intentionally preserves context (RAG, Cache, Profile) across
        session stops to allow restarting without re-uploading documents.
        """
        websocket = AsyncMock()
        server.vector_store = mock_vector_store
        
        message = Message(type=MessageType.STOP_SESSION)
        
        await server._handle_stop_session(websocket, message)
        
        # Vector store should NOT be cleared (intentional design)
        mock_vector_store.clear.assert_not_called()
        # Vector store should still be available
        assert server.vector_store is not None

    async def test_upload_context_adds_to_vector_store(self, server, mock_vector_store):
        websocket = AsyncMock()
        server.vector_store = mock_vector_store
        
        # Mock context manager
        chunk1 = MagicMock()
        chunk1.text = "content1"
        chunk1.metadata = {"source": "file1"}
        chunk2 = MagicMock()
        chunk2.text = "content2"
        chunk2.metadata = {"source": "file1"}
        
        # We need to make sure server uses the same context manager instance if possible
        # Or we can just mock the property on the server
        server.context_manager.process_file = AsyncMock(return_value=2)
        
        # NOTE: server.py implementation needs to get chunks from somewhere.
        # If it uses context_manager.get_all_chunks() or if we modify process_file to return chunks.
        # Let's assume we modify process_file to return chunks, OR we use a separate method to get recent chunks.
        # For this test, let's assume we implement a way.
        # If we use `get_all_chunks`, we should mock it.
        server.context_manager.get_all_chunks = MagicMock(return_value=[chunk1, chunk2])
        
        # But wait, if we upload multiple files, we might want to only add new chunks.
        # Let's see how we implement it.
        # If I change process_file to return [Chunk], I can verify that.
        # Let's setup the expectation:
        # We will modify process_file to return List[Chunk] instead of int.
        
        server.context_manager.process_file = AsyncMock(return_value=[chunk1, chunk2])
        
        message = Message(
            type=MessageType.UPLOAD_CONTEXT,
            data={"files": [{"name": "file1.txt", "content": "base64content"}]}
        )
        
        await server._handle_upload_context(websocket, message)
        
        # Verify add_documents called
        # mock_vector_store.add_documents.assert_called_with(["content1", "content2"])
        # Actually checking validation might fail if chunks order or strict equality.
        # Let's check arguments.
        
        args = mock_vector_store.add_documents.call_args
        assert args is not None
        assert args[0][0] == ["content1", "content2"]
        # Metadata check if we implement it
        # assert args[1]['metadatas'] == ...
