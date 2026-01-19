import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';
import EnhanceButton from './EnhanceButton';

type CombinedHistoryItem =
  | {
      type: 'transcription';
      timestamp: number;
      speaker: 'User' | 'Interviewer';
      text: string;
    }
  | {
      type: 'answer';
      timestamp: number;
      speaker: 'AI Assistant';
      text: string;
      question: string;
      confidence: 'high' | 'medium' | 'low';
    };

// Patterns that indicate LLM "thinking" vs actual answer content
// Expanded to catch more thinking patterns while avoiding false positives
const THINKING_PATTERNS = [
  /^<thinking>/m,             // Explicit <thinking> tag (primary format)
  /^>\s*\*Thinking:/m,        // Markdown blockquote thinking (legacy Gemini)
  /^\*\*[^*]+\*\*$/m,           // **Bold headers** on their own line
  /^My focus/m,                 // "My focus is..."
  /^I'm exploring/m,            // "I'm exploring..."
  /^I'm considering/m,          // "I'm considering..."
  /^I am focusing/m,            // "I am focusing..."
  /^Analyzing/m,                // "Analyzing..."
  /^\*[^*]+\*$/m,               // *Italic notes*
  /^I view the/m,               // Bridge phrases before actual answer
  /^Let me think/m,             // "Let me think..."
  /^Let me analyze/m,           // "Let me analyze..."
  /^First,? I'll/m,             // "First, I'll..."
  /^To answer this,/m,          // "To answer this, I need to..."
  /^The key points? are:/m,     // "The key points are:"
  /^Based on (?:the|my)/m,      // "Based on the/my..."
  /^From (?:my )?(?:experience|background),/m,  // References to context
  /^\[?Reasoning[?:\]:]?\s*/mi, // Explicit reasoning markers
  /^I'll structure/m,           // "I'll structure..."
  /^Here's my approach/m,       // "Here's my approach..."
  /^For (?:this|that) (?:question|scenario),/m, // For question scenarios
];

// Try to separate thinking from answer
function separateThinkingFromAnswer(text: string): { thinking: string | null; answer: string; isStreaming?: boolean } {
  if (!text) return { thinking: null, answer: '' };

  // Priority 1: Check for explicit <thinking> tags (most reliable)
  // Handle both complete tags and streaming (open tag only)
  
  // Case 1a: Complete thinking block (has both opening and closing tags)
  const completeThinkingMatch = text.match(/<thinking>([\s\S]*?)<\/thinking>/);
  if (completeThinkingMatch) {
    const thinkingContent = completeThinkingMatch[1].trim();
    const answerContent = text.replace(/<thinking>[\s\S]*?<\/thinking>\s*/, '').trim();
    
    if (thinkingContent.length > 10 && answerContent.length > 10) {
      return {
        thinking: thinkingContent,
        answer: answerContent
      };
    }
  }
  
  // Case 1b: Streaming - only opening tag present (no closing tag yet)
  // This handles the case where LLM is still outputting thinking content
  const streamingThinkingMatch = text.match(/<thinking>([\s\S]*)$/);
  if (streamingThinkingMatch && !text.includes('</thinking>')) {
    const thinkingContent = streamingThinkingMatch[1].trim();
    return {
      thinking: thinkingContent,
      answer: '', // No answer yet, still thinking
      isStreaming: true
    };
  }

  // Priority 2: Check for markdown blockquote thinking (legacy format)
  const blockquoteMatch = text.match(/^>\s*\*Thinking:\s*([\s\S]*?)\*\s*\n\n/m);
  if (blockquoteMatch) {
    const thinkingContent = blockquoteMatch[1].trim();
    const answerContent = text.replace(/^>\s*\*Thinking:[\s\S]*?\*\s*\n\n/m, '').trim();
    
    if (thinkingContent.length > 10 && answerContent.length > 10) {
      return {
        thinking: thinkingContent,
        answer: answerContent
      };
    }
  }

  // Priority 3: Heuristic pattern matching (fallback)

  // Look for patterns that mark the start of actual answer
  // Comprehensive list of answer markers
  const answerMarkers = [
    // STAR format markers
    /\n\n(?:Situation|Task|Action|Result)[:\s]/,
    /\n\nI had a situation/,     // Classic STAR opener
    /\n\nAt my previous/,        // Experience opener
    /\n\nIn my role/,            // Role opener
    /\n\nWhen I was/,            // Past experience
    /\n\nDuring my time/,        // Experience opener
    /\n\nAt \w+,/,               // "At Company,"
    /\n\nI remember/,            // Story recall
    /\n\nOne example/,           // Example opener
    /\n\nFor example/,           // Example
    /\n\nFor instance/,          // Instance
    /\n\nHere's what happened/,  // Story
    /\n\nLet me share/,          // Sharing experience
    /\n\nThis (?:led|resulted|helped|achieved)/,  // Results
    /\n\nThe outcome was/,       // Outcome
    /\n\nAs a result,/,          // Result
    /\n\nI (?:successfully|managed to|was able to)/,  // Success statements
    /\n\nMy (?:key|major) (?:achievement|contribution|impact)/,  // Achievements
    /\n\n---\n/,                  // Explicit separator

    // Bullet points that indicate answer content
    /\n\n[-•*]\s+\w+/,          // List items after double newline
  ];

  // Check if text starts with thinking patterns
  const firstLine = text.split('\n')[0];
  const hasThinkingStart = THINKING_PATTERNS.some(pattern => pattern.test(firstLine));

  if (!hasThinkingStart) {
    return { thinking: null, answer: text };
  }

  // Find where the actual answer starts
  for (const marker of answerMarkers) {
    const match = text.match(marker);
    if (match && match.index !== undefined) {
      const thinkingPart = text.substring(0, match.index).trim();
      const answerPart = text.substring(match.index).trim();

      // Only separate if thinking is substantial and answer is meaningful
      if (thinkingPart.length > 30 && answerPart.length > 30) {
        return {
          thinking: thinkingPart,
          answer: answerPart
        };
      }
    }
  }

  // If no clear answer marker found but thinking was detected at start
  // Check if the thinking part is just section headers
  const isJustHeaders = THINKING_PATTERNS.some(p =>
    p.test(firstLine) && !p.toString().includes('Let me') && !p.toString().includes('Based on')
  ) && text.length < 200;

  if (isJustHeaders) {
    return { thinking: null, answer: text };
  }

  return { thinking: null, answer: text };
}

// Component to render the separated thinking/answer
function AnswerContent({ text }: { text: string; isComplete?: boolean }) {
  const [showThinking, setShowThinking] = useState(false);
  const { thinking, answer, isStreaming } = useMemo(() => separateThinkingFromAnswer(text), [text]);
  
  if (!thinking) {
    // No thinking detected, render normally
    return (
      <p className="text-text-primary whitespace-pre-wrap leading-relaxed tracking-wide">
        {text || 'AI-generated answer will stream here...'}
      </p>
    );
  }
  
  return (
    <div className="space-y-3">
      {/* Thinking trace - collapsible */}
      <div className="border-l-2 border-amber-300 dark:border-amber-600 bg-amber-50/50 dark:bg-amber-900/10 rounded-r-lg">
        <button 
          onClick={() => setShowThinking(!showThinking)}
          className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors rounded-r-lg"
        >
          <span className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400 font-medium">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            {isStreaming ? 'AI Thinking...' : 'AI Reasoning Trace'}
            {isStreaming && (
              <span className="inline-block w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
            )}
            {!isStreaming && (
              <span className="text-amber-500 dark:text-amber-500">({showThinking ? 'hide' : 'show'})</span>
            )}
          </span>
          {!isStreaming && (
            <svg 
              className={`w-4 h-4 text-amber-500 transition-transform ${showThinking ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          )}
        </button>
        {(showThinking || isStreaming) && (
          <div className="px-3 pb-3 text-sm text-amber-900/70 dark:text-amber-300/70 whitespace-pre-wrap italic">
            {thinking}
            {isStreaming && <span className="inline-block animate-pulse">▊</span>}
          </div>
        )}
      </div>
      
      {/* Answer separator - only show if there's an answer */}
      {answer && !isStreaming && (
        <>
          <div className="flex items-center gap-2 py-1">
            <div className="flex-1 h-px bg-green-300 dark:bg-green-700" />
            <span className="text-xs font-semibold text-green-700 dark:text-green-400 uppercase tracking-wide flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              Your Answer
            </span>
            <div className="flex-1 h-px bg-green-300 dark:bg-green-700" />
          </div>
          
          {/* Actual answer */}
          <p className="text-text-primary whitespace-pre-wrap leading-relaxed tracking-wide">
            {answer}
          </p>
        </>
      )}
    </div>
  );
}

const AnswerDisplay: React.FC = () => {
  const status = useSessionStore((state) => state.status);
  const currentTranscription = useSessionStore((state) => state.currentTranscription);
  const interimTranscript = useSessionStore((state) => state.interimTranscript);
  const currentAnswer = useSessionStore((state) => state.currentAnswer);
  const transcriptionHistory = useSessionStore((state) => state.transcriptionHistory);
  const answerHistory = useSessionStore((state) => state.answerHistory);
  const enhancement = useSessionStore((state) => state.enhancement);
  const applyEnhancement = useSessionStore((state) => state.applyEnhancement);
  const cancelEnhancement = useSessionStore((state) => state.cancelEnhancement);
  const addTranscription = useSessionStore((state) => state.addTranscription);
  const startAnswer = useSessionStore((state) => state.startAnswer);
  const setInterimTranscript = useSessionStore((state) => state.setInterimTranscript);
  const setStorySuggestion = useSessionStore((state) => state.setStorySuggestion);
  const setStructureHint = useSessionStore((state) => state.setStructureHint);
  const setConsistencyWarnings = useSessionStore((state) => state.setConsistencyWarnings);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [manualQuestion, setManualQuestion] = useState('');

  const { sendMessage, isConnected } = useWebSocket();
  
  const handleCancelEnhancement = () => {
    sendMessage({ type: 'CANCEL_ENHANCEMENT' });
    cancelEnhancement();
  };

  const handleSendManualQuestion = () => {
    const trimmedQuestion = manualQuestion.trim();
    if (!trimmedQuestion || !isConnected || (status !== 'listening' && status !== 'listening_paused')) {
      return;
    }

    const timestamp = Date.now();

    // Update local state so UI reflects the manual question immediately
    addTranscription({
      speaker: 'Interviewer',
      text: trimmedQuestion,
      timestamp,
      confidence: 1.0,
    });

    // Prepare answer buffer with the question
    startAnswer(trimmedQuestion, timestamp);
    setInterimTranscript(null);

    // Clear coaching data for the new question
    setStorySuggestion(null);
    setStructureHint(null);
    setConsistencyWarnings([]);

    sendMessage({
      type: 'MANUAL_QUESTION',
      data: { question: trimmedQuestion },
    });
    setManualQuestion('');
  };

  const handleQuestionKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendManualQuestion();
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentAnswer?.answerText]);

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const combinedHistory = useMemo<CombinedHistoryItem[]>(() => {
    const transcriptions: CombinedHistoryItem[] = transcriptionHistory.map((t) => ({
      type: 'transcription',
      timestamp: t.timestamp,
      speaker: t.speaker,
      text: t.text,
    }));

    const answers: CombinedHistoryItem[] = answerHistory.map((a) => ({
      type: 'answer',
      timestamp: a.timestamp,
      speaker: 'AI Assistant',
      text: a.answerText,
      question: a.question,
      confidence: a.confidence,
    }));

    return [...transcriptions, ...answers].sort((a, b) => a.timestamp - b.timestamp);
  }, [transcriptionHistory, answerHistory]);

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-border p-5 h-full min-h-[600px] flex flex-col dark:shadow-none transition-colors">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-green-50 dark:bg-green-900/20 rounded-lg text-green-600 dark:text-green-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-text-primary">AI Answer</h2>
            <p className="text-xs text-text-muted">Real-time assistance</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <EnhanceButton disabled={!currentAnswer?.isComplete} />
          {(transcriptionHistory.length > 0 || answerHistory.length > 0) && (
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="text-xs font-medium text-primary hover:text-primary-hover flex items-center gap-1 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={showHistory ? "M19 9l-7 7-7-7" : "M9 5l7 7-7 7"} />
              </svg>
              {showHistory ? 'Hide History' : `History (${answerHistory.length})`}
            </button>
          )}
        </div>
      </div>

      {/* History Panel */}
      {showHistory && (transcriptionHistory.length > 0 || answerHistory.length > 0) && (
        <div className="mb-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-xl max-h-[300px] overflow-y-auto border border-border">
          <h3 className="font-medium text-sm text-text-secondary mb-3">Session History</h3>
          <div className="space-y-3">
            {combinedHistory.map((item, idx) => (
              <div
                key={`${item.type}-${idx}`}
                className="text-sm border-b border-border last:border-0 pb-3 mb-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-text-muted text-xs">{formatTime(item.timestamp)}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      item.type === 'answer'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : item.speaker === 'Interviewer'
                          ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400'
                          : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {item.speaker}
                  </span>
                </div>
                {item.type === 'answer' && item.question && (
                  <div className="text-xs text-text-muted mb-1 italic pl-2 border-l-2 border-green-200 dark:border-green-800">
                    Q: {item.question}
                  </div>
                )}
                <p
                  className={`text-text-primary whitespace-pre-wrap ${
                    item.type === 'answer' ? 'pl-2 border-l-2 border-green-200 dark:border-green-800 mt-1' : ''
                  }`}
                >
                  {item.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4 flex-grow overflow-y-auto">
        {/* Question Section */}
        <div className="p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl border border-blue-100 dark:border-blue-900/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="font-medium text-sm text-blue-700 dark:text-blue-300">Question</h3>
            </div>
            {currentTranscription && (
              <span
                className={`text-xs px-2 py-1 rounded-full font-medium ${
                  currentTranscription.speaker === 'Interviewer'
                    ? 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400'
                    : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                }`}
              >
                {currentTranscription.speaker}
              </span>
            )}
          </div>
          <p className={`text-text-primary ${interimTranscript ? 'italic text-text-secondary' : ''}`}>
            {interimTranscript || currentTranscription?.text || 'Detected question will appear here...'}
          </p>
          {interimTranscript && (
            <span className="inline-flex items-center gap-1 text-xs text-blue-500 mt-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
              Listening...
            </span>
          )}
        </div>

        {/* Answer Section */}
        <div className="p-4 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl border border-green-100 dark:border-green-900/30 min-h-[300px]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="font-medium text-sm text-green-700 dark:text-green-300">Answer</h3>
            </div>
          </div>
          <AnswerContent 
            text={currentAnswer?.answerText || ''} 
            isComplete={currentAnswer?.isComplete || false} 
          />
          {currentAnswer && !currentAnswer.isComplete && (
            <span className="inline-block w-2 h-4 bg-green-500 animate-pulse ml-1 rounded-sm" />
          )}
          <div ref={scrollRef} />
        </div>

        {/* Enhanced Answer Panel - Shows when enhancement is in progress or complete */}
        {(enhancement.isEnhancing || enhancement.enhancedText) && (
          <div className="p-4 bg-gradient-to-br from-blue-50 to-violet-50 dark:from-blue-900/20 dark:to-violet-900/20 rounded-xl border-2 border-blue-200 dark:border-blue-800">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-sm text-blue-700 dark:text-blue-300 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Enhanced Answer
                {enhancement.enhancementType && (
                  <span className="text-xs bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 px-2 py-0.5 rounded-full">
                    {enhancement.enhancementType.replace('_', ' ')}
                  </span>
                )}
              </h3>
              {enhancement.isEnhancing && (
                <span className="flex items-center gap-1 text-xs text-blue-500">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  Generating...
                </span>
              )}
            </div>
            
            <p className="text-text-primary whitespace-pre-wrap leading-relaxed tracking-wide">
              {enhancement.enhancedText || 'Generating enhanced answer...'}
            </p>
              {enhancement.isEnhancing && (
                <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1 rounded-sm" />
              )}
              
              {/* Cancel button while enhancement is in progress */}
              {enhancement.isEnhancing && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-blue-200 dark:border-blue-800">
                  <button
                    onClick={handleCancelEnhancement}
                    className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm font-medium rounded-lg border border-red-300 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
                  >
                    Cancel Enhancement
                  </button>
                </div>
              )}

              {/* Action buttons when enhancement is complete */}
            {!enhancement.isEnhancing && enhancement.enhancedText && (
              <div className="flex gap-2 mt-4 pt-3 border-t border-blue-200 dark:border-blue-800">
                <button
                  onClick={applyEnhancement}
                  className="px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-medium rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all shadow-sm hover:shadow"
                >
                  Use This Answer
                </button>
                <button
                  onClick={cancelEnhancement}
                  className="px-4 py-2 bg-surface text-text-secondary text-sm font-medium rounded-lg border border-border hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                >
                  Keep Original
                </button>
              </div>
            )}
          </div>
        )}

        {/* Manual Question Input - In main chat window */}
        {(status === 'listening' || status === 'listening_paused') && (
          <div className="pt-3 border-t border-border">
            <label htmlFor="manual-question" className="block text-xs font-medium text-text-secondary mb-1.5 flex justify-between">
              <span>Ask Manually</span>
              {status === 'listening_paused' && <span className="text-amber-500 font-semibold">Listening Paused</span>}
            </label>
            <textarea
              id="manual-question"
              value={manualQuestion}
              onChange={(e) => setManualQuestion(e.target.value)}
              onKeyDown={handleQuestionKeyDown}
              placeholder="Type & Enter to ask a question..."
              className="w-full p-2.5 text-sm bg-slate-50 dark:bg-slate-800 border border-border rounded-lg resize-none focus:ring-1 focus:ring-primary focus:border-primary text-text-primary placeholder:text-text-muted transition-colors"
              rows={2}
              disabled={!isConnected || (status !== 'listening' && status !== 'listening_paused')}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default AnswerDisplay;
