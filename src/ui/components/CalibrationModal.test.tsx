import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react';
import CalibrationModal from './CalibrationModal';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

// Mock store and hooks
vi.mock('../store/sessionStore');
vi.mock('../hooks/useWebSocket');

// Mock AudioContext and MediaDevices
const mockGetUserMedia = vi.fn();
Object.defineProperty(navigator, 'mediaDevices', {
  value: {
    getUserMedia: mockGetUserMedia,
  },
  writable: true,
});

const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockCreateMediaStreamSource = vi.fn();
const mockCreateScriptProcessor = vi.fn();

class MockAudioContext {
  createMediaStreamSource = mockCreateMediaStreamSource;
  createScriptProcessor = mockCreateScriptProcessor;
  close = vi.fn().mockResolvedValue(undefined);
  state = 'running';
  resume = vi.fn().mockResolvedValue(undefined);
  suspend = vi.fn().mockResolvedValue(undefined);
  destination = {};
}

// @ts-ignore
window.AudioContext = MockAudioContext;
// @ts-ignore
window.webkitAudioContext = MockAudioContext;

describe('CalibrationModal', () => {
  const mockSendMessage = vi.fn();
  const mockSetStatus = vi.fn();
  const mockSetVoiceProfileActive = vi.fn();
  const mockSetLastError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useWebSocket as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      sendMessage: mockSendMessage,
      isConnected: true,
    });
    
    // Default store state
    (useSessionStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector: any) => {
      const state = {
        status: 'calibrating', // Modal is open when status is calibrating
        lastError: null,
        setStatus: mockSetStatus,
        setVoiceProfileActive: mockSetVoiceProfileActive,
        setLastError: mockSetLastError,
      };
      return selector(state);
    });

    // Mock successful stream
    mockGetUserMedia.mockResolvedValue({
      getTracks: () => [{ stop: vi.fn() }],
    });

    // Mock ScriptProcessor
    mockCreateScriptProcessor.mockReturnValue({
      connect: mockConnect,
      disconnect: mockDisconnect,
      onaudioprocess: null,
    });
    
    mockCreateMediaStreamSource.mockReturnValue({
      connect: vi.fn(),
    });
  });

  afterEach(() => {
      vi.restoreAllMocks();
  });

  it('renders when status is calibrating', () => {
    render(<CalibrationModal />);
    expect(screen.getByText('Voice Calibration')).toBeInTheDocument();
  });

  it('does not render when status is idle', () => {
    (useSessionStore as unknown as ReturnType<typeof vi.fn>).mockImplementation((selector: any) => {
      return selector({ status: 'idle' });
    });
    render(<CalibrationModal />);
    expect(screen.queryByText('Voice Calibration')).not.toBeInTheDocument();
  });

  it('starts recording when button clicked', async () => {
    render(<CalibrationModal />);
    
    const startButton = screen.getByText('Start Recording');
    await act(async () => {
      fireEvent.click(startButton);
    });

    expect(mockGetUserMedia).toHaveBeenCalledWith(expect.objectContaining({
      audio: expect.objectContaining({
        channelCount: 1,
      })
    }));
    expect(await screen.findByTestId('recording-status')).toHaveTextContent('Recording...');
  });

  it.skip('sends audio data after recording finishes', async () => {
    vi.useFakeTimers();
    const startTime = new Date(2024, 0, 1, 12, 0, 0);
    vi.setSystemTime(startTime);

    render(<CalibrationModal />);
    
    // Start recording
    await act(async () => {
      fireEvent.click(screen.getByText('Start Recording'));
    });

    // Wait for recording to start
    await screen.findByTestId('recording-status');

    // Check if script processor was created
    expect(mockCreateScriptProcessor).toHaveBeenCalled();

    // Simulate audio process
    const scriptProcessor = mockCreateScriptProcessor.mock.results[0].value;
    
    act(() => {
        if (scriptProcessor.onaudioprocess) {
            const mockEvent = {
                inputBuffer: {
                    getChannelData: () => new Float32Array([0.1, -0.1, 0.5, -0.5]),
                }
            };
            scriptProcessor.onaudioprocess(mockEvent);
        }
    });

    // Advance system time past the recording duration
    await act(async () => {
       // Advance time by 6 seconds
       vi.setSystemTime(new Date(startTime.getTime() + 6000));
       // Advance timers to trigger the next RAF/timeout callback
       vi.advanceTimersByTime(100); 
    });

    await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith(
            expect.objectContaining({
                type: 'CALIBRATE_VOICE',
                data: expect.objectContaining({
                    audioData: expect.any(String)
                })
            })
        );
    });

    vi.useRealTimers();
  });

  it('cancels calibration when Cancel is clicked', () => {
    render(<CalibrationModal />);
    
    fireEvent.click(screen.getByText('Cancel'));
    expect(mockSetStatus).toHaveBeenCalledWith('idle');
  });
});
