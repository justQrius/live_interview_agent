import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useSessionStore, Provider } from '../store/sessionStore';
import { ProviderSettings } from './ProviderSettings';

interface AccordionSectionProps {
  title: string;
  icon: React.ReactNode;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const AccordionSection: React.FC<AccordionSectionProps> = ({ title, icon, isOpen, onToggle, children }) => (
  <div className="border border-border rounded-xl overflow-hidden bg-surface dark:bg-surface">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-4 text-left hover:bg-surface-elevated/50 dark:hover:bg-surface-elevated/30 transition-colors"
    >
      <div className="flex items-center gap-3">
        <span className="text-primary">{icon}</span>
        <span className="font-medium text-text-primary">{title}</span>
      </div>
      <svg
        className={`w-5 h-5 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    <div
      className={`transition-all duration-200 ease-in-out ${
        isOpen ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0 overflow-hidden'
      }`}
    >
      <div className="p-4 pt-0 border-t border-border">{children}</div>
    </div>
  </div>
);

const SettingsPanel: React.FC = () => {
  const [error, setError] = useState<string | null>(null);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    providers: true,
    preferences: true,
    privacy: false,
  });

  const isScreenInvisible = useSessionStore((state) => state.isScreenInvisible);
  const setScreenInvisibility = useSessionStore((state) => state.setScreenInvisibility);
  const preferredSttProvider = useSessionStore((state) => state.preferredSttProvider);
  const preferredLlmProvider = useSessionStore((state) => state.preferredLlmProvider);
  const setPreferredSttProvider = useSessionStore((state) => state.setPreferredSttProvider);
  const setPreferredLlmProvider = useSessionStore((state) => state.setPreferredLlmProvider);
  const setApiKey = useSessionStore((state) => state.setApiKey);

  useEffect(() => {
    const syncKey = async () => {
        const provider = preferredSttProvider === 'auto' ? 'gemini' : preferredSttProvider;
        try {
            const key = await invoke<string>('get_api_key', { provider });
            setApiKey(key);
        } catch (e) {
            console.warn(`Could not load key for ${provider}:`, e);
            setApiKey(null);
        }
    };
    
    syncKey();

    const handleApiKeyChange = () => {
      syncKey();
    };

    window.addEventListener('apiKeyChanged', handleApiKeyChange);
    return () => window.removeEventListener('apiKeyChanged', handleApiKeyChange);
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

  const toggleSection = (section: string) => {
    setOpenSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="bg-surface rounded-2xl shadow-lg dark:shadow-none border border-border p-6" data-testid="settings-panel">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text-primary">Settings</h2>
          <p className="text-sm text-text-muted">Configure your AI providers and preferences</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-destructive/10 border border-destructive/30 text-destructive rounded-xl flex items-center gap-3" role="alert">
          <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm">{error}</span>
        </div>
      )}

      <div className="space-y-3">
        {/* API Keys Section */}
        <AccordionSection
          title="API Keys"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          }
          isOpen={openSections.providers}
          onToggle={() => toggleSection('providers')}
        >
          <ProviderSettings />
        </AccordionSection>

        {/* Preferences Section */}
        <AccordionSection
          title="Provider Preferences"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
          }
          isOpen={openSections.preferences}
          onToggle={() => toggleSection('preferences')}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">Speech-to-Text</label>
              <select
                value={preferredSttProvider}
                onChange={(e) => setPreferredSttProvider(e.target.value as Provider | 'auto')}
                className="w-full px-4 py-2.5 bg-surface-elevated dark:bg-surface border border-border rounded-xl text-text-primary focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
              >
                <option value="auto">Auto (Default)</option>
                <option value="gemini">Google Gemini</option>
                <option value="groq">Groq</option>
                <option value="deepgram">Deepgram</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">Language Model</label>
              <select
                value={preferredLlmProvider}
                onChange={(e) => setPreferredLlmProvider(e.target.value as Provider | 'auto')}
                className="w-full px-4 py-2.5 bg-surface-elevated dark:bg-surface border border-border rounded-xl text-text-primary focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
              >
                <option value="auto">Auto (Default)</option>
                <option value="gemini">Google Gemini</option>
                <option value="anthropic">Anthropic</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
          </div>
        </AccordionSection>

        {/* Privacy Section */}
        <AccordionSection
          title="Privacy & Security"
          icon={
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          }
          isOpen={openSections.privacy}
          onToggle={() => toggleSection('privacy')}
        >
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between p-4 bg-surface-elevated dark:bg-surface rounded-xl border border-border">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">Screen Invisibility</span>
                  {isScreenInvisible && (
                    <span className="text-xs px-2 py-0.5 bg-success/10 text-success rounded-full font-medium">Active</span>
                  )}
                </div>
                <p className="text-sm text-text-muted mt-1">
                  Hide this app from screen sharing and recordings
                </p>
              </div>
              <button
                onClick={handleToggleScreenInvisibility}
                className={`relative inline-flex h-7 w-12 items-center rounded-full transition-colors ${
                  isScreenInvisible 
                    ? 'bg-gradient-to-r from-blue-500 to-blue-600' 
                    : 'bg-surface-elevated dark:bg-gray-700 border border-border'
                }`}
                data-testid="screen-invisibility-toggle"
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-transform ${
                    isScreenInvisible ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            <div className="p-4 bg-blue-500/5 dark:bg-blue-500/10 rounded-xl border border-blue-500/20">
              <div className="flex gap-3">
                <svg className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-text-secondary">
                  API keys are stored securely in your operating system's keychain. They never leave your device.
                </p>
              </div>
            </div>
          </div>
        </AccordionSection>
      </div>
    </div>
  );
};

export default SettingsPanel;
