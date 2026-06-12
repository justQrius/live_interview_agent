import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Provider } from '../store/sessionStore';

interface ApiKeyStatus {
  exists: boolean;
}

const PROVIDERS: { id: Provider; name: string; icon: string; color: string }[] = [
  { id: 'gemini', name: 'Google Gemini', icon: 'G', color: 'from-blue-500 to-cyan-500' },
  { id: 'groq', name: 'Groq', icon: 'GQ', color: 'from-orange-500 to-red-500' },
  { id: 'deepgram', name: 'Deepgram', icon: 'DG', color: 'from-green-500 to-emerald-500' },
  { id: 'openai', name: 'OpenAI', icon: 'OA', color: 'from-gray-600 to-gray-800' },
  { id: 'anthropic', name: 'Anthropic', icon: 'A', color: 'from-amber-500 to-orange-600' },
];

const ProviderRow: React.FC<{ provider: Provider; name: string; icon: string; color: string }> = ({ provider, name, icon, color }) => {
  const [input, setInput] = useState('');
  const [hasKey, setHasKey] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
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
            // Never log key material, even partially.
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
      setStatusMsg({ text: status.exists ? 'Saved' : 'Warning', type: status.exists ? 'success' : 'error' });
      setTimeout(() => setStatusMsg(null), 3000);
      console.log('[ProviderSettings] Dispatching apiKeyChanged event for provider:', provider);
      window.dispatchEvent(new CustomEvent('apiKeyChanged', { detail: { provider } }));
    } catch (err) {
      console.error('[ProviderSettings] Save failed:', err);
      setStatusMsg({ text: `Error`, type: 'error' });
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
      setStatusMsg({ text: `Error`, type: 'error' });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-4 rounded-xl border border-border bg-surface-elevated dark:bg-surface animate-pulse">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700"></div>
          <div className="flex-1">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded"></div>
            <div className="h-3 w-16 bg-gray-200 dark:bg-gray-700 rounded mt-2"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      hasKey 
        ? 'border-success/30 bg-success/5 dark:bg-success/10' 
        : 'border-border bg-surface-elevated dark:bg-surface hover:border-primary/30'
    }`}>
      <div className="flex items-start gap-3">
        {/* Provider Icon */}
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}>
          {icon}
        </div>
        
        {/* Provider Info & Input */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="font-medium text-text-primary">{name}</span>
              {hasKey && (
                <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-success/10 text-success rounded-full font-medium">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Active
                </span>
              )}
            </div>
            {statusMsg && (
              <span className={`text-xs font-medium ${statusMsg.type === 'success' ? 'text-success' : 'text-destructive'}`}>
                {statusMsg.text}
              </span>
            )}
          </div>
          
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={hasKey ? 'Enter new key to update' : `Enter API key`}
                className="w-full pl-3 pr-10 py-2 bg-surface dark:bg-surface-elevated border border-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text-secondary transition-colors"
                title={showPassword ? 'Hide key' : 'Show key'}
              >
                {showPassword ? (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
            
            <button
              onClick={handleSave}
              disabled={!input.trim() || isSaving}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all shadow-sm"
            >
              {isSaving ? (
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </span>
              ) : hasKey ? 'Update' : 'Save'}
            </button>
            
            {hasKey && (
              <button
                onClick={handleDelete}
                disabled={isSaving}
                className="p-2 text-destructive hover:bg-destructive/10 disabled:opacity-50 rounded-lg transition-colors"
                title="Delete key"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export const ProviderSettings: React.FC = () => {
  return (
    <div className="space-y-3 pt-2">
      {PROVIDERS.map((p) => (
        <ProviderRow key={p.id} provider={p.id} name={p.name} icon={p.icon} color={p.color} />
      ))}
    </div>
  );
};
