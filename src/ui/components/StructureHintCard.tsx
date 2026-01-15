import { StructureHint } from '../store/sessionStore';

interface Props {
  hint: StructureHint;
}

export function StructureHintCard({ hint }: Props) {
  return (
    <div className="bg-surface dark:bg-surface-elevated border border-border rounded-xl overflow-hidden shadow-sm dark:shadow-none">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-surface-elevated/50 dark:bg-surface/50">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
              </svg>
            </div>
            <h3 className="font-semibold text-text-primary">{hint.name}</h3>
          </div>
          <span className="text-xs px-2.5 py-1 bg-violet-500/10 text-violet-600 dark:text-violet-400 rounded-full font-medium border border-violet-500/20">
            Framework
          </span>
        </div>
      </div>
      
      {/* Sections */}
      <div className="p-4 space-y-2">
        {hint.sections.map((section, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-surface-elevated/50 dark:bg-surface/50 border border-border/50">
            <span className="text-xs font-mono text-text-muted bg-surface dark:bg-surface-elevated px-2 py-1 rounded border border-border min-w-[48px] text-center">
              {section.percentage}
            </span>
            <div className="flex-1 min-w-0">
              <span className="font-medium text-sm text-text-primary">{section.name}</span>
              <span className="text-sm text-text-muted mx-1">-</span>
              <span className="text-sm text-text-secondary">{section.description}</span>
            </div>
          </div>
        ))}
      </div>
      
      {/* Pro Tips */}
      <div className="mx-4 mb-4 p-4 bg-amber-500/5 dark:bg-amber-500/10 rounded-xl border border-amber-500/20">
        <div className="flex items-center gap-2 mb-2">
          <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wider">Pro Tips</span>
        </div>
        <ul className="space-y-1.5">
          {hint.tips.slice(0, 2).map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-text-secondary">
              <svg className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
