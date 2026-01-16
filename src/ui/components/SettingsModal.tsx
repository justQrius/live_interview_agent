import React, { useEffect } from 'react';
import SettingsPanel from './SettingsPanel';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  // Close on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      window.addEventListener('keydown', handleEscape);
    }
    
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 dark:bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 transition-opacity">
      {/* Click outside to close */}
      <div className="absolute inset-0" onClick={onClose} />
      
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto m-4 animate-in fade-in zoom-in-95 duration-200 scrollbar-thin">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-text-muted hover:text-text-primary bg-surface/50 dark:bg-surface-elevated/50 hover:bg-surface dark:hover:bg-surface-elevated backdrop-blur-md rounded-full transition-all z-10 border border-transparent hover:border-border"
          aria-label="Close settings"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <SettingsPanel />
      </div>
    </div>
  );
};

export default SettingsModal;
