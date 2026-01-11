import { Contradiction } from '../store/sessionStore';

interface Props {
  warnings: Contradiction[];
  onDismiss: () => void;
}

export function ConsistencyPanel({ warnings, onDismiss }: Props) {
  if (warnings.length === 0) return null;

  return (
    <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg shadow-md mb-4 relative">
      <button 
        onClick={onDismiss}
        className="absolute top-2 right-2 text-red-400 hover:text-red-600"
        title="Dismiss warning"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
      
      <div className="flex items-center gap-2 mb-2">
        <span className="text-red-500 text-xl">⚠️</span>
        <h3 className="font-bold text-red-700">Consistency Check</h3>
      </div>
      
      <div className="space-y-2">
        {warnings.map((w, i) => (
          <div key={i} className="text-sm text-red-800 bg-red-100/50 p-2 rounded">
            <p className="font-semibold text-xs uppercase tracking-wide text-red-600 mb-1">{w.claim_type.replace('_', ' ')}</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-red-500 block">Previously:</span>
                <span className="font-medium">{w.existing}</span>
              </div>
              <div>
                <span className="text-red-500 block">Just now:</span>
                <span className="font-medium">{w.new}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
