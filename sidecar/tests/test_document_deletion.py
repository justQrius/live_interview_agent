import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
from src.server import SidecarServer
from src.protocol import Message, MessageType

@pytest.mark.asyncio
async def test_handle_delete_document_flow():
    """Test the orchestration of document deletion across all components."""
    # Setup
    server = SidecarServer()
    
    # Mock components
    server.rag_manifest = MagicMock()
    server.vector_store = MagicMock()
    server.context_manager = MagicMock()
    server.gemini_file_uploader = MagicMock()
    server.memory_store = MagicMock()
    server.gemini_cache_manager = MagicMock()
    server.llm = MagicMock()
    
    # Mock Websocket
    websocket = AsyncMock()
    
    # Define test data
    filename = "test_resume.pdf"
    message = Message(
        type=MessageType.DELETE_DOCUMENT,
        data={"filename": filename}
    )
    
    # Execute
    await server._handle_delete_document(websocket, message)
    
    # Verify calls
    
    # 1. RagManifest
    server.rag_manifest.remove_document.assert_called_once_with(filename)
    
    # 2. VectorStore
    server.vector_store.delete_document.assert_called_once_with(filename)
    
    # 3. ContextManager
    server.context_manager.remove_document.assert_called_once_with(filename)
    
    # 4. GeminiFileUploader
    server.gemini_file_uploader.delete_file.assert_called_once_with(filename)
    
    # 5. MemoryStore
    server.memory_store.delete_document_by_filename.assert_called_once_with(filename)
    
    # 6. Response sent
    websocket.send.assert_called_once()
    call_args = websocket.send.call_args[0][0]
    response = json.loads(call_args)
    
    assert response["type"] == MessageType.DOCUMENT_DELETED
    assert response["data"]["filename"] == filename
    assert response["data"]["success"] is True

@pytest.mark.asyncio
async def test_handle_delete_document_missing_filename():
    """Test error handling for missing filename."""
    server = SidecarServer()
    websocket = AsyncMock()
    
    message = Message(
        type=MessageType.DELETE_DOCUMENT,
        data={} # Missing filename
    )
    
    await server._handle_delete_document(websocket, message)
    
    # Verify error response
    call_args = websocket.send.call_args[0][0]
    response = json.loads(call_args)
    
    assert response["type"] == MessageType.DOCUMENT_DELETED
    assert response["data"]["success"] is False
    assert "required" in response["data"]["error"]

@pytest.mark.asyncio
async def test_handle_delete_document_exception():
    """Test error handling when a component fails."""
    server = SidecarServer()
    server.rag_manifest = MagicMock()
    # Simulate failure
    server.rag_manifest.remove_document.side_effect = Exception("Manifest error")
    
    websocket = AsyncMock()
    message = Message(
        type=MessageType.DELETE_DOCUMENT,
        data={"filename": "error.txt"}
    )
    
    await server._handle_delete_document(websocket, message)
    
    # Verify error response
    call_args = websocket.send.call_args[0][0]
    response = json.loads(call_args)
    
    assert response["type"] == MessageType.DOCUMENT_DELETED
    assert response["data"]["success"] is False
    assert "Manifest error" in response["data"]["error"]
