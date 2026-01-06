import React from 'react';
import { render, screen, act } from '@testing-library/react';
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
});
