import { useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { StorySuggestionCard } from './StorySuggestionCard';
import { StructureHintCard } from './StructureHintCard';
import { ConsistencyPanel } from './ConsistencyPanel';

export function CoachingPanel() {
  const storySuggestion = useSessionStore(state => state.storySuggestion);
  const structureHint = useSessionStore(state => state.structureHint);
  const consistencyWarnings = useSessionStore(state => state.consistencyWarnings);
  const setConsistencyWarnings = useSessionStore(state => state.setConsistencyWarnings);
  
  // Allow user to hide structure hints if not needed
  const [showStructureHint, setShowStructureHint] = useState(true);

  const hasContent = storySuggestion || (structureHint && showStructureHint) || consistencyWarnings.length > 0;

  // Show toggle even if there's no content currently, if structureHint exists
  const showToggle = structureHint !== null;

  if (!hasContent && !showToggle) return null;

  return (
    <div className="space-y-4 animate-fadeIn">
      {consistencyWarnings.length > 0 && (
        <ConsistencyPanel 
          warnings={consistencyWarnings} 
          onDismiss={() => setConsistencyWarnings([])} 
        />
      )}
      
      {storySuggestion && (
        <StorySuggestionCard story={storySuggestion} />
      )}
      
      {structureHint && (
        <div>
          {showStructureHint ? (
            <div className="relative">
              <button
                onClick={() => setShowStructureHint(false)}
                className="absolute top-3 right-3 p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-elevated dark:hover:bg-surface transition-colors z-10"
                title="Hide structure hint"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <StructureHintCard hint={structureHint} />
            </div>
          ) : (
            <button
              onClick={() => setShowStructureHint(true)}
              className="w-full text-left p-4 bg-surface dark:bg-surface-elevated border border-border rounded-xl text-sm text-text-secondary hover:bg-surface-elevated dark:hover:bg-surface hover:text-text-primary transition-all flex items-center gap-3 group"
            >
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
              <span>Show answer structure hint ({structureHint.name})</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
