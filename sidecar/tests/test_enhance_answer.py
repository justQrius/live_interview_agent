"""
Tests for answer enhancement feature (Phase 5).
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.protocol import (
    MessageType,
    EnhancementType,
    create_enhanced_answer_start_message,
    create_enhanced_answer_chunk_message,
    create_enhanced_answer_complete_message,
)


class TestEnhancementType:
    """Tests for EnhancementType enum."""
    
    def test_enhancement_type_values(self):
        """All enhancement types should exist with correct values."""
        assert EnhancementType.ADD_DETAIL.value == "add_detail"
        assert EnhancementType.MAKE_SPECIFIC.value == "make_specific"
        assert EnhancementType.SUGGEST_STAR.value == "suggest_star"
        assert EnhancementType.ADJUST_TONE.value == "adjust_tone"
        assert EnhancementType.SHORTEN.value == "shorten"
    
    def test_enhancement_type_count(self):
        """Should have exactly 5 enhancement types."""
        assert len(EnhancementType) == 5
    
    def test_enhancement_type_from_string(self):
        """Should be able to create from string value."""
        assert EnhancementType("add_detail") == EnhancementType.ADD_DETAIL
        assert EnhancementType("shorten") == EnhancementType.SHORTEN


class TestEnhancementMessageTypes:
    """Tests for enhancement message types in protocol."""
    
    def test_enhance_answer_message_type_exists(self):
        """ENHANCE_ANSWER message type should exist."""
        assert hasattr(MessageType, 'ENHANCE_ANSWER')
        assert MessageType.ENHANCE_ANSWER.value == "ENHANCE_ANSWER"
    
    def test_enhanced_answer_start_type_exists(self):
        """ENHANCED_ANSWER_START message type should exist."""
        assert hasattr(MessageType, 'ENHANCED_ANSWER_START')
        assert MessageType.ENHANCED_ANSWER_START.value == "ENHANCED_ANSWER_START"
    
    def test_enhanced_answer_chunk_type_exists(self):
        """ENHANCED_ANSWER_CHUNK message type should exist."""
        assert hasattr(MessageType, 'ENHANCED_ANSWER_CHUNK')
        assert MessageType.ENHANCED_ANSWER_CHUNK.value == "ENHANCED_ANSWER_CHUNK"
    
    def test_enhanced_answer_complete_type_exists(self):
        """ENHANCED_ANSWER_COMPLETE message type should exist."""
        assert hasattr(MessageType, 'ENHANCED_ANSWER_COMPLETE')
        assert MessageType.ENHANCED_ANSWER_COMPLETE.value == "ENHANCED_ANSWER_COMPLETE"


class TestEnhancementMessageCreation:
    """Tests for enhancement message helper functions."""
    
    def test_create_enhanced_answer_start_message(self):
        """Should create ENHANCED_ANSWER_START message correctly."""
        msg = create_enhanced_answer_start_message(
            enhancement_type=EnhancementType.ADD_DETAIL,
            original_question="Tell me about yourself"
        )
        
        assert msg.type == MessageType.ENHANCED_ANSWER_START
        assert msg.data["enhancementType"] == "add_detail"
        assert msg.data["originalQuestion"] == "Tell me about yourself"
    
    def test_create_enhanced_answer_chunk_message(self):
        """Should create ENHANCED_ANSWER_CHUNK message correctly."""
        msg = create_enhanced_answer_chunk_message(
            chunk="Here is more detail about my experience...",
            complete=False
        )
        
        assert msg.type == MessageType.ENHANCED_ANSWER_CHUNK
        assert msg.data["chunk"] == "Here is more detail about my experience..."
        assert msg.data["complete"] is False
    
    def test_create_enhanced_answer_chunk_complete(self):
        """Should create complete ENHANCED_ANSWER_CHUNK message."""
        msg = create_enhanced_answer_chunk_message(
            chunk="",
            complete=True
        )
        
        assert msg.type == MessageType.ENHANCED_ANSWER_CHUNK
        assert msg.data["complete"] is True
    
    def test_create_enhanced_answer_complete_message(self):
        """Should create ENHANCED_ANSWER_COMPLETE message correctly."""
        msg = create_enhanced_answer_complete_message(
            enhancement_type=EnhancementType.SHORTEN,
            success=True
        )
        
        assert msg.type == MessageType.ENHANCED_ANSWER_COMPLETE
        assert msg.data["enhancementType"] == "shorten"
        assert msg.data["success"] is True
    
    def test_message_serialization(self):
        """Messages should serialize to JSON correctly."""
        msg = create_enhanced_answer_start_message(
            enhancement_type=EnhancementType.SUGGEST_STAR,
            original_question="Describe a challenge"
        )
        
        json_str = msg.to_json()
        assert '"type": "ENHANCED_ANSWER_START"' in json_str
        assert '"enhancementType": "suggest_star"' in json_str


class TestEnhancementPromptBuilding:
    """Tests for enhancement prompt building logic."""
    
    @pytest.fixture
    def mock_server(self):
        """Create a mock server with the enhancement method."""
        # Import the actual server class
        import sys
        sys.path.insert(0, 'src')
        from server import SidecarServer
        
        server = SidecarServer()
        return server
    
    def test_add_detail_prompt(self, mock_server):
        """ADD_DETAIL prompt should ask for more context."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.ADD_DETAIL,
            question="Tell me about yourself",
            answer="I am a software engineer."
        )
        
        assert "Enhance this answer" in prompt
        assert "more specific details" in prompt.lower() or "context" in prompt.lower()
    
    def test_make_specific_prompt(self, mock_server):
        """MAKE_SPECIFIC prompt should ask for metrics."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.MAKE_SPECIFIC,
            question="What did you achieve?",
            answer="I improved performance."
        )
        
        assert "specific" in prompt.lower()
        assert "numbers" in prompt.lower() or "metrics" in prompt.lower()
    
    def test_suggest_star_prompt(self, mock_server):
        """SUGGEST_STAR prompt should mention STAR format."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.SUGGEST_STAR,
            question="Describe a challenge",
            answer="I faced a difficult project."
        )
        
        assert "STAR" in prompt
        assert "Situation" in prompt
        assert "Task" in prompt
        assert "Action" in prompt
        assert "Result" in prompt
    
    def test_adjust_tone_confident_prompt(self, mock_server):
        """ADJUST_TONE with confident preference should ask for confidence."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.ADJUST_TONE,
            question="Why should we hire you?",
            answer="I think I could help.",
            tone_preference="confident"
        )
        
        assert "confident" in prompt.lower()
    
    def test_adjust_tone_humble_prompt(self, mock_server):
        """ADJUST_TONE with humble preference should ask for humility."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.ADJUST_TONE,
            question="What are your strengths?",
            answer="I am the best at everything.",
            tone_preference="humble"
        )
        
        assert "humble" in prompt.lower()
    
    def test_shorten_prompt(self, mock_server):
        """SHORTEN prompt should ask to condense."""
        prompt = mock_server._build_enhancement_prompt(
            enhancement_type=EnhancementType.SHORTEN,
            question="What is your experience?",
            answer="I have extensive experience spanning many years..."
        )
        
        assert "shorten" in prompt.lower() or "condense" in prompt.lower() or "concise" in prompt.lower()
    
    def test_prompt_includes_original_content(self, mock_server):
        """All prompts should include original question and answer."""
        question = "Tell me about a project"
        answer = "I led a major migration project"
        
        for enhancement_type in EnhancementType:
            prompt = mock_server._build_enhancement_prompt(
                enhancement_type=enhancement_type,
                question=question,
                answer=answer
            )
            
            assert question in prompt
            assert answer in prompt


class TestEnhancementHandlerValidation:
    """Tests for enhancement handler input validation."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.send = AsyncMock()
        return ws
    
    @pytest.fixture
    def server(self):
        """Create server instance."""
        import sys
        sys.path.insert(0, 'src')
        from server import SidecarServer
        return SidecarServer()
    
    @pytest.mark.asyncio
    async def test_missing_original_question_error(self, server, mock_websocket):
        """Should return error when originalQuestion is missing."""
        from src.protocol import Message, MessageType
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "add_detail",
                "originalAnswer": "Some answer"
            }
        )
        
        await server._handle_enhance_answer(mock_websocket, message)
        
        # Should have sent an error
        mock_websocket.send.assert_called()
        call_args = mock_websocket.send.call_args[0][0]
        assert "ERR_MISSING_DATA" in call_args or "required" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_missing_original_answer_error(self, server, mock_websocket):
        """Should return error when originalAnswer is missing."""
        from src.protocol import Message, MessageType
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "add_detail",
                "originalQuestion": "Some question"
            }
        )
        
        await server._handle_enhance_answer(mock_websocket, message)
        
        mock_websocket.send.assert_called()
        call_args = mock_websocket.send.call_args[0][0]
        assert "ERR_MISSING_DATA" in call_args or "required" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_enhancement_type_error(self, server, mock_websocket):
        """Should return error for invalid enhancement type."""
        from src.protocol import Message, MessageType
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "invalid_type",
                "originalQuestion": "Question",
                "originalAnswer": "Answer"
            }
        )
        
        await server._handle_enhance_answer(mock_websocket, message)
        
        mock_websocket.send.assert_called()
        call_args = mock_websocket.send.call_args[0][0]
        assert "ERR_INVALID_ENHANCEMENT_TYPE" in call_args or "invalid" in call_args.lower()
    
    @pytest.mark.asyncio
    async def test_llm_not_initialized_error(self, server, mock_websocket):
        """Should return error when LLM is not initialized."""
        from src.protocol import Message, MessageType
        
        # Ensure LLM is None
        server.llm = None
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "add_detail",
                "originalQuestion": "Question",
                "originalAnswer": "Answer"
            }
        )
        
        await server._handle_enhance_answer(mock_websocket, message)
        
        mock_websocket.send.assert_called()
        call_args = mock_websocket.send.call_args[0][0]
        assert "ERR_LLM_NOT_READY" in call_args or "LLM" in call_args


class TestEnhancementFlow:
    """Integration tests for enhancement flow."""
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket connection."""
        ws = AsyncMock()
        ws.send = AsyncMock()
        return ws
    
    @pytest.fixture
    def server_with_llm(self):
        """Create server with mocked LLM."""
        import sys
        sys.path.insert(0, 'src')
        from server import SidecarServer
        
        server = SidecarServer()
        
        # Mock LLM that yields chunks
        async def mock_generate(*args, **kwargs):
            yield "Enhanced "
            yield "answer "
            yield "content."
        
        mock_llm = MagicMock()
        mock_llm.generate_response = mock_generate
        server.llm = mock_llm
        
        return server
    
    @pytest.mark.asyncio
    async def test_successful_enhancement_sends_all_messages(self, server_with_llm, mock_websocket):
        """Successful enhancement should send start, chunks, and complete messages."""
        from src.protocol import Message, MessageType
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "add_detail",
                "originalQuestion": "Tell me about yourself",
                "originalAnswer": "I am an engineer."
            }
        )
        
        await server_with_llm._handle_enhance_answer(mock_websocket, message)
        
        # Should have sent multiple messages
        assert mock_websocket.send.call_count >= 3
        
        # Check message types sent
        sent_messages = [call[0][0] for call in mock_websocket.send.call_args_list]
        
        # First should be start
        assert "ENHANCED_ANSWER_START" in sent_messages[0]
        
        # Last should be complete
        assert "ENHANCED_ANSWER_COMPLETE" in sent_messages[-1]
        
        # Middle should be chunks
        chunk_messages = [m for m in sent_messages if "ENHANCED_ANSWER_CHUNK" in m]
        assert len(chunk_messages) >= 1
    
    @pytest.mark.asyncio
    async def test_enhancement_with_rag_for_add_detail(self, server_with_llm, mock_websocket):
        """ADD_DETAIL enhancement should try to fetch more RAG context."""
        from src.protocol import Message, MessageType
        
        # Mock RAG engine
        mock_rag = MagicMock()
        mock_rag.retrieve.return_value = [
            MagicMock(text="Additional context from resume"),
            MagicMock(text="More experience details")
        ]
        server_with_llm.rag_engine = mock_rag
        
        message = Message(
            type=MessageType.ENHANCE_ANSWER,
            data={
                "enhancementType": "add_detail",
                "originalQuestion": "What is your experience?",
                "originalAnswer": "I have 5 years of experience."
            }
        )
        
        await server_with_llm._handle_enhance_answer(mock_websocket, message)
        
        # RAG should have been called with higher limit
        mock_rag.retrieve.assert_called_once()
        call_args = mock_rag.retrieve.call_args
        assert call_args[1].get('limit', call_args[0][1] if len(call_args[0]) > 1 else 5) >= 8


class TestEnhancementTypeSelection:
    """Tests for selecting appropriate enhancement type based on context."""
    
    def test_all_enhancement_types_are_valid(self):
        """All enhancement types should be valid enum members."""
        valid_types = ["add_detail", "make_specific", "suggest_star", "adjust_tone", "shorten"]
        
        for type_str in valid_types:
            enhancement_type = EnhancementType(type_str)
            assert enhancement_type is not None
    
    def test_enhancement_type_invalid_raises(self):
        """Invalid enhancement type string should raise ValueError."""
        with pytest.raises(ValueError):
            EnhancementType("invalid_type")
        
        with pytest.raises(ValueError):
            EnhancementType("ADD_DETAIL")  # Case-sensitive
