# STORY-040: History Panel UI

**Phase**: 3A (Foundation)
**Priority**: P1 - Must Have
**Effort**: 1 day
**Dependencies**: STORY-039

## Description

Create the frontend UI components for viewing and managing session history. Includes a panel to list saved sessions, view session details, and perform actions (export, delete).

## Acceptance Criteria

- [ ] Create `HistoryPanel` component with session list
- [ ] Create `SessionViewer` component for read-only session replay
- [ ] Add "History" button/tab to main navigation
- [ ] Display session metadata (date, duration, context files)
- [ ] Support export to JSON, Markdown, and plain text
- [ ] Support session deletion with confirmation dialog
- [ ] Handle empty state (no saved sessions)
- [ ] Responsive design for panel

## Technical Details

### Components

```typescript
// src/ui/components/HistoryPanel.tsx
interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function HistoryPanel({ isOpen, onClose }: HistoryPanelProps) {
  const { savedSessions, listSessions, deleteSession, exportSession } = useSessionStore();
  
  useEffect(() => {
    if (isOpen) {
      listSessions();
    }
  }, [isOpen]);
  
  return (
    <div className="history-panel">
      <h2>Session History</h2>
      {savedSessions.length === 0 ? (
        <EmptyState message="No saved sessions yet" />
      ) : (
        <SessionList sessions={savedSessions} onSelect={...} onDelete={...} />
      )}
    </div>
  );
}
```

```typescript
// src/ui/components/SessionViewer.tsx
interface SessionViewerProps {
  sessionId: string;
  onBack: () => void;
}

export function SessionViewer({ sessionId, onBack }: SessionViewerProps) {
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  
  // Load session data
  // Render transcriptions and answers in read-only timeline view
}
```

### Store Extensions

```typescript
// Add to sessionStore.ts
savedSessions: SessionSummary[];
isHistoryOpen: boolean;
selectedSessionId: string | null;

listSessions: () => Promise<void>;
loadSession: (sessionId: string) => Promise<SessionData>;
exportSession: (sessionId: string, format: string) => Promise<string>;
deleteSession: (sessionId: string) => Promise<void>;
setHistoryOpen: (open: boolean) => void;
```

### UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [←] Session History                         [Export ▼]     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📅 Jan 9, 2026 - 2:30 PM                                ││
│  │ Duration: 45 min | 12 Q&A | resume.pdf                  ││
│  │                                        [View] [Delete]  ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 📅 Jan 8, 2026 - 10:00 AM                               ││
│  │ Duration: 30 min | 8 Q&A | resume.pdf, job_desc.txt     ││
│  │                                        [View] [Delete]  ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Test Cases

1. **List sessions**: Open panel, verify sessions load and display
2. **Empty state**: No sessions, show friendly message
3. **View session**: Click session, verify details load
4. **Export JSON**: Export session, verify valid JSON downloaded
5. **Export Markdown**: Export session, verify Markdown format
6. **Delete session**: Delete with confirmation, verify removed from list
7. **Responsive**: Panel works on narrow screens

## Definition of Done

- [ ] Components implemented with proper styling
- [ ] WebSocket integration for all actions
- [ ] Loading and error states handled
- [ ] Confirmation dialogs for destructive actions
- [ ] Unit tests for components
- [ ] Manual UI testing
