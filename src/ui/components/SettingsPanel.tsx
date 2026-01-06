import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSessionStore } from '../store/sessionStore';

interface ApiKeyStatus {
  exists: boolean;
}

const SettingsPanel: React.FC = () => {
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasStoredKey, setHasStoredKey] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isScreenInvisible = useSessionStore((state) => state.isScreenInvisible);
  const setScreenInvisibility = useSessionStore((state) => state.setScreenInvisibility);
  const setApiKey = useSessionStore((state) => state.setApiKey);

  useEffect(() => {
    checkApiKeyStatus();
  }, []);

  const checkApiKeyStatus = async () => {
    setIsLoading(true);
    try {
      const status = await invoke<ApiKeyStatus>('has_api_key');
      setHasStoredKey(status.exists);
      if (status.exists) {
        // Load the key into session store for use by the app
        const key = await invoke<string>('get_api_key');
        setApiKey(key);
      }
    } catch (err) {
      console.error('Failed to check API key status:', err);
      setError('Failed to check API key status');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveApiKey = async () => {
    if (!apiKeyInput.trim()) return;

    setIsSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await invoke('set_api_key', { key: apiKeyInput });
      setApiKey(apiKeyInput);
      setHasStoredKey(true);
      setApiKeyInput('');
      setSuccessMessage('API key saved securely to OS keychain');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to save API key:', err);
      setError(`Failed to save API key: ${err}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteApiKey = async () => {
    setError(null);
    setSuccessMessage(null);

    try {
      await invoke('delete_api_key');
      setApiKey(null);
      setHasStoredKey(false);
      setSuccessMessage('API key removed from OS keychain');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to delete API key:', err);
      setError(`Failed to delete API key: ${err}`);
    }
  };

  const handleToggleScreenInvisibility = async () => {
    const newValue = !isScreenInvisible;
    try {
      // TODO: Call Tauri command to toggle screen invisibility (STORY-015)
      // await invoke('toggle_screen_invisibility', { enabled: newValue });
      console.log('Screen invisibility toggle not implemented yet (STORY-015)');
      setScreenInvisibility(newValue);
    } catch (err) {
      console.error('Failed to toggle screen invisibility:', err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && apiKeyInput.trim() && !isSaving) {
      handleSaveApiKey();
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6" data-testid="settings-panel">
        <h2 className="text-xl font-semibold mb-4">Settings</h2>
        <div className="text-gray-500">Loading...</div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6" data-testid="settings-panel">
      <h2 className="text-xl font-semibold mb-4">Settings</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-300 text-red-700 rounded-lg" role="alert">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-3 bg-green-100 border border-green-300 text-green-700 rounded-lg" role="status">
          {successMessage}
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Gemini API Key
          </label>
          <input
            type="password"
            value={apiKeyInput}
            onChange={(e) => setApiKeyInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={hasStoredKey ? 'Enter new key to replace' : 'Enter your API key'}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            data-testid="api-key-input"
          />
          <p className="text-xs text-gray-500 mt-1">
            {hasStoredKey
              ? 'API key stored securely in OS keychain'
              : 'Will be stored securely in OS keychain'}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSaveApiKey}
            disabled={!apiKeyInput.trim() || isSaving}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200"
            data-testid="save-api-key-button"
          >
            {isSaving ? 'Saving...' : hasStoredKey ? 'Update API Key' : 'Save API Key'}
          </button>

          {hasStoredKey && (
            <button
              onClick={handleDeleteApiKey}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg transition duration-200"
              data-testid="delete-api-key-button"
            >
              Delete
            </button>
          )}
        </div>

        <hr className="my-4" />

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
