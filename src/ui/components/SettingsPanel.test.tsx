import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPanel from './SettingsPanel';
import { useSessionStore } from '../store/sessionStore';

const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: null,
      currentTranscription: null,
      currentAnswer: null,
      answerHistory: [],
      loadedContextFiles: [],
      preferredSttProvider: 'auto',
      preferredLlmProvider: 'auto',
    });

    mockInvoke.mockImplementation((command: string, args: any) => {
      if (command === 'has_api_key') {
        return Promise.resolve({ exists: false });
      }
      if (command === 'get_api_key') {
        return Promise.resolve(`key-for-${args?.provider}`);
      }
      return Promise.resolve();
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Provider Settings', () => {
    it('should render all providers', async () => {
      render(<SettingsPanel />);
      // Wait for loading to finish
      await waitFor(() => {
          expect(screen.getByText('Google Gemini', { selector: 'label' })).toBeInTheDocument();
      });
      expect(screen.getByText('Groq', { selector: 'label' })).toBeInTheDocument();
      expect(screen.getByText('Deepgram', { selector: 'label' })).toBeInTheDocument();
      expect(screen.getByText('OpenAI', { selector: 'label' })).toBeInTheDocument();
      expect(screen.getByText('Anthropic', { selector: 'label' })).toBeInTheDocument();
    });

    it('should allow saving a key for a provider', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      const input = await screen.findByPlaceholderText('Enter Google Gemini API Key');
      await user.type(input, 'new-gemini-key');

      const saveButtons = screen.getAllByText('Save');
      await user.click(saveButtons[0]);

      expect(mockInvoke).toHaveBeenCalledWith('set_api_key', { 
        provider: 'gemini', 
        key: 'new-gemini-key' 
      });
    });

    it('should show saved status', async () => {
      mockInvoke.mockImplementation((command: string, args: any) => {
        if (command === 'has_api_key' && args?.provider === 'gemini') {
          return Promise.resolve({ exists: true });
        }
        if (command === 'get_api_key') {
          return Promise.resolve('some-fake-key');
        }
        return Promise.resolve({ exists: false });
      });

      render(<SettingsPanel />);
      
      await waitFor(() => {
         const activeStatus = screen.queryAllByText('Active');
         expect(activeStatus.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Preferences', () => {
    it('should render preference dropdowns', () => {
      render(<SettingsPanel />);
      expect(screen.getByText('Preferred STT Provider')).toBeInTheDocument();
      expect(screen.getByText('Preferred LLM Provider')).toBeInTheDocument();
    });

    it('should update store when preferences change', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      const selects = screen.getAllByRole('combobox');
      const sttSelect = selects[0];
      const llmSelect = selects[1];

      await user.selectOptions(sttSelect, 'openai');
      expect(useSessionStore.getState().preferredSttProvider).toBe('openai');

      await user.selectOptions(llmSelect, 'anthropic');
      expect(useSessionStore.getState().preferredLlmProvider).toBe('anthropic');
    });

    it('should sync apiKey when STT preference changes', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
          expect(mockInvoke).toHaveBeenCalledWith('get_api_key', { provider: 'gemini' });
      });

      const selects = screen.getAllByRole('combobox');
      await user.selectOptions(selects[0], 'openai');

      await waitFor(() => {
          expect(mockInvoke).toHaveBeenCalledWith('get_api_key', { provider: 'openai' });
      });
    });
  });

  describe('screen invisibility toggle', () => {
    it('should call toggle_screen_invisibility Tauri command', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await user.click(screen.getByTestId('screen-invisibility-toggle'));

      expect(mockInvoke).toHaveBeenCalledWith('toggle_screen_invisibility', { enabled: true });
    });
  });
});
