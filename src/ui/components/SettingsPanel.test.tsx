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
    it('should render all providers in API Keys section', async () => {
      render(<SettingsPanel />);
      // Wait for loading to finish - use getAllByText since names appear in dropdowns too
      await waitFor(() => {
          const geminiElements = screen.getAllByText('Google Gemini');
          expect(geminiElements.length).toBeGreaterThan(0);
      });
      // Check that API Keys section exists and contains providers
      expect(screen.getByText('API Keys')).toBeInTheDocument();
      expect(screen.getAllByText('Groq').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Deepgram').length).toBeGreaterThan(0);
      expect(screen.getAllByText('OpenAI').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Anthropic').length).toBeGreaterThan(0);
    });

    it('should allow saving a key for a provider', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      // Placeholder is now just "Enter API key" (generic) - wait for providers to load
      const inputs = await screen.findAllByPlaceholderText('Enter API key');
      await user.type(inputs[0], 'new-gemini-key');

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
    it('should render preference section', () => {
      render(<SettingsPanel />);
      // The section is now titled "Provider Preferences" and labels are different
      expect(screen.getByText('Provider Preferences')).toBeInTheDocument();
      expect(screen.getByText('Language Model (LLM)')).toBeInTheDocument();
      expect(screen.getByText('Speech-to-Text (Batch)')).toBeInTheDocument();
    });

    it('should update store when LLM preference changes', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      // Wait for API key inputs to load (provider rows loaded)
      await waitFor(() => {
        expect(screen.getAllByPlaceholderText('Enter API key').length).toBeGreaterThan(0);
      });

      // Get all comboboxes - structure is: LLM Provider, LLM Model, STT Provider, STT Model, Streaming Provider, Streaming Model
      const selects = screen.getAllByRole('combobox');
      const llmProviderSelect = selects[0]; // First select is LLM provider
      const sttProviderSelect = selects[2]; // Third select is STT provider

      await user.selectOptions(llmProviderSelect, 'anthropic');
      expect(useSessionStore.getState().preferredLlmProvider).toBe('anthropic');

      await user.selectOptions(sttProviderSelect, 'openai');
      expect(useSessionStore.getState().preferredSttProvider).toBe('openai');
    });

    it('should sync apiKey when STT preference changes', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      // Initially loads gemini key (default when preferredSttProvider is 'auto')
      await waitFor(() => {
          expect(mockInvoke).toHaveBeenCalledWith('get_api_key', { provider: 'gemini' });
      });

      // Wait for API key inputs to load (provider rows loaded)
      await waitFor(() => {
        expect(screen.getAllByPlaceholderText('Enter API key').length).toBeGreaterThan(0);
      });

      // Get STT provider select (third combobox)
      const selects = screen.getAllByRole('combobox');
      const sttProviderSelect = selects[2];
      
      await user.selectOptions(sttProviderSelect, 'openai');

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
