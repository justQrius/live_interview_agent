import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSessionStore, Provider } from '../store/sessionStore';
import { ProviderSettings } from './ProviderSettings';

const SettingsPanel: React.FC = () => {
  const [error, setError] = useState<string | null>(null);

  const isScreenInvisible = useSessionStore((state) => state.isScreenInvisible);
  const setScreenInvisibility = useSessionStore((state) => state.setScreenInvisibility);
  const preferredSttProvider = useSessionStore((state) => state.preferredSttProvider);
  const preferredLlmProvider = useSessionStore((state) => state.preferredLlmProvider);
  const setPreferredSttProvider = useSessionStore((state) => state.setPreferredSttProvider);
  const setPreferredLlmProvider = useSessionStore((state) => state.setPreferredLlmProvider);
  const setApiKey = useSessionStore((state) => state.setApiKey);

  // Sync the active API key based on STT preference (Primary key for session)
  // This ensures SessionControls continues to work with the selected provider
  useEffect(() => {
    const syncKey = async () => {
        // Default to gemini if auto
        const provider = preferredSttProvider === 'auto' ? 'gemini' : preferredSttProvider;
        try {
            const key = await invoke<string>('get_api_key', { provider });
            setApiKey(key);
        } catch (e) {
            console.warn(`Could not load key for ${provider}:`, e);
            // If we can't get the key, clear it so SessionControls knows configuration is missing
            setApiKey(null);
        }
    };
    syncKey();
  }, [preferredSttProvider, setApiKey]);

  const handleToggleScreenInvisibility = async () => {
    const newValue = !isScreenInvisible;
    try {
      await invoke('toggle_screen_invisibility', { enabled: newValue });
      setScreenInvisibility(newValue);
    } catch (err) {
      console.error('Failed to toggle screen invisibility:', err);
      setError(`Failed to toggle screen invisibility: ${err}`);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6" data-testid="settings-panel">
      <h2 className="text-xl font-semibold mb-4">Settings</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-lg" role="alert">
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* Provider Configuration */}
        <div>
           <ProviderSettings />
        </div>

        <hr className="border-gray-200" />

        {/* Preferences */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
             <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Preferred STT Provider</label>
                <select
                    value={preferredSttProvider}
                    onChange={(e) => setPreferredSttProvider(e.target.value as Provider | 'auto')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="auto">Auto (Default)</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="groq">Groq</option>
                    <option value="deepgram">Deepgram</option>
                    <option value="openai">OpenAI</option>
                </select>
             </div>
             <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Preferred LLM Provider</label>
                <select
                    value={preferredLlmProvider}
                    onChange={(e) => setPreferredLlmProvider(e.target.value as Provider | 'auto')}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="auto">Auto (Default)</option>
                    <option value="gemini">Google Gemini</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="openai">OpenAI</option>
                </select>
             </div>
        </div>

        <hr className="border-gray-200" />

        {/* Screen Invisibility */}
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">Screen Invisibility</label>
          <button
            onClick={handleToggleScreenInvisibility}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              isScreenInvisible ? 'bg-blue-600' : 'bg-gray-300'
            }`}
            data-testid="screen-invisibility-toggle"
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isScreenInvisible ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {isScreenInvisible && (
          <p className="text-xs text-blue-600">
            App will be hidden from screen sharing and recordings
          </p>
        )}
      </div>
    </div>
  );
};

export default SettingsPanel;
