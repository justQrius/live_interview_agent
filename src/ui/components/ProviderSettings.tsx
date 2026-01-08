import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Provider } from '../store/sessionStore';

interface ApiKeyStatus {
  exists: boolean;
}

const PROVIDERS: { id: Provider; name: string }[] = [
  { id: 'gemini', name: 'Google Gemini' },
  { id: 'groq', name: 'Groq' },
  { id: 'deepgram', name: 'Deepgram' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'anthropic', name: 'Anthropic' },
];

const ProviderRow: React.FC<{ provider: Provider; name: string }> = ({ provider, name }) => {
  const [input, setInput] = useState('');
  const [hasKey, setHasKey] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      console.log(`[ProviderSettings] Checking key status for ${provider}...`);
      const status = await invoke<ApiKeyStatus>('has_api_key', { provider });
      console.log(`[ProviderSettings] ${provider} key exists:`, status.exists);
      setHasKey(status.exists);
      if (status.exists) {
        try {
            const key = await invoke<string>('get_api_key', { provider });
            console.log(`[ProviderSettings] Retrieved ${provider} key:`, key.substring(0, 10) + '...');
            setInput(key);
        } catch (e) {
            console.error(`[ProviderSettings] Failed to retrieve ${provider} key:`, e);
        }
      }
    } catch (err) {
      console.error(`[ProviderSettings] Failed to check status for ${provider}:`, err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!input.trim()) return;
    setIsSaving(true);
    setStatusMsg(null);
    try {
      console.log('[ProviderSettings] Saving API key for provider:', provider);
      await invoke('set_api_key', { provider, key: input });
      console.log('[ProviderSettings] Save successful, checking if key exists...');
      
      const status = await invoke<ApiKeyStatus>('has_api_key', { provider });
      console.log('[ProviderSettings] Verification check result:', status);
      
      setHasKey(status.exists);
      setStatusMsg({ text: status.exists ? 'Saved & Verified' : 'Saved (Warning: Could not verify)', type: status.exists ? 'success' : 'error' });
      setTimeout(() => setStatusMsg(null), 3000);
      console.log('[ProviderSettings] Dispatching apiKeyChanged event for provider:', provider);
      window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }));
    } catch (err) {
      console.error('[ProviderSettings] Save failed:', err);
      setStatusMsg({ text: `Error: ${err}`, type: 'error' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsSaving(true);
    try {
      await invoke('delete_api_key', { provider });
      setHasKey(false);
      setInput('');
      setStatusMsg({ text: 'Deleted', type: 'success' });
      setTimeout(() => setStatusMsg(null), 3000);
      window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }));
    } catch (err) {
      setStatusMsg({ text: `Error: ${err}`, type: 'error' });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) return <div className="h-16 animate-pulse bg-gray-100 rounded"></div>;

  return (
    <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium text-gray-700">{name}</label>
        {statusMsg && (
          <span className={`text-xs ${statusMsg.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {statusMsg.text}
          </span>
        )}
      </div>
      <div className="flex gap-2">
        <input
          type="password"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={hasKey ? 'Key stored (enter new to update)' : `Enter ${name} API Key`}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <button
          onClick={handleSave}
          disabled={!input.trim() || isSaving}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium py-2 px-3 rounded-md transition"
        >
          {hasKey ? 'Update' : 'Save'}
        </button>
        {hasKey && (
          <button
            onClick={handleDelete}
            disabled={isSaving}
            className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white text-sm font-medium py-2 px-3 rounded-md transition"
          >
            Delete
          </button>
        )}
      </div>
      <div className="mt-1 flex items-center">
        <div className={`h-2 w-2 rounded-full mr-2 ${hasKey ? 'bg-green-500' : 'bg-gray-300'}`}></div>
        <span className="text-xs text-gray-500">{hasKey ? 'Active' : 'Not configured'}</span>
      </div>
    </div>
  );
};

export const ProviderSettings: React.FC = () => {
  return (
    <div className="space-y-3">
      {PROVIDERS.map((p) => (
        <ProviderRow key={p.id} provider={p.id} name={p.name} />
      ))}
    </div>
  );
};
