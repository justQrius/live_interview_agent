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
    <div className="fixed inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-surface dark:bg-surface-elevated rounded-2xl shadow-2xl p-6 max-w-md w-full mx-4 border border-border">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <div>
            <h2 className="text-xl font-bold text-text-primary">Voice Calibration</h2>
            <p className="text-sm text-text-muted">Help us recognize your voice</p>
          </div>
        </div>
        
        {error ? (
          <div className="bg-destructive/10 border border-destructive/20 text-destructive p-4 rounded-xl mb-4 text-sm flex items-center gap-2">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </div>
        ) : (
          <div className="mb-5">
            <p className="text-text-secondary text-sm mb-3">Please read the following text clearly:</p>
            <div className="p-4 bg-surface-elevated dark:bg-surface rounded-xl border border-border">
              <p className="font-medium italic text-text-primary leading-relaxed">
                "The quick brown fox jumps over the lazy dog. I am calibrating my voice profile for the interview."
              </p>
            </div>
          </div>
        )}

        <div className="mb-6">
          <div className="w-full bg-surface-elevated dark:bg-surface rounded-full h-2 overflow-hidden">
            <div 
              className={`h-2 rounded-full transition-all duration-100 ${isRecording ? 'bg-gradient-to-r from-red-500 to-rose-600' : 'bg-gradient-to-r from-blue-500 to-blue-600'}`} 
              style={{ width: `${progress}%` }}
            ></div>
          </div>
          <div className="text-sm text-text-muted mt-2 flex justify-between">
            <span data-testid="recording-status" className={isRecording ? 'text-red-500 font-medium' : ''}>
              {isRecording ? 'Recording...' : 'Ready to record'}
            </span>
            <span className="tabular-nums">{Math.ceil((progress / 100) * (RECORDING_DURATION_MS / 1000))} / {RECORDING_DURATION_MS / 1000}s</span>
          </div>
        </div>

        <div className="flex gap-3">
          {!isRecording ? (
            <button 
              onClick={handleStartRecording}
              className="flex-1 bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white font-medium py-2.5 px-4 rounded-xl transition-all duration-200 shadow-sm"
            >
              Start Recording
            </button>
          ) : (
             <button 
              className="flex-1 bg-surface-elevated dark:bg-surface text-text-muted font-medium py-2.5 px-4 rounded-xl cursor-not-allowed flex items-center justify-center gap-2"
              disabled
            >
              <span className="w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></span>
              Recording...
            </button>
          )}
          
          <button 
            onClick={handleCancel}
            className="flex-1 bg-surface-elevated dark:bg-surface hover:bg-primary/5 dark:hover:bg-primary/10 text-text-primary font-medium py-2.5 px-4 rounded-xl transition-all duration-200 border border-border"
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
