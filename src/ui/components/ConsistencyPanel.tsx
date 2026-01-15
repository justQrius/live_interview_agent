import { Contradiction } from '../store/sessionStore';

interface Props {
  warnings: Contradiction[];
  onDismiss: () => void;
}

export function ConsistencyPanel({ warnings, onDismiss }: Props) {
  if (warnings.length === 0) return null;

  return (
    <div className="bg-destructive/5 dark:bg-destructive/10 border border-destructive/20 rounded-xl overflow-hidden shadow-sm dark:shadow-none relative">
      {/* Header */}
      <div className="px-4 py-3 border-b border-destructive/20 bg-destructive/5 dark:bg-destructive/10">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-red-500 to-rose-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="font-semibold text-destructive">Consistency Alert</h3>
              <p className="text-xs text-text-muted">{warnings.length} potential contradiction{warnings.length > 1 ? 's' : ''} detected</p>
            </div>
          </div>
          <button 
            onClick={onDismiss}
            className="p-2 rounded-lg text-destructive/70 hover:text-destructive hover:bg-destructive/10 transition-colors"
            title="Dismiss warning"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      
      {/* Warnings */}
      <div className="p-4 space-y-3">
        {warnings.map((w, i) => (
          <div key={i} className="bg-surface dark:bg-surface-elevated p-4 rounded-xl border border-border">
            <p className="text-xs font-semibold uppercase tracking-wide text-destructive/80 mb-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-destructive"></span>
              {w.claim_type.replace('_', ' ')}
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-surface-elevated dark:bg-surface rounded-lg border border-border">
                <span className="text-xs text-text-muted block mb-1">Previously stated</span>
                <span className="text-sm font-medium text-text-primary">{w.existing}</span>
              </div>
              <div className="p-3 bg-destructive/5 dark:bg-destructive/10 rounded-lg border border-destructive/20">
                <span className="text-xs text-destructive/70 block mb-1">Just now</span>
                <span className="text-sm font-medium text-text-primary">{w.new}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
