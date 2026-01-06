# STORY-013: Answer Display UI

## Description
Implement a React component to display streaming answers from the AI assistant. The component should handle the `ANSWER_CHUNK` WebSocket messages (already handled in `useWebSocket` hook/store) and render them with a smooth typing effect. It should also display the confidence level of the final answer.

## Acceptance Criteria
- [ ] Create `AnswerDisplay` component in `src/ui/components/AnswerDisplay.tsx`
- [ ] Display the current streaming answer text
- [ ] Implement smooth scrolling to bottom as text arrives
- [ ] Show confidence badge (High/Medium/Low) when answer is complete
- [ ] Support "typing effect" (optional but nice for UX, though raw streaming might be fast enough)
- [ ] Handle multiple answer sessions (clear previous answer on new question or session start)
- [ ] Integrate into `App.tsx` main layout
- [ ] Unit tests for the component

## Technical Implementation
- **File**: `src/ui/components/AnswerDisplay.tsx`
- **Store**: Use `useSessionStore` to access `currentAnswer` and `answerConfidence`
- **Styling**: Tailwind CSS
  - Use a card or distinct section for the answer
  - Use different colors for confidence badges (Green=High, Yellow=Medium, Red=Low)
- **Props**: None (connects to store)

## Data Flow
1. WebSocket receives `ANSWER_CHUNK` -> updates `sessionStore.currentAnswer`
2. `AnswerDisplay` observes `currentAnswer`
3. Renders text updates in real-time
