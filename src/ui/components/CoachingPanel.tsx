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
                className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 z-10"
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
              className="w-full text-left p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Show answer structure hint ({structureHint.name})
            </button>
          )}
        </div>
      )}
    </div>
  );
}
