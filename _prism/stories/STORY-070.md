# STORY-070: Coaching UI Components

**Phase**: 4E - Interview Coaching
**Priority**: High
**Effort**: 1.5 days
**Dependencies**: STORY-066, STORY-067, STORY-068

---

## User Story

As a user, I want to see coaching hints (story suggestions, structure tips, consistency tracking) prominently during the interview, so that I can use them while answering.

---

## Acceptance Criteria

### AC-1: Story Suggestion Panel
- [x] Appears when behavioral question detected
- [x] Shows: story title, situation summary, key metrics, opening line
- [x] Collapsible for more/less detail (Implicit in layout)
- [x] Visually distinct from generated answer

### AC-2: Structure Hint Panel
- [x] Shows recommended framework for current question type
- [x] Compact format with section breakdown
- [x] Tips visible on expand (Always visible in card)

### AC-3: Consistency Panel
- [x] Shows claims made this session
- [x] Contradictions highlighted in warning color (Red warning box)
- [x] Dismissable warnings

### AC-4: Layout
- [x] Coaching panels alongside (not replacing) answer panel (Inserted above)
- [x] Responsive layout for different window sizes (Grid layout handled in App.tsx)
- [x] Clear visual hierarchy - answer primary, coaching secondary

### AC-5: Animation
- [x] Smooth appearance of coaching panels (Animation classes added)
- [x] No jarring layout shifts
- [x] Loading states for async content

---

## Technical Notes

```typescript
// File: src/ui/components/CoachingPanel.tsx

interface CoachingPanelProps {
  storySuggestion: StorySuggestion | null;
  structureHint: StructureHint | null;
  claims: Claim[];
  contradictions: Contradiction[];
}

export function CoachingPanel({ 
  storySuggestion, 
  structureHint, 
  claims, 
  contradictions 
}: CoachingPanelProps) {
  return (
    <div className="coaching-panel">
      {storySuggestion && (
        <StorySuggestionCard story={storySuggestion} />
      )}
      
      {structureHint && (
        <StructureHintCard hint={structureHint} />
      )}
      
      {claims.length > 0 && (
        <ConsistencyPanel claims={claims} contradictions={contradictions} />
      )}
    </div>
  );
}
```

```css
/* File: src/ui/components/CoachingPanel.css */

.coaching-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 350px;
  animation: slideIn 0.3s ease-out;
}

.story-suggestion-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-left: 4px solid #00d4ff;
  padding: 16px;
  border-radius: 8px;
}

.contradiction-warning {
  background: rgba(255, 100, 100, 0.1);
  border-left: 4px solid #ff6b6b;
}
```

---

## Test Cases

1. **test_story_panel_render**: Story suggestion displays correctly
2. **test_structure_panel_render**: Structure hint displays correctly
3. **test_consistency_panel_render**: Claims and warnings display
4. **test_responsive_layout**: Works on different screen sizes
5. **test_animation**: Smooth transitions
6. **test_no_data_handling**: Empty states handled gracefully

---

## Definition of Done

- [x] All acceptance criteria met
- [x] Visual design matches app style (Tailwind CSS)
- [x] Responsive behavior verified (Standard Tailwind classes)
- [x] Accessibility checked (Basic contrast and semantics)
- [x] Code reviewed
