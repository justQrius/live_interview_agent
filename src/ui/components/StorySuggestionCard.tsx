import { StorySuggestion } from '../store/sessionStore';

interface Props {
  story: StorySuggestion;
}

export function StorySuggestionCard({ story }: Props) {
  const relevancePercent = Math.round(story.relevanceScore * 100);
  
  return (
    <div className="bg-surface dark:bg-surface-elevated border border-border rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      {/* Header with gradient accent */}
      <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-500 p-[1px]">
        <div className="bg-surface dark:bg-surface-elevated px-4 py-3">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-text-primary">{story.title}</h3>
                <span className="text-xs text-text-muted">Relevant Story</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative w-10 h-10">
                <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18" cy="18" r="15"
                    fill="none"
                    className="stroke-surface-elevated dark:stroke-surface"
                    strokeWidth="3"
                  />
                  <circle
                    cx="18" cy="18" r="15"
                    fill="none"
                    className="stroke-cyan-500"
                    strokeWidth="3"
                    strokeDasharray={`${relevancePercent} 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-cyan-500">
                  {relevancePercent}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="p-4 space-y-4">
        <p className="text-sm text-text-secondary line-clamp-3">{story.situation}</p>
        
        {story.keyMetrics.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {story.keyMetrics.map((m, i) => (
              <span 
                key={i} 
                className="text-xs px-2.5 py-1 rounded-full bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 font-medium"
              >
                {m}
              </span>
            ))}
          </div>
        )}
        
        {/* Suggested Opening */}
        <div className="bg-surface-elevated dark:bg-surface p-4 rounded-xl border border-border">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Suggested Opening</span>
          </div>
          <p className="text-sm italic text-text-primary">"{story.suggestedOpening}"</p>
        </div>
      </div>
    </div>
  );
}
