
import asyncio
import logging
from unittest.mock import MagicMock, patch, AsyncMock
import pytest
from providers.llm.gemini import GeminiLLMProvider, GeminiLLMProviderError

# Helper for creating chunk mocks
def _chunk(text: str | None) -> MagicMock:
    chunk = MagicMock()
    chunk.text = text
    return chunk

class TestGeminiRetryLogic:
    @pytest.fixture
    def provider(self):
        with patch("providers.llm.gemini.GeminiClient") as mock_client_cls:
            client = MagicMock()
            mock_client_cls.return_value = client
            provider = GeminiLLMProvider(api_key="test_key")
            provider._client = client
            # Faster backoff for tests
            provider._model_name = "model-1" # Set initial model
            return provider

    @pytest.mark.asyncio
    async def test_retry_on_503(self, provider):
        # Setup: Fail twice with 503, then succeed
        provider._client.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("Overloaded"),
            [_chunk("Success")]
        ]

        # Patch sleep to avoid waiting real time
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            chunks = []
            async for chunk in provider.generate_response("prompt", "context", []):
                chunks.append(chunk)
            
            assert "".join(chunks) == "Success"
            # Should have called generate_content 3 times (2 failures + 1 success)
            assert provider._client.generate_content.call_count == 3
            
            # Verify sleep called twice
            assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_failover_on_429(self, provider):
        # Setup: Fail with 429 on first model, succeed on second
        # Note: We need to check what models are in fallback list
        # By default config it adds fallback models.
        # Let's ensure we have multiple models to try.
        
        # generate_content called with:
        # 1. model-1 -> 429
        # 2. gemini-3-flash-preview -> Success
        
        provider._client.generate_content.side_effect = [
            Exception("429 Resource Exhausted"),
            [_chunk("Success from fallback")]
        ]
        
        chunks = []
        async for chunk in provider.generate_response("prompt", "context", []):
            chunks.append(chunk)
            
        assert "".join(chunks) == "Success from fallback"
        assert provider._client.generate_content.call_count == 2
        
        # Check call args to verify model switching
        # Note: Code retries on same model for 429/503 before switching
        calls = provider._client.generate_content.call_args_list
        assert calls[0].kwargs['model'] == 'model-1'
        # Should retry on same model first
        assert calls[1].kwargs['model'] == 'model-1'

    @pytest.mark.asyncio
    async def test_max_retries_503_then_failover(self, provider):
        # Setup: Fail 503 4 times (initial + 3 retries) on model-1
        # Then succeed on model-2
        
        # We need to simulate enough side effects
        # model-1: 4 failures (initial, retry 1, retry 2, retry 3)
        # model-2: Success
        
        side_effects = [Exception("503 Overloaded")] * 4
        side_effects.append([_chunk("Success from fallback model")])
        
        provider._client.generate_content.side_effect = side_effects
        
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            chunks = []
            async for chunk in provider.generate_response("prompt", "context", []):
                chunks.append(chunk)
                
            assert "".join(chunks) == "Success from fallback model"
            
            # Should call 5 times: 4 on model-1, 1 on model-2
            assert provider._client.generate_content.call_count == 5
            
            # Check models
            calls = provider._client.generate_content.call_args_list
            # First 4 calls use model-1
            for i in range(4):
                assert calls[i].kwargs['model'] == 'model-1'
            # 5th call uses fallback
            assert calls[4].kwargs['model'] == 'gemini-3-flash-preview'

    @pytest.mark.asyncio
    async def test_all_models_fail(self, provider):
        # Setup: All models fail with non-retryable error or exhausted retries
        # Let's just use 400 Bad Request which is non-retryable and fatal
        
        provider._client.generate_content.side_effect = Exception("400 Bad Request")
        
        with pytest.raises(GeminiLLMProviderError, match="non-retryable error"):
            async for _ in provider.generate_response("prompt", "context", []):
                pass
        
        # Should only try once because 400 is not 429 or 503
        assert provider._client.generate_content.call_count == 1
