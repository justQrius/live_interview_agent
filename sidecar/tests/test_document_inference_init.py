
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from src.server import SidecarServer, Message, MessageType
from src.providers.config import ProviderConfig

@pytest.mark.asyncio
async def test_infer_document_types_auto_init_singular_key():
    """
    Verify that INFER_DOCUMENT_TYPES message with 'apiKey' (singular) initializes the LLM provider.
    This mimics the legacy/simple client format.
    """
    server = SidecarServer()
    server.document_classifier = MagicMock()
    server.document_classifier.classify = AsyncMock()
    server.document_classifier.classify.return_value = MagicMock(
        document_type="resume", confidence=0.9, reason="Test", to_dict=lambda: {}
    )
    
    # Mock ProviderFactory
    with patch("src.server.ProviderFactory") as MockFactory:
        mock_factory_instance = MockFactory.return_value
        mock_llm = MagicMock()
        mock_factory_instance.get_llm_provider.return_value = mock_llm
        
        # 1. Verify LLM is None initially
        assert server.llm is None
        
        # 2. Send INFER_DOCUMENT_TYPES with 'apiKey' (singular)
        websocket = AsyncMock()
        message = Message(
            type=MessageType.INFER_DOCUMENT_TYPES,
            data={
                "files": [{"filename": "resume.txt", "content": "base64encoded"}],
                "apiKey": "fake-key"  # Singular key
            }
        )
        
        server._extract_text_for_classification = AsyncMock(return_value="I am a software engineer...")
        
        await server._handle_infer_document_types(websocket, message)
        
        # 3. Verify LLM was initialized
        # If the bug exists, this will fail because it checked "apiKeys" in data
        assert server.llm == mock_llm, "LLM should be initialized with 'apiKey' singular"

