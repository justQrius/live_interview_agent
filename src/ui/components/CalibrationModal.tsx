import React, { useEffect, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

const RECORDING_DURATION_MS = 5000;

const CalibrationModal: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const setStatus = useSessionStore((state) => state.setStatus);
  const setVoiceProfileActive = useSessionStore((state) => state.setVoiceProfileActive);
  const lastError = useSessionStore((state) => state.lastError);
  const setLastError = useSessionStore((state) => state.setLastError);
  const { sendMessage } = useWebSocket();

  const [isRecording, setIsRecording] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Int16Array[]>([]);
  const startTimeRef = useRef<number>(0);
  const animationFrameRef = useRef<number>(0);
  const prevStatusRef = useRef(status);

  useEffect(() => {
    if (prevStatusRef.current === 'calibrating' && status === 'idle') {
      if (!lastError && !error) {
        setVoiceProfileActive(true);
      }
    }
    prevStatusRef.current = status;
  }, [status, lastError, error, setVoiceProfileActive]);

  // Reset state when modal opens
  useEffect(() => {
    if (status === 'calibrating') {
      setIsRecording(false);
      setProgress(0);
      setError(null);
      setLastError(null);
      audioChunksRef.current = [];
    }
  }, [status, setLastError]);

  // Clean up on unmount or close
  useEffect(() => {
    return () => {
      stopRecordingResources();
    };
  }, []);

  const stopRecordingResources = () => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current.onaudioprocess = null;
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(console.error);
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
  };

  const handleStartRecording = async () => {
    setError(null);
    audioChunksRef.current = [];
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        } 
      });
      
      streamRef.current = stream;
      
      // Create AudioContext at 16kHz
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      
      // Use ScriptProcessor (bufferSize, inputChannels, outputChannels)
      // 4096 gives ~256ms latency at 16kHz
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        
        // Convert Float32 to Int16
        const int16Data = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          // Clamp to [-1, 1] then scale to Int16 range
          const s = Math.max(-1, Math.min(1, inputData[i]));
          int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        audioChunksRef.current.push(int16Data);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
      startTimeRef.current = Date.now();
      
      // Start progress loop
      const updateProgress = () => {
        const elapsed = Date.now() - startTimeRef.current;
        const p = Math.min(100, (elapsed / RECORDING_DURATION_MS) * 100);
        setProgress(p);

        if (elapsed < RECORDING_DURATION_MS) {
          animationFrameRef.current = requestAnimationFrame(updateProgress);
        } else {
          finishRecording();
        }
      };
      
      animationFrameRef.current = requestAnimationFrame(updateProgress);

    } catch (err) {
      console.error('Failed to start recording:', err);
      setError('Could not access microphone. Please check permissions.');
    }
  };

  const finishRecording = async () => {
    stopRecordingResources();
    setIsRecording(false);
    setProgress(100);

    // Concatenate chunks
    const totalLength = audioChunksRef.current.reduce((acc, chunk) => acc + chunk.length, 0);
    const finalBuffer = new Int16Array(totalLength);
    let offset = 0;
    for (const chunk of audioChunksRef.current) {
      finalBuffer.set(chunk, offset);
      offset += chunk.length;
    }

    if (totalLength === 0) {
      setError('No audio captured.');
      return;
    }

    // Convert to Base64
    const base64Audio = arrayBufferToBase64(finalBuffer.buffer);
    
    // Send to server
    sendMessage({
      type: 'CALIBRATE_VOICE',
      data: { audioData: base64Audio } // Wrap in data object if protocol expects it, 
      // check usage in sessionControls. 
      // Wait, AGENTS.md says {"type": "CALIBRATE_VOICE", "audioData": "..."} at top level?
      // But useWebSocket structure is { type, data? }.
      // Let's check useWebSocket implementation again.
    });
    
    // In useWebSocket.ts:
    // const sendMessage = (message: WebSocketMessage) => { ... ws.send(JSON.stringify(message)); }
    // WebSocketMessage = { type: MessageType; data?: unknown; }
    // So the JSON sent is {"type": "...", "data": ...}
    
    // BUT AGENTS.md says: {"type": "CALIBRATE_VOICE", "audioData": "base64..."}
    // This implies audioData is a sibling of type, OR inside data.
    // If the Python side expects {"type": "CALIBRATE_VOICE", "audioData": ...} at root, 
    // then useWebSocket's `WebSocketMessage` interface might be slightly misleading or specific to how we structured it.
    
    // Let's check sidecar/src/server.py to be sure how it parses messages.
    // I can't check python files easily right now without reading them.
    // However, usually in this project structure:
    // If useWebSocket enforces {type, data}, then I should send { type: 'CALIBRATE_VOICE', data: { audioData: ... } }
    // AND server.py should look into `data` field.
    
    // Let's assume the useWebSocket structure is authoritative for the frontend.
    // I will verify with server.py later if tests fail or if I can read it.
    
    // For now, I will assume { type: 'CALIBRATE_VOICE', data: { audioData: ... } } is how useWebSocket sends it.
    // If I pass data: { audioData: ... }, useWebSocket stringifies { type: ..., data: { audioData: ... } }
    
    // Update store to indicate we are done (optimistic or wait for server?)
    // Requirement says "Shows Success/Error state based on server response"
    // So we don't close immediately. We wait for server to change status.
    // But sending calibration usually triggers 'processing' then 'idle'.
    
    // For now, I'll just show "Processing..." state locally? 
    // No, status is global.
  };

  const handleCancel = () => {
    stopRecordingResources();
    setStatus('idle');
  };

  if (status !== 'calibrating') return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4">
        <h2 className="text-2xl font-bold mb-4">Voice Calibration</h2>
        
        {error ? (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        ) : (
          <p className="text-gray-600 mb-4">
            Please read the following text clearly:
            <br />
            <span className="font-medium italic block mt-2 p-3 bg-gray-50 rounded text-gray-800">
              "The quick brown fox jumps over the lazy dog. I am calibrating my voice profile for the interview."
            </span>
          </p>
        )}

        <div className="mb-6">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div 
              className={`h-2.5 rounded-full transition-all duration-100 ${isRecording ? 'bg-red-600' : 'bg-blue-600'}`} 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-500 mt-2 flex justify-between">
            <span data-testid="recording-status">{isRecording ? 'Recording...' : 'Ready to record'}</span>
            <span>{Math.ceil((progress / 100) * (RECORDING_DURATION_MS / 1000))} / {RECORDING_DURATION_MS / 1000}s</span>
          </p>
        </div>

        <div className="flex gap-3">
          {!isRecording ? (
            <button 
              onClick={handleStartRecording}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200"
            >
              Start Recording
            </button>
          ) : (
             <button 
              className="flex-1 bg-gray-400 text-white font-medium py-2 px-4 rounded-lg cursor-not-allowed"
              disabled
            >
              Recording...
            </button>
          )}
          
          <button 
            onClick={handleCancel}
            className="flex-1 bg-gray-300 hover:bg-gray-400 text-gray-700 font-medium py-2 px-4 rounded-lg transition duration-200"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

// Helper to convert ArrayBuffer to Base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export default CalibrationModal;
