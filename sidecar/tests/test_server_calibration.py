import asyncio
import json
import base64
import pytest
import numpy as np
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from protocol import Message, MessageType, SessionStatus

@pytest.mark.asyncio
class TestServerCalibration:
    
    @pytest.fixture
    def mock_recognizer(self):
        with patch('server.SpeakerRecognizer') as mock:
            instance = mock.return_value
            # Mock create_embedding to return a dummy embedding
            instance.create_embedding.return_value = np.zeros(192, dtype=np.float32)
            yield instance

    async def test_calibrate_voice_success(self, mock_recognizer):
        from server import SidecarServer
        
        server = SidecarServer(port=8766) # Use different port
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1) # Wait for start
        
        try:
            import websockets
            async with websockets.connect("ws://127.0.0.1:8766") as ws:
                # 1. Start session
                await ws.send(Message(MessageType.START_SESSION, {"apiKey": "key"}).to_json())
                await ws.recv() # Status msg
                
                # 2. Send calibration data
                # Create dummy audio bytes (int16)
                audio_data = np.zeros(16000, dtype=np.int16).tobytes()
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                msg = Message(
                    MessageType.CALIBRATE_VOICE,
                    {"audioData": audio_b64}
                )
                await ws.send(msg.to_json())
                
                # 3. Expect CALIBRATING status
                response1 = await ws.recv()
                msg1 = Message.from_json(response1)
                assert msg1.type == MessageType.STATUS
                assert msg1.data["state"] == "calibrating"
                
                # 4. Expect IDLE status (completion)
                response2 = await ws.recv()
                msg2 = Message.from_json(response2)
                assert msg2.type == MessageType.STATUS
                assert msg2.data["state"] == "idle"
                
                # Verify embedding was created
                assert mock_recognizer.create_embedding.called
                
        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass

    async def test_calibrate_voice_failure(self, mock_recognizer):
        from server import SidecarServer
        
        # Make create_embedding raise exception
        mock_recognizer.create_embedding.side_effect = Exception("Model error")
        
        server = SidecarServer(port=8767)
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(0.1)
        
        try:
            import websockets
            async with websockets.connect("ws://127.0.0.1:8767") as ws:
                await ws.send(Message(MessageType.START_SESSION, {"apiKey": "key"}).to_json())
                await ws.recv()
                
                audio_data = np.zeros(16000, dtype=np.int16).tobytes()
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                msg = Message(
                    MessageType.CALIBRATE_VOICE,
                    {"audioData": audio_b64}
                )
                await ws.send(msg.to_json())
                
                # Expect CALIBRATING
                await ws.recv()
                
                # Expect ERROR
                response2 = await ws.recv()
                msg2 = Message.from_json(response2)
                assert msg2.type == MessageType.ERROR
                assert "Model error" in msg2.data["message"]
                
                # Expect IDLE (reset)
                response3 = await ws.recv()
                msg3 = Message.from_json(response3)
                assert msg3.type == MessageType.STATUS
                assert msg3.data["state"] == "idle"
                
        finally:
            await server.stop()
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
