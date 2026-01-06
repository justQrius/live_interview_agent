import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import AnswerDisplay from './AnswerDisplay';
import { useSessionStore } from '../store/sessionStore';

// Mock scrollIntoView
const scrollIntoViewMock = vi.fn();
window.HTMLElement.prototype.scrollIntoView = scrollIntoViewMock;

describe('AnswerDisplay', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      currentTranscription: null,
      currentAnswer: null,
      transcriptionHistory: [],
      answerHistory: [],
    });
  });

  it('renders initial state correctly', () => {
    render(<AnswerDisplay />);
    expect(screen.getByText('AI Answer')).toBeInTheDocument();
    expect(screen.getByText('Detected question will appear here...')).toBeInTheDocument();
    expect(screen.getByText('AI-generated answer will stream here...')).toBeInTheDocument();
  });

  it('displays transcription when available', () => {
    useSessionStore.setState({
      currentTranscription: {
        speaker: 'Interviewer',
        text: 'What is your greatest strength?',
        timestamp: Date.now(),
        confidence: 0.9,
      },
    });

    render(<AnswerDisplay />);
    expect(screen.getByText('What is your greatest strength?')).toBeInTheDocument();
    expect(screen.getByText('Interviewer')).toBeInTheDocument();
  });

  it('displays streaming answer', () => {
    useSessionStore.setState({
      currentAnswer: {
        question: 'What is your greatest strength?',
        answerText: 'My greatest strength is...',
        confidence: 'high',
        timestamp: Date.now(),
        isComplete: false,
      },
    });

    render(<AnswerDisplay />);
    expect(screen.getByText('My greatest strength is...')).toBeInTheDocument();
  });

  it('scrolls to bottom when answer updates', () => {
    const { rerender } = render(<AnswerDisplay />);
    
    act(() => {
      useSessionStore.setState({
        currentAnswer: {
          question: 'Test',
          answerText: 'First part...',
          confidence: 'high',
          timestamp: Date.now(),
          isComplete: false,
        },
      });
    });
    
    rerender(<AnswerDisplay />);
    
    // Check if scrollIntoView was called
    // Note: We need to implement the ref logic in the component for this to pass
    expect(scrollIntoViewMock).toHaveBeenCalled();
  });

  it('shows correct confidence badge', () => {
    useSessionStore.setState({
      currentAnswer: {
        question: 'Test',
        answerText: 'Answer',
        confidence: 'high',
        timestamp: Date.now(),
        isComplete: true,
      },
    });

    render(<AnswerDisplay />);
    expect(screen.getByText('High')).toHaveClass('text-green-600');
    expect(screen.getByText('Complete')).toBeInTheDocument();
  });

  describe('transcription history', () => {
    it('should not show history button when no history', () => {
      render(<AnswerDisplay />);
      expect(screen.queryByText(/show history/i)).not.toBeInTheDocument();
    });

    it('should show history button when transcription history exists', () => {
      useSessionStore.setState({
        transcriptionHistory: [
          { speaker: 'Interviewer', text: 'Q1', timestamp: Date.now(), confidence: 0.9 },
        ],
        answerHistory: [],
      });

      render(<AnswerDisplay />);
      expect(screen.getByText(/show history/i)).toBeInTheDocument();
    });

    it('should show history count in button', () => {
      useSessionStore.setState({
        transcriptionHistory: [],
        answerHistory: [
          { question: 'Q1', answerText: 'A1', confidence: 'high', timestamp: Date.now(), isComplete: true },
          { question: 'Q2', answerText: 'A2', confidence: 'medium', timestamp: Date.now(), isComplete: true },
        ],
      });

      render(<AnswerDisplay />);
      expect(screen.getByText('Show History (2)')).toBeInTheDocument();
    });

    it('should toggle history panel on button click', async () => {
      const user = userEvent.setup();
      useSessionStore.setState({
        transcriptionHistory: [
          { speaker: 'Interviewer', text: 'Test question', timestamp: Date.now(), confidence: 0.9 },
        ],
        answerHistory: [],
      });

      render(<AnswerDisplay />);

      // Click to show
      await user.click(screen.getByText(/show history/i));
      expect(screen.getByText('Session History')).toBeInTheDocument();
      expect(screen.getByText('Test question')).toBeInTheDocument();

      // Click to hide
      await user.click(screen.getByText(/hide history/i));
      expect(screen.queryByText('Session History')).not.toBeInTheDocument();
    });

    it('should display transcription history with speaker badges', async () => {
      const user = userEvent.setup();
      const timestamp = Date.now();
      useSessionStore.setState({
        transcriptionHistory: [
          { speaker: 'Interviewer', text: 'Interviewer question', timestamp, confidence: 0.9 },
          { speaker: 'User', text: 'User response', timestamp: timestamp + 1000, confidence: 0.8 },
        ],
        answerHistory: [],
      });

      render(<AnswerDisplay />);
      await user.click(screen.getByText(/show history/i));

      expect(screen.getByText('Interviewer question')).toBeInTheDocument();
      expect(screen.getByText('User response')).toBeInTheDocument();
      // Check speaker badges exist (note: there may be duplicates from current transcription)
      expect(screen.getAllByText('Interviewer').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('User').length).toBeGreaterThanOrEqual(1);
    });
  });
});
