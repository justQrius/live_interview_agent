import type { ReactNode } from 'react';

interface PreparationSummaryProps {
  summary: string | null;
  isExpanded: boolean;
  onToggle: () => void;
}

type Block =
  | { kind: 'h2'; text: string }
  | { kind: 'h3'; text: string }
  | { kind: 'ul'; items: string[] }
  | { kind: 'p'; text: string };

/**
 * Parse a tiny markdown subset (headings, unordered lists, bold, paragraphs)
 * into a structured representation. The result is rendered with React elements
 * so any user/llm-supplied text is automatically escaped — no innerHTML path.
 */
function parseMarkdown(text: string): Block[] {
  if (!text) return [];

  const lines = text.split('\n');
  const blocks: Block[] = [];
  let currentList: string[] | null = null;

  const flushList = () => {
    if (currentList && currentList.length > 0) {
      blocks.push({ kind: 'ul', items: currentList });
    }
    currentList = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line === '') {
      flushList();
      continue;
    }

    const h2 = /^##\s+(.+)$/.exec(line);
    if (h2) {
      flushList();
      blocks.push({ kind: 'h2', text: h2[1] });
      continue;
    }

    const h3 = /^###\s+(.+)$/.exec(line);
    if (h3) {
      flushList();
      blocks.push({ kind: 'h3', text: h3[1] });
      continue;
    }

    const li = /^[*-]\s+(.+)$/.exec(line);
    if (li) {
      if (!currentList) currentList = [];
      currentList.push(li[1]);
      continue;
    }

    flushList();
    blocks.push({ kind: 'p', text: line });
  }

  flushList();
  return blocks;
}

/**
 * Render **bold** spans inside a text string as React elements.
 * Everything else is a plain text node (React escapes it automatically).
 */
function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts
    .filter((p) => p.length > 0)
    .map((part, i) => {
      const bold = /^\*\*([^*]+)\*\*$/.exec(part);
      if (bold) {
        return <strong key={i} className="text-text-primary">{bold[1]}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
}

export function PreparationSummary({ summary, isExpanded, onToggle }: PreparationSummaryProps) {
  if (!summary) return null;

  const blocks = parseMarkdown(summary);

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
          {blocks.map((block, i) => {
            switch (block.kind) {
              case 'h2':
                return <h2 key={i} className="font-bold text-xl mt-4 mb-2 text-text-primary">{renderInline(block.text)}</h2>;
              case 'h3':
                return <h3 key={i} className="font-bold text-lg mt-4 mb-2 text-text-primary">{renderInline(block.text)}</h3>;
              case 'ul':
                return (
                  <ul key={i} className="my-2">
                    {block.items.map((item, j) => (
                      <li key={j} className="ml-4 list-disc">{renderInline(item)}</li>
                    ))}
                  </ul>
                );
              case 'p':
                return <p key={i} className="my-2">{renderInline(block.text)}</p>;
            }
          })}
        </div>
      )}
    </div>
  );
}
