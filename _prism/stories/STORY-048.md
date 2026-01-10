# STORY-048: Preparation Summary UI

**Phase**: 3B (Enhanced Context)
**Priority**: P2 - Should Have
**Effort**: 0.5 days
**Dependencies**: STORY-047

## Description

Create UI components to display the pre-interview preparation summary. Includes a button to trigger preparation and a panel to show the results.

## Acceptance Criteria

- [ ] Create `PreparationButton` component
- [ ] Create `PreparationSummary` panel component
- [ ] Show loading state during preparation
- [ ] Render markdown summary with proper formatting
- [ ] Allow collapsing/expanding the summary
- [ ] Persist preparation across session navigation

## Technical Details

### Components

```typescript
// src/ui/components/PreparationButton.tsx
interface PreparationButtonProps {
  disabled?: boolean;
}

export function PreparationButton({ disabled }: PreparationButtonProps) {
  const { preparationStatus, startPreparation } = useSessionStore();
  
  return (
    <button 
      onClick={startPreparation}
      disabled={disabled || preparationStatus === 'preparing'}
      className="preparation-button"
    >
      {preparationStatus === 'preparing' ? (
        <><Spinner /> Preparing...</>
      ) : preparationStatus === 'ready' ? (
        <>✓ Prepared</>
      ) : (
        <>🎯 Prepare for Interview</>
      )}
    </button>
  );
}
```

```typescript
// src/ui/components/PreparationSummary.tsx
interface PreparationSummaryProps {
  summary: string | null;
  isExpanded: boolean;
  onToggle: () => void;
}

export function PreparationSummary({ summary, isExpanded, onToggle }: PreparationSummaryProps) {
  if (!summary) return null;
  
  return (
    <div className="preparation-summary">
      <div className="summary-header" onClick={onToggle}>
        <h3>📋 Interview Preparation</h3>
        <span>{isExpanded ? '▼' : '▶'}</span>
      </div>
      {isExpanded && (
        <div className="summary-content">
          <ReactMarkdown>{summary}</ReactMarkdown>
        </div>
      )}
    </div>
  );
}
```

### Store Extensions

```typescript
// Add to sessionStore.ts
preparationStatus: 'not_started' | 'preparing' | 'ready';
preparationSummary: string | null;
isPreparationExpanded: boolean;

startPreparation: () => Promise<void>;
setPreparationExpanded: (expanded: boolean) => void;
```

### Styling

```css
.preparation-summary {
  background: var(--bg-secondary);
  border-radius: 8px;
  margin: 1rem 0;
  overflow: hidden;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  cursor: pointer;
  background: var(--bg-tertiary);
}

.summary-content {
  padding: 1rem;
  max-height: 400px;
  overflow-y: auto;
}
```

## Test Cases

1. **Trigger preparation**: Click button, verify loading state
2. **Display summary**: Summary renders with proper markdown
3. **Collapse/expand**: Toggle works correctly
4. **Disabled state**: Button disabled when no documents
5. **Re-prepare**: Can trigger preparation again after changes

## Definition of Done

- [ ] Components implemented with styling
- [ ] Markdown rendering working
- [ ] Store integration complete
- [ ] Responsive design
- [ ] Unit tests passing
