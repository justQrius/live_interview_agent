import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SettingsPanel from './SettingsPanel';
import { useSessionStore } from '../store/sessionStore';

// Mock Tauri invoke
const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => mockInvoke(...args),
}));

describe('SettingsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset store state
    useSessionStore.setState({
      status: 'idle',
      isScreenInvisible: false,
      voiceProfileActive: false,
      apiKey: null,
      currentTranscription: null,
      currentAnswer: null,
      answerHistory: [],
      loadedContextFiles: [],
    });
    // Default mock: no API key stored
    mockInvoke.mockImplementation((command: string) => {
      if (command === 'has_api_key') {
        return Promise.resolve({ exists: false });
      }
      return Promise.resolve();
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('initial loading', () => {
    it('should show loading state initially', () => {
      render(<SettingsPanel />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('should check API key status on mount', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(mockInvoke).toHaveBeenCalledWith('has_api_key');
      });
    });

    it('should show settings form after loading', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByTestId('api-key-input')).toBeInTheDocument();
      expect(screen.getByTestId('save-api-key-button')).toBeInTheDocument();
    });
  });

  describe('when no API key is stored', () => {
    it('should show correct placeholder text', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input') as HTMLInputElement;
      expect(input.placeholder).toBe('Enter your API key');
    });

    it('should show "Save API Key" button text', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByTestId('save-api-key-button')).toHaveTextContent('Save API Key');
    });

    it('should not show delete button', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.queryByTestId('delete-api-key-button')).not.toBeInTheDocument();
    });

    it('should disable save button when input is empty', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByTestId('save-api-key-button')).toBeDisabled();
    });
  });

  describe('when API key is stored', () => {
    beforeEach(() => {
      mockInvoke.mockImplementation((command: string) => {
        if (command === 'has_api_key') {
          return Promise.resolve({ exists: true });
        }
        if (command === 'get_api_key') {
          return Promise.resolve('stored-api-key-123');
        }
        return Promise.resolve();
      });
    });

    it('should load and set API key in store', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(mockInvoke).toHaveBeenCalledWith('get_api_key');
      });

      expect(useSessionStore.getState().apiKey).toBe('stored-api-key-123');
    });

    it('should show "Update API Key" button text', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByTestId('save-api-key-button')).toHaveTextContent('Update API Key');
    });

    it('should show delete button', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(screen.getByTestId('delete-api-key-button')).toBeInTheDocument();
    });

    it('should show correct placeholder text', async () => {
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input') as HTMLInputElement;
      expect(input.placeholder).toBe('Enter new key to replace');
    });
  });

  describe('saving API key', () => {
    it('should call set_api_key with the input value', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input');
      await user.type(input, 'new-test-key');

      const saveButton = screen.getByTestId('save-api-key-button');
      await user.click(saveButton);

      expect(mockInvoke).toHaveBeenCalledWith('set_api_key', { key: 'new-test-key' });
    });

    it('should update store with new API key', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input');
      await user.type(input, 'new-test-key');
      await user.click(screen.getByTestId('save-api-key-button'));

      await waitFor(() => {
        expect(useSessionStore.getState().apiKey).toBe('new-test-key');
      });
    });

    it('should show success message after saving', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input');
      await user.type(input, 'new-test-key');
      await user.click(screen.getByTestId('save-api-key-button'));

      await waitFor(() => {
        expect(screen.getByRole('status')).toHaveTextContent('API key saved securely');
      });
    });

    it('should clear input after saving', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input') as HTMLInputElement;
      await user.type(input, 'new-test-key');
      await user.click(screen.getByTestId('save-api-key-button'));

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });

    it('should allow saving with Enter key', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input');
      await user.type(input, 'enter-key-test{Enter}');

      expect(mockInvoke).toHaveBeenCalledWith('set_api_key', { key: 'enter-key-test' });
    });

    it('should show error message on save failure', async () => {
      mockInvoke.mockImplementation((command: string) => {
        if (command === 'has_api_key') {
          return Promise.resolve({ exists: false });
        }
        if (command === 'set_api_key') {
          return Promise.reject('Keychain access denied');
        }
        return Promise.resolve();
      });

      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      const input = screen.getByTestId('api-key-input');
      await user.type(input, 'new-test-key');
      await user.click(screen.getByTestId('save-api-key-button'));

      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent('Failed to save API key');
      });
    });
  });

  describe('deleting API key', () => {
    beforeEach(() => {
      mockInvoke.mockImplementation((command: string) => {
        if (command === 'has_api_key') {
          return Promise.resolve({ exists: true });
        }
        if (command === 'get_api_key') {
          return Promise.resolve('stored-api-key-123');
        }
        return Promise.resolve();
      });
    });

    it('should call delete_api_key when delete button clicked', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      await user.click(screen.getByTestId('delete-api-key-button'));

      expect(mockInvoke).toHaveBeenCalledWith('delete_api_key');
    });

    it('should clear API key from store after deletion', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(useSessionStore.getState().apiKey).toBe('stored-api-key-123');
      });

      await user.click(screen.getByTestId('delete-api-key-button'));

      await waitFor(() => {
        expect(useSessionStore.getState().apiKey).toBeNull();
      });
    });

    it('should show success message after deletion', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      await user.click(screen.getByTestId('delete-api-key-button'));

      await waitFor(() => {
        expect(screen.getByRole('status')).toHaveTextContent('API key removed');
      });
    });

    it('should hide delete button after deletion', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      await user.click(screen.getByTestId('delete-api-key-button'));

      await waitFor(() => {
        expect(screen.queryByTestId('delete-api-key-button')).not.toBeInTheDocument();
      });
    });
  });

  describe('screen invisibility toggle', () => {
    it('should toggle screen invisibility state', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      expect(useSessionStore.getState().isScreenInvisible).toBe(false);

      await user.click(screen.getByTestId('screen-invisibility-toggle'));

      expect(useSessionStore.getState().isScreenInvisible).toBe(true);
    });

    it('should show info text when enabled', async () => {
      const user = userEvent.setup();
      render(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
      });

      await user.click(screen.getByTestId('screen-invisibility-toggle'));

      expect(screen.getByText(/hidden from screen sharing/i)).toBeInTheDocument();
    });
  });
});
