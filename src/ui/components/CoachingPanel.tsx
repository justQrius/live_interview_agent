import { useSessionStore } from '../store/sessionStore';
import { StorySuggestionCard } from './StorySuggestionCard';
import { StructureHintCard } from './StructureHintCard';
import { ConsistencyPanel } from './ConsistencyPanel';

export function CoachingPanel() {
  const storySuggestion = useSessionStore(state => state.storySuggestion);
  const structureHint = useSessionStore(state => state.structureHint);
  const consistencyWarnings = useSessionStore(state => state.consistencyWarnings);
  const setConsistencyWarnings = useSessionStore(state => state.setConsistencyWarnings);

  const hasContent = storySuggestion || structureHint || consistencyWarnings.length > 0;

  if (!hasContent) return null;

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
        <StructureHintCard hint={structureHint} />
      )}
    </div>
  );
}
