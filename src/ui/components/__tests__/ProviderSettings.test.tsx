import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProviderSettings } from '../ProviderSettings';

// Mock the Tauri invoke function
const mockInvoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: any[]) => {
    console.log('Mock invoke called with:', args);
    return mockInvoke(...args);
  },
}));

describe('ProviderSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock implementation
    mockInvoke.mockImplementation((cmd, _args) => {
      console.log('Mock implementation for:', cmd);
      if (cmd === 'has_api_key') {
        return Promise.resolve({ exists: false });
      }
      if (cmd === 'get_api_key') {
        return Promise.reject('Not found');
      }
      return Promise.resolve();
    });
  });

  it('renders all provider inputs', async () => {
    render(<ProviderSettings />);
    
    // Use findByText which waits for the element to appear
    expect(await screen.findByText('Google Gemini', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByText('Groq')).toBeInTheDocument();
    expect(screen.getByText('Deepgram')).toBeInTheDocument();
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('allows saving an API key', async () => {
    render(<ProviderSettings />);
    
    // Wait for loading to finish by finding one of the inputs
    const input = await screen.findByPlaceholderText('Enter OpenAI API Key', {}, { timeout: 3000 });
    expect(input).toBeInTheDocument();

    // Find input for OpenAI
    const inputs = screen.getAllByPlaceholderText(/Enter.*API Key/);
    const openaiInput = inputs[3]; // OpenAI is 4th in the list
    
    fireEvent.change(openaiInput, { target: { value: 'sk-test-key' } });
    
    const saveButtons = screen.getAllByText('Save');
    const openaiSave = saveButtons[3];
    
    // Update mock to handle the save and subsequent check
    mockInvoke.mockImplementation((cmd, args) => {
        if (cmd === 'set_api_key') return Promise.resolve();
        if (cmd === 'has_api_key' && args?.provider === 'openai') return Promise.resolve({ exists: true });
        // Default for other calls
        return Promise.resolve({ exists: false });
    });
             
    fireEvent.click(openaiSave);
    
    await waitFor(() => {
      expect(mockInvoke).toHaveBeenCalledWith('set_api_key', {
        provider: 'openai',
        key: 'sk-test-key'
      });
    });
    
    // Wait for the UI to update to "Update" button
    await waitFor(() => {
        const updateButtons = screen.getAllByText('Update');
        expect(updateButtons.length).toBeGreaterThan(0);
    });
  });

  it('shows existing keys as configured', async () => {
    // Mock that Groq key exists
    mockInvoke.mockImplementation((cmd, args) => {
      if (cmd === 'has_api_key' && args?.provider === 'groq') {
        return Promise.resolve({ exists: true });
      }
      if (cmd === 'get_api_key' && args?.provider === 'groq') {
        return Promise.resolve('gsk-existing-key');
      }
      return Promise.resolve({ exists: false });
    });

    render(<ProviderSettings />);

    await waitFor(() => {
        const updateButtons = screen.getAllByText('Update');
        expect(updateButtons.length).toBeGreaterThan(0);
        expect(screen.getByText('Active')).toBeInTheDocument();
    });
  });
});
