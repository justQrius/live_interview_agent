import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SessionControls from './SessionControls';
import { useSessionStore } from '../store/sessionStore';

// Mock useWebSocket hook
const mockSendMessage = vi.fn();
vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: mockSendMessage,
    isConnected: true,
  }),
}));

describe('SessionControls', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: 'test-api-key',
      currentTranscription: null,
      currentAnswer: null,
      transcriptionHistory: [],
      answerHistory: [],
      loadedContextFiles: [],
      lastError: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial render', () => {
    it('should render session controls header', () => {
      render(<SessionControls />);
      expect(screen.getByText('Session Controls')).toBeInTheDocument();
    });

    it('should show connected status when connected', () => {
      render(<SessionControls />);
      expect(screen.getByText('Connected to sidecar')).toBeInTheDocument();
    });

    it('should show idle status initially', () => {
      render(<SessionControls />);
      expect(screen.getByText('Idle')).toBeInTheDocument();
    });

    it('should show all control buttons', () => {
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /start session/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /stop session/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /calibrate voice/i })).toBeInTheDocument();
    });
  });

  describe('start session', () => {
    it('should enable start button when idle with API key', () => {
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /start session/i })).not.toBeDisabled();
    });

    it('should disable start button when no API key', () => {
      useSessionStore.setState({ apiKey: null });
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /configure api key first/i })).toBeDisabled();
    });

    it('should send START_SESSION message on click', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /start session/i }));

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'START_SESSION',
        data: { apiKey: 'test-api-key' },
      });
    });

    it('should update status to listening after start', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /start session/i }));

      expect(useSessionStore.getState().status).toBe('listening');
    });

    it('should disable start button when not idle', () => {
      useSessionStore.setState({ status: 'listening' });
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /start session/i })).toBeDisabled();
    });
  });

  describe('stop session', () => {
    beforeEach(() => {
      useSessionStore.setState({ status: 'listening' });
    });

    it('should enable stop button when session is active', () => {
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /stop session/i })).not.toBeDisabled();
    });

    it('should disable stop button when idle', () => {
      useSessionStore.setState({ status: 'idle' });
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /stop session/i })).toBeDisabled();
    });

    it('should show confirmation modal when stop clicked', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /stop session/i }));

      expect(screen.getByText('Stop Session?')).toBeInTheDocument();
      expect(screen.getByText(/This will stop the current session/i)).toBeInTheDocument();
    });

    it('should close modal when cancel clicked', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /stop session/i }));
      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(screen.queryByText('Stop Session?')).not.toBeInTheDocument();
    });

    it('should send STOP_SESSION and clear data when confirmed', async () => {
      const user = userEvent.setup();
      useSessionStore.setState({
        status: 'listening',
        transcriptionHistory: [
          { speaker: 'Interviewer', text: 'Test', timestamp: Date.now(), confidence: 0.9 },
        ],
        answerHistory: [
          { question: 'Q', answerText: 'A', confidence: 'high', timestamp: Date.now(), isComplete: true },
        ],
      });
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /stop session/i }));
      await user.click(screen.getAllByRole('button', { name: /stop session/i })[1]); // Confirm button

      expect(mockSendMessage).toHaveBeenCalledWith({ type: 'STOP_SESSION' });
      expect(useSessionStore.getState().status).toBe('idle');
      expect(useSessionStore.getState().transcriptionHistory).toEqual([]);
      expect(useSessionStore.getState().answerHistory).toEqual([]);
    });
  });

  describe('calibrate voice', () => {
    it('should enable calibrate button when idle and connected', () => {
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /calibrate voice/i })).not.toBeDisabled();
    });

    it('should disable calibrate button when not idle', () => {
      useSessionStore.setState({ status: 'listening' });
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /calibrate voice/i })).toBeDisabled();
    });

    it('should set status to calibrating on click', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.click(screen.getByRole('button', { name: /calibrate voice/i }));

      expect(useSessionStore.getState().status).toBe('calibrating');
    });
  });

  describe('manual question input', () => {
    beforeEach(() => {
      useSessionStore.setState({ status: 'listening' });
    });

    it('should show manual question input when listening', () => {
      render(<SessionControls />);
      expect(screen.getByLabelText(/ask a question manually/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/type a question/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send question/i })).toBeInTheDocument();
    });

    it('should hide manual question input when not listening', () => {
      useSessionStore.setState({ status: 'idle' });
      render(<SessionControls />);
      expect(screen.queryByLabelText(/ask a question manually/i)).not.toBeInTheDocument();
    });

    it('should disable send button when input is empty', () => {
      render(<SessionControls />);
      expect(screen.getByRole('button', { name: /send question/i })).toBeDisabled();
    });

    it('should enable send button when input has text', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.type(screen.getByPlaceholderText(/type a question/i), 'Test question');

      expect(screen.getByRole('button', { name: /send question/i })).not.toBeDisabled();
    });

    it('should send MANUAL_QUESTION message on click', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.type(screen.getByPlaceholderText(/type a question/i), 'What is React?');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'MANUAL_QUESTION',
        data: { question: 'What is React?' },
      });
    });

    it('should clear input after sending', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Test question');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(input).toHaveValue('');
    });

    it('should send message on Enter key', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Enter test{Enter}');

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'MANUAL_QUESTION',
        data: { question: 'Enter test' },
      });
    });

    it('should not send on Shift+Enter', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Test{Shift>}{Enter}{/Shift}more text');

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should not send whitespace-only input', async () => {
      const user = userEvent.setup();
      render(<SessionControls />);

      await user.type(screen.getByPlaceholderText(/type a question/i), '   ');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should clear current answer before sending new question', async () => {
      const user = userEvent.setup();
      useSessionStore.setState({
        status: 'listening',
        currentAnswer: {
          question: 'Old Q',
          answerText: 'Old A',
          confidence: 'high',
          timestamp: Date.now(),
          isComplete: true,
        },
      });
      render(<SessionControls />);

      await user.type(screen.getByPlaceholderText(/type a question/i), 'New question');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(useSessionStore.getState().currentAnswer).toBeNull();
    });
  });

  describe('status display', () => {
    it('should show listening status with green color', () => {
      useSessionStore.setState({ status: 'listening' });
      render(<SessionControls />);
      expect(screen.getByText('Listening...')).toBeInTheDocument();
    });

    it('should show processing status with blue color', () => {
      useSessionStore.setState({ status: 'processing' });
      render(<SessionControls />);
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('should show calibrating status with yellow color', () => {
      useSessionStore.setState({ status: 'calibrating' });
      render(<SessionControls />);
      expect(screen.getByText('Calibrating...')).toBeInTheDocument();
    });
  });
});

