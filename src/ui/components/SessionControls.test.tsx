import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SessionControls from './SessionControls';
import { useSessionStore } from '../store/sessionStore';

const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

const mockSendMessage = vi.fn();
vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    sendMessage: mockSendMessage,
    isConnected: true,
  }),
}));

const renderSessionControls = async () => {
  render(<SessionControls />);

  // SessionControls runs an async key check in an effect. Await it so React
  // state updates happen within RTL's internal act() handling.
  // We wait for the invoke to be called, which means the effect ran.
  await waitFor(() => {
    expect(mockInvoke).toHaveBeenCalledWith('has_api_key', expect.any(Object));
  });
};

describe('SessionControls', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    mockInvoke.mockImplementation((command: string, payload?: Record<string, unknown>) => {
      if (command === 'has_api_key') {
        return Promise.resolve({ exists: true });
      }

      if (command === 'get_api_key') {
        const provider = String(payload?.provider ?? '');
        return Promise.resolve(provider ? `key-${provider}` : '');
      }

      return Promise.reject(new Error(`Unexpected invoke: ${command}`));
    });

    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: null,
      preferredSttProvider: 'auto',
      preferredLlmProvider: 'auto',
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
    it('should render session controls header', async () => {
      await renderSessionControls();
      expect(screen.getByText('Session Controls')).toBeInTheDocument();
    });

    it('should show connected status when connected', async () => {
      await renderSessionControls();
      expect(screen.getByText('Connected to sidecar')).toBeInTheDocument();
    });

    it('should show idle status initially', async () => {
      await renderSessionControls();
      expect(screen.getByText('Idle')).toBeInTheDocument();
    });

    it('should show all control buttons', async () => {
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /start session/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /stop session/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /calibrate voice/i })).toBeInTheDocument();
    });
  });

  describe('start session', () => {
    it('should enable start button once API key check resolves', async () => {
      await renderSessionControls();

      const startButton = screen.getByRole('button', { name: /start session/i });
      await waitFor(() => expect(startButton).not.toBeDisabled());
    });

    it('should disable start button when no primary API key exists', async () => {
      mockInvoke.mockImplementation((command: string) => {
        if (command === 'has_api_key') return Promise.resolve({ exists: false });
        return Promise.reject(new Error(`Unexpected invoke: ${command}`));
      });

      await renderSessionControls();

      const startButton = await screen.findByRole('button', { name: /configure api key first/i });
      await waitFor(() => expect(startButton).toBeDisabled());
    });

    it('should send START_SESSION message on click', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      const startButton = screen.getByRole('button', { name: /start session/i });
      await waitFor(() => expect(startButton).not.toBeDisabled());

      await user.click(startButton);

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'START_SESSION',
        data: {
          apiKeys: expect.any(Object),
          preferences: { sttProvider: 'auto', llmProvider: 'auto' },
        },
      });
    });

    it('should update status to listening after start', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      const startButton = screen.getByRole('button', { name: /start session/i });
      await waitFor(() => expect(startButton).not.toBeDisabled());

      await user.click(startButton);

      expect(useSessionStore.getState().status).toBe('listening');
    });

    it('should disable start button when not idle', async () => {
      useSessionStore.setState({ status: 'listening' });
      await renderSessionControls();

      const startButton = await screen.findByRole('button', { name: /start session/i });
      expect(startButton).toBeDisabled();
    });
  });

  describe('stop session', () => {
    beforeEach(() => {
      useSessionStore.setState({ status: 'listening' });
    });

    it('should enable stop button when session is active', async () => {
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /stop session/i })).not.toBeDisabled();
    });

    it('should disable stop button when idle', async () => {
      useSessionStore.setState({ status: 'idle' });
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /stop session/i })).toBeDisabled();
    });

    it('should show confirmation modal when stop clicked', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      await user.click(screen.getByRole('button', { name: /stop session/i }));

      expect(screen.getByText('Stop Session?')).toBeInTheDocument();
      expect(screen.getByText(/This will stop the current session/i)).toBeInTheDocument();
    });

    it('should close modal when cancel clicked', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      await user.click(screen.getByRole('button', { name: /stop session/i }));
      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(screen.queryByText('Stop Session?')).not.toBeInTheDocument();
    });

    it('should send STOP_SESSION and clear data when confirmed', async () => {
      const user = userEvent.setup();
      useSessionStore.setState({
        status: 'listening',
        transcriptionHistory: [{ speaker: 'Interviewer', text: 'Test', timestamp: Date.now(), confidence: 0.9 }],
        answerHistory: [
          {
            question: 'Q',
            answerText: 'A',
            confidence: 'high',
            timestamp: Date.now(),
            isComplete: true,
          },
        ],
      });

      await renderSessionControls();

      await user.click(screen.getByRole('button', { name: /stop session/i }));
      await user.click(screen.getAllByRole('button', { name: /stop session/i })[1]);

      expect(mockSendMessage).toHaveBeenCalledWith({ type: 'STOP_SESSION' });
      expect(useSessionStore.getState().status).toBe('idle');
      expect(useSessionStore.getState().transcriptionHistory).toEqual([]);
      expect(useSessionStore.getState().answerHistory).toEqual([]);
    });
  });

  describe('calibrate voice', () => {
    it('should enable calibrate button when idle and connected', async () => {
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /calibrate voice/i })).not.toBeDisabled();
    });

    it('should disable calibrate button when not idle', async () => {
      useSessionStore.setState({ status: 'listening' });
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /calibrate voice/i })).toBeDisabled();
    });

    it('should set status to calibrating on click', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      await user.click(screen.getByRole('button', { name: /calibrate voice/i }));

      expect(useSessionStore.getState().status).toBe('calibrating');
    });
  });

  describe('manual question input', () => {
    beforeEach(() => {
      useSessionStore.setState({ status: 'listening' });
    });

    it('should show manual question input when listening', async () => {
      await renderSessionControls();
      expect(screen.getByLabelText(/ask a question manually/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/type a question/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /send question/i })).toBeInTheDocument();
    });

    it('should hide manual question input when not listening', async () => {
      useSessionStore.setState({ status: 'idle' });
      await renderSessionControls();
      expect(screen.queryByLabelText(/ask a question manually/i)).not.toBeInTheDocument();
    });

    it('should disable send button when input is empty', async () => {
      await renderSessionControls();
      expect(screen.getByRole('button', { name: /send question/i })).toBeDisabled();
    });

    it('should enable send button when input has text', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      await user.type(screen.getByPlaceholderText(/type a question/i), 'Test question');

      expect(screen.getByRole('button', { name: /send question/i })).not.toBeDisabled();
    });

    it('should send MANUAL_QUESTION message on click', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      await user.type(screen.getByPlaceholderText(/type a question/i), 'What is React?');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'MANUAL_QUESTION',
        data: { question: 'What is React?' },
      });
    });

    it('should clear input after sending', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Test question');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(input).toHaveValue('');
    });

    it('should send message on Enter key', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Enter test{Enter}');

      expect(mockSendMessage).toHaveBeenCalledWith({
        type: 'MANUAL_QUESTION',
        data: { question: 'Enter test' },
      });
    });

    it('should not send on Shift+Enter', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

      const input = screen.getByPlaceholderText(/type a question/i);
      await user.type(input, 'Test{Shift>}{Enter}{/Shift}more text');

      expect(mockSendMessage).not.toHaveBeenCalled();
    });

    it('should not send whitespace-only input', async () => {
      const user = userEvent.setup();
      await renderSessionControls();

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

      await renderSessionControls();

      await user.type(screen.getByPlaceholderText(/type a question/i), 'New question');
      await user.click(screen.getByRole('button', { name: /send question/i }));

      expect(useSessionStore.getState().currentAnswer).toBeNull();
    });
  });

  describe('status display', () => {
    it('should show listening status', async () => {
      useSessionStore.setState({ status: 'listening' });
      await renderSessionControls();
      expect(screen.getByText('Listening...')).toBeInTheDocument();
    });

    it('should show processing status', async () => {
      useSessionStore.setState({ status: 'processing' });
      await renderSessionControls();
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('should show calibrating status', async () => {
      useSessionStore.setState({ status: 'calibrating' });
      await renderSessionControls();
      expect(screen.getByText('Calibrating...')).toBeInTheDocument();
    });
  });
});
