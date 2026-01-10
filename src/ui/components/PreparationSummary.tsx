interface PreparationSummaryProps {
  summary: string | null;
  isExpanded: boolean;
  onToggle: () => void;
}

function renderMarkdown(text: string): string {
  if (!text) return '';
  
  return text
    .replace(/^### (.+)$/gm, '<h3 class="font-bold text-lg mt-4 mb-2">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 class="font-bold text-xl mt-4 mb-2">$1</h2>')
    .replace(/^\* (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p class="my-2">')
    // Wrap paragraphs that don't start with tags we just added
    .replace(/^(?!<(h2|h3|li|p))/gm, '<p class="my-2">');
}

export function PreparationSummary({ summary, isExpanded, onToggle }: PreparationSummaryProps) {
  if (!summary) return null;

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden mt-4 border border-gray-200">
      <div 
        className="bg-gray-50 px-4 py-3 flex justify-between items-center cursor-pointer hover:bg-gray-100 transition-colors"
        onClick={onToggle}
      >
        <h3 className="font-semibold text-gray-800 flex items-center gap-2">
          <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
          </svg>
          Interview Preparation Summary
        </h3>
        <button className="text-gray-500 focus:outline-none">
          {isExpanded ? (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </button>
      </div>
      
      {isExpanded && (
        <div className="p-4 max-h-96 overflow-y-auto bg-white text-gray-700 text-sm leading-relaxed">
          <div dangerouslySetInnerHTML={{ __html: renderMarkdown(summary) }} />
        </div>
      )}
    </div>
  );
}
