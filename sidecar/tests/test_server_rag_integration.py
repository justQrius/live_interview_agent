import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import json
import asyncio

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from server import SidecarServer
from protocol import Message, MessageType

@pytest.mark.asyncio
class TestServerRagIntegration:
    @pytest.fixture
    def mock_vector_store(self):
        with patch('server.VectorStore') as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance
            yield instance

    @pytest.fixture
    def mock_context_manager(self):
        with patch('server.ContextManager') as mock_cls:
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
        with patch('server.SpeakerRecognizer'), \
             patch('server.GeminiSTT'), \
             patch('server.VADProcessor'), \
             patch('server.AudioCapture'):
            s = SidecarServer()
            yield s
            # Cleaning up any running tasks if necessary, though stop() is not awaited in existing code?
            # Looking at SidecarServer.stop(), it is async.
            await s.stop()

    async def test_start_session_initializes_vector_store(self, server, mock_vector_store):
        websocket = AsyncMock()
        
        message = Message(
            type=MessageType.START_SESSION,
            data={"apiKey": "test-key"}
        )
        
        # Patch _start_audio_processing to avoid side effects
        with patch.object(server, '_start_audio_processing', new_callable=AsyncMock):
            await server._handle_start_session(websocket, message)
            
            # Check VectorStore initialized with API key
            from server import VectorStore as VSClass
            VSClass.assert_called_with(api_key="test-key")
            
            # Check server holds reference
            assert server.vector_store == mock_vector_store

    async def test_stop_session_clears_vector_store(self, server, mock_vector_store):
        websocket = AsyncMock()
        server.vector_store = mock_vector_store
        
        message = Message(type=MessageType.STOP_SESSION)
        
        await server._handle_stop_session(websocket, message)
        
        mock_vector_store.clear.assert_called_once()
        assert server.vector_store is None

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
