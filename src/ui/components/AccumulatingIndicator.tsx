import { useSessionStore } from '../store/sessionStore';

/**
 * AccumulatingIndicator - Shows when the system is buffering multi-segment speech
 * 
 * Phase 6: Utterance Accumulation
 * Displays a subtle indicator when the accumulator is collecting speech segments
 * before they're complete enough for question detection.
 */
export function AccumulatingIndicator() {
  const accumulating = useSessionStore((state) => state.accumulating);

  if (!accumulating.isAccumulating) {
    return null;
  }

  // Truncate preview to reasonable length for display
  const preview = accumulating.bufferPreview 
    ? (accumulating.bufferPreview.length > 60 
        ? accumulating.bufferPreview.slice(0, 60) + '...' 
        : accumulating.bufferPreview)
    : '';

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-amber-500/10 dark:bg-amber-500/5 border border-amber-500/20 rounded-lg animate-pulse">
      {/* Listening Icon with Animation */}
      <div className="relative flex-shrink-0">
        <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center">
          <svg 
            className="w-4 h-4 text-amber-500" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" 
            />
          </svg>
        </div>
        {/* Pulsing ring */}
        <div className="absolute inset-0 rounded-full border-2 border-amber-500/50 animate-ping" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
            Listening to {accumulating.speaker || 'speaker'}...
          </span>
          <span className="text-xs text-text-muted">
            ({accumulating.segmentCount} segment{accumulating.segmentCount !== 1 ? 's' : ''}, {accumulating.durationSeconds.toFixed(1)}s)
          </span>
        </div>
        
        {/* Preview of buffered text */}
        {preview && (
          <p className="text-sm text-text-secondary truncate mt-0.5 italic">
            "{preview}"
          </p>
        )}
      </div>

      {/* Segment dots visualization */}
      <div className="flex items-center gap-1 flex-shrink-0">
        {Array.from({ length: Math.min(accumulating.segmentCount, 5) }).map((_, i) => (
          <div 
            key={i} 
            className="w-1.5 h-1.5 rounded-full bg-amber-500"
            style={{ 
              opacity: 0.4 + (i * 0.15),
              animationDelay: `${i * 100}ms` 
            }}
          />
        ))}
        {accumulating.segmentCount > 5 && (
          <span className="text-xs text-amber-500 ml-1">+{accumulating.segmentCount - 5}</span>
        )}
      </div>
    </div>
  );
}
