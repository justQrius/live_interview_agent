import { StorySuggestion } from '../store/sessionStore';

interface Props {
  story: StorySuggestion;
}

export function StorySuggestionCard({ story }: Props) {
  return (
    <div className="bg-gradient-to-br from-indigo-900 to-slate-900 border-l-4 border-cyan-400 p-4 rounded-lg shadow-lg mb-4 text-white">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-lg text-cyan-300">{story.title}</h3>
        <span className="text-xs bg-indigo-800 px-2 py-1 rounded text-cyan-200">
          Match: {Math.round(story.relevanceScore * 100)}%
        </span>
      </div>
      
      <p className="text-sm text-gray-300 mb-3 line-clamp-3">{story.situation}</p>
      
      {story.keyMetrics.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {story.keyMetrics.map((m, i) => (
            <span key={i} className="text-xs bg-cyan-900/50 text-cyan-200 px-2 py-1 rounded border border-cyan-700/50">
              {m}
            </span>
          ))}
        </div>
      )}
      
      <div className="bg-black/20 p-3 rounded border border-indigo-800/50">
        <p className="text-xs text-indigo-300 uppercase mb-1 font-semibold tracking-wider">Suggested Opening</p>
        <p className="text-sm italic text-gray-200">"{story.suggestedOpening}"</p>
      </div>
    </div>
  );
}
