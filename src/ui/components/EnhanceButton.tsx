import React, { useState, useRef, useEffect } from 'react';
import { useSessionStore, EnhancementType } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

interface EnhanceOption {
  type: EnhancementType;
  label: string;
  icon: string;
  description: string;
}

const ENHANCE_OPTIONS: EnhanceOption[] = [
  {
    type: 'add_detail',
    label: 'Add More Detail',
    icon: '📝',
    description: 'Expand with more context from your documents',
  },
  {
    type: 'make_specific',
    label: 'Add Specifics',
    icon: '📊',
    description: 'Include metrics, numbers, and concrete examples',
  },
  {
    type: 'suggest_star',
    label: 'STAR Format',
    icon: '⭐',
    description: 'Restructure as a STAR story',
  },
  {
    type: 'adjust_tone',
    label: 'Adjust Tone',
    icon: '🎯',
    description: 'Make more confident or humble',
  },
  {
    type: 'shorten',
    label: 'Shorten',
    icon: '✂️',
    description: 'Condense to key points',
  },
];

interface EnhanceButtonProps {
  disabled?: boolean;
}

const EnhanceButton: React.FC<EnhanceButtonProps> = ({ disabled = false }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [tonePreference, setTonePreference] = useState<'confident' | 'humble'>('confident');
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const currentAnswer = useSessionStore((state) => state.currentAnswer);
  const currentTranscription = useSessionStore((state) => state.currentTranscription);
  const enhancement = useSessionStore((state) => state.enhancement);
  const startEnhancement = useSessionStore((state) => state.startEnhancement);
  
  const { sendMessage } = useWebSocket();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleEnhance = (type: EnhancementType) => {
    if (!currentAnswer?.answerText || !currentAnswer.isComplete) {
      return;
    }

    const question = currentTranscription?.text || currentAnswer.question || '';
    const answer = currentAnswer.answerText;

    // Update local state
    startEnhancement(type, question, answer);

    // Send message to sidecar
    sendMessage({
      type: 'ENHANCE_ANSWER',
      data: {
        enhancementType: type,
        originalQuestion: question,
        originalAnswer: answer,
        tonePreference: type === 'adjust_tone' ? tonePreference : undefined,
      },
    });

    setIsOpen(false);
  };

  const isDisabled = disabled || 
    !currentAnswer?.isComplete || 
    enhancement.isEnhancing ||
    !currentAnswer?.answerText;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isDisabled}
        className={`
          flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg
          transition-all duration-200
          ${isDisabled
            ? 'bg-surface-elevated dark:bg-surface text-text-muted cursor-not-allowed'
            : 'bg-primary/10 text-primary hover:bg-primary/20'
          }
        `}
        title={isDisabled ? 'Wait for answer to complete' : 'Enhance this answer'}
      >
        {enhancement.isEnhancing ? (
          <>
            <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span>Enhancing...</span>
          </>
        ) : (
          <>
            <svg 
              className="w-4 h-4" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M13 10V3L4 14h7v7l9-11h-7z" 
              />
            </svg>
            <span>Enhance</span>
            <svg 
              className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M19 9l-7 7-7-7" 
              />
            </svg>
          </>
        )}
      </button>

      {/* Dropdown Menu */}
      {isOpen && !isDisabled && (
        <div className="absolute right-0 mt-2 w-64 bg-surface dark:bg-surface-elevated rounded-xl shadow-lg border border-border z-50 overflow-hidden">
          <div className="p-2">
            <p className="text-xs text-text-muted px-2 py-1 uppercase font-semibold tracking-wide">
              Enhance Answer
            </p>
            
            {ENHANCE_OPTIONS.map((option) => (
              <div key={option.type}>
                <button
                  onClick={() => handleEnhance(option.type)}
                  className="w-full text-left px-3 py-2 rounded-lg hover:bg-primary/5 dark:hover:bg-primary/10 transition-colors group"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{option.icon}</span>
                    <div>
                      <p className="font-medium text-text-primary group-hover:text-primary">
                        {option.label}
                      </p>
                      <p className="text-xs text-text-muted">
                        {option.description}
                      </p>
                    </div>
                  </div>
                </button>

                {/* Tone selector for Adjust Tone option */}
                {option.type === 'adjust_tone' && (
                  <div className="ml-8 mt-1 mb-2 flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setTonePreference('confident');
                      }}
                      className={`px-2 py-1 text-xs rounded-md transition-colors ${
                        tonePreference === 'confident'
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'bg-surface-elevated dark:bg-surface text-text-secondary hover:bg-primary/5'
                      }`}
                    >
                      Confident
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setTonePreference('humble');
                      }}
                      className={`px-2 py-1 text-xs rounded-md transition-colors ${
                        tonePreference === 'humble'
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'bg-surface-elevated dark:bg-surface text-text-secondary hover:bg-primary/5'
                      }`}
                    >
                      Humble
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default EnhanceButton;
