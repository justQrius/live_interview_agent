interface PreparationSummaryProps {
  summary: string | null;
  isExpanded: boolean;
  onToggle: () => void;
}

function renderMarkdown(text: string): string {
  if (!text) return '';
  
  return text
    .replace(/^### (.+)$/gm, '<h3 class="font-bold text-lg mt-4 mb-2 text-text-primary">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="font-bold text-xl mt-4 mb-2 text-text-primary">$1</h2>')
    .replace(/^\* (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-text-primary">$1</strong>')
    .replace(/\n\n/g, '</p><p class="my-2">')
    // Wrap paragraphs that don't start with tags we just added
    .replace(/^(?!<(h2|h3|li|p))/gm, '<p class="my-2">');
}

export function PreparationSummary({ summary, isExpanded, onToggle }: PreparationSummaryProps) {
  if (!summary) return null;

  return (
    <div className="bg-surface dark:bg-surface-elevated rounded-xl shadow-sm dark:shadow-none overflow-hidden mt-4 border border-border">
      <div 
        className="bg-surface-elevated/50 dark:bg-surface/50 px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-surface-elevated dark:hover:bg-surface transition-colors border-b border-border"
        onClick={onToggle}
      >
        <h3 className="font-semibold text-text-primary flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          Interview Preparation Summary
        </h3>
        <button className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface dark:hover:bg-surface-elevated transition-colors focus:outline-none">
          <svg className={`w-5 h-5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
      
      {isExpanded && (
        <div className="p-4 max-h-96 overflow-y-auto bg-surface dark:bg-surface-elevated text-text-secondary text-sm leading-relaxed">
          <div dangerouslySetInnerHTML={{ __html: renderMarkdown(summary) }} />
        </div>
      )}
    </div>
  );
}
