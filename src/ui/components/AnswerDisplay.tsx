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
const THINKING_PATTERNS = [
  /^\*\*[^*]+\*\*$/m,           // **Bold headers** on their own line
  /^My focus/m,                 // "My focus is..."
  /^I'm exploring/m,            // "I'm exploring..."
  /^I'm considering/m,          // "I'm considering..."
  /^I am focusing/m,            // "I am focusing..."
  /^Analyzing/m,                // "Analyzing..."
  /^\*[^*]+\*$/m,               // *Italic notes*
  /^I view the/m,               // Bridge phrases before actual answer
];

// Try to separate thinking from answer
function separateThinkingFromAnswer(text: string): { thinking: string | null; answer: string } {
  if (!text) return { thinking: null, answer: '' };
  
  // Look for patterns that mark the start of actual answer
  // Common patterns: first-person statements about real experience
  const answerMarkers = [
    /\n\nI had a situation/,
    /\n\nAt my previous/,
    /\n\nIn my role/,
    /\n\nWhen I was/,
    /\n\nDuring my time/,
    /\n\nAt \w+,/,           // "At Company,"
    /\n\nI remember/,
    /\n\nOne example/,
    /\n\nFor example/,
    /\n\nHere's what happened/,
    /\n\nLet me share/,
    /\n\n---\n/,            // Explicit separator
  ];
  
  // Check if text starts with thinking patterns
  const hasThinkingStart = THINKING_PATTERNS.some(pattern => pattern.test(text.split('\n')[0]));
  
  if (!hasThinkingStart) {
    return { thinking: null, answer: text };
  }
  
  // Find where the actual answer starts
  for (const marker of answerMarkers) {
    const match = text.match(marker);
    if (match && match.index !== undefined) {
      const thinkingPart = text.substring(0, match.index).trim();
      const answerPart = text.substring(match.index).trim();
      
      // Only separate if thinking is substantial (more than just a header)
      if (thinkingPart.length > 50 && answerPart.length > 50) {
        return {
          thinking: thinkingPart,
          answer: answerPart
        };
      }
    }
  }
  
  return { thinking: null, answer: text };
}

// Component to render the separated thinking/answer
function AnswerContent({ text }: { text: string; isComplete?: boolean }) {
  const [showThinking, setShowThinking] = useState(false);
  const { thinking, answer } = useMemo(() => separateThinkingFromAnswer(text), [text]);
  
  if (!thinking) {
    // No thinking detected, render normally
    return (
      <p className="text-gray-800 whitespace-pre-wrap leading-relaxed tracking-wide">
        {text || 'AI-generated answer will stream here...'}
      </p>
    );
  }
  
  return (
    <div className="space-y-3">
      {/* Thinking trace - collapsible */}
      <div className="border-l-2 border-amber-300 bg-amber-50/50 rounded-r">
        <button 
          onClick={() => setShowThinking(!showThinking)}
          className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-amber-50 transition-colors"
        >
          <span className="flex items-center gap-2 text-xs text-amber-700 font-medium">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            AI Reasoning Trace
            <span className="text-amber-500">({showThinking ? 'hide' : 'show'})</span>
          </span>
          <svg 
            className={`w-4 h-4 text-amber-500 transition-transform ${showThinking ? 'rotate-180' : ''}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {showThinking && (
          <div className="px-3 pb-3 text-sm text-amber-900/70 whitespace-pre-wrap italic">
            {thinking}
          </div>
        )}
      </div>
      
      {/* Answer separator */}
      <div className="flex items-center gap-2 py-1">
        <div className="flex-1 h-px bg-green-300"></div>
        <span className="text-xs font-semibold text-green-700 uppercase tracking-wide flex items-center gap-1">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          Your Answer
        </span>
        <div className="flex-1 h-px bg-green-300"></div>
      </div>
      
      {/* Actual answer */}
      <p className="text-gray-800 whitespace-pre-wrap leading-relaxed tracking-wide">
        {answer}
      </p>
    </div>
  );
}

const AnswerDisplay: React.FC = () => {
  const currentTranscription = useSessionStore((state) => state.currentTranscription);
  const interimTranscript = useSessionStore((state) => state.interimTranscript);
  const currentAnswer = useSessionStore((state) => state.currentAnswer);
  const transcriptionHistory = useSessionStore((state) => state.transcriptionHistory);
  const answerHistory = useSessionStore((state) => state.answerHistory);
  const enhancement = useSessionStore((state) => state.enhancement);
  const applyEnhancement = useSessionStore((state) => state.applyEnhancement);
  const cancelEnhancement = useSessionStore((state) => state.cancelEnhancement);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  
  const { sendMessage } = useWebSocket();
  
  const handleCancelEnhancement = () => {
    sendMessage({ type: 'CANCEL_ENHANCEMENT' });
    cancelEnhancement();
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [currentAnswer?.answerText]);

  const getConfidenceColor = (confidence: 'high' | 'medium' | 'low') => {
    switch (confidence) {
      case 'high':
        return 'text-green-600 bg-green-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-red-600 bg-red-100';
    }
  };

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
    <div className="bg-white rounded-lg shadow-md p-6 h-full min-h-[600px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">AI Answer</h2>
        {(transcriptionHistory.length > 0 || answerHistory.length > 0) && (
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {showHistory ? 'Hide History' : `Show History (${answerHistory.length})`}
          </button>
        )}
      </div>

      {/* History Panel */}
      {showHistory && (transcriptionHistory.length > 0 || answerHistory.length > 0) && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg max-h-[300px] overflow-y-auto border border-gray-200">
          <h3 className="font-medium text-sm text-gray-700 mb-3">Session History</h3>
          <div className="space-y-3">
            {combinedHistory.map((item, idx) => (
              <div
                key={`${item.type}-${idx}`}
                className="text-sm border-b border-gray-100 last:border-0 pb-3 mb-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-gray-400 text-xs">{formatTime(item.timestamp)}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${
                      item.type === 'answer'
                        ? 'bg-green-100 text-green-700'
                        : item.speaker === 'Interviewer'
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {item.speaker}
                  </span>
                </div>
                {item.type === 'answer' && item.question && (
                  <div className="text-xs text-gray-500 mb-1 italic pl-2 border-l-2 border-green-100">
                    Q: {item.question}
                  </div>
                )}
                <p
                  className={`text-gray-800 whitespace-pre-wrap ${
                    item.type === 'answer' ? 'pl-2 border-l-2 border-green-200 mt-1' : ''
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
        <div className="p-4 bg-blue-50 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-sm text-gray-600">Question:</h3>
            {currentTranscription && (
              <span
                className={`text-xs px-2 py-1 rounded ${
                  currentTranscription.speaker === 'Interviewer'
                    ? 'bg-purple-100 text-purple-700'
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {currentTranscription.speaker}
              </span>
            )}
          </div>
          <p className={`text-gray-800 ${interimTranscript ? 'italic text-gray-500' : ''}`}>
            {interimTranscript || currentTranscription?.text || 'Detected question will appear here...'}
          </p>
          {interimTranscript && (
            <span className="inline-flex items-center gap-1 text-xs text-blue-500 mt-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
              Listening...
            </span>
          )}
        </div>

        <div className="p-4 bg-green-50 rounded-lg min-h-[300px]">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-medium text-sm text-gray-600">Answer:</h3>
            <EnhanceButton disabled={!currentAnswer?.isComplete} />
          </div>
          <AnswerContent 
            text={currentAnswer?.answerText || ''} 
            isComplete={currentAnswer?.isComplete || false} 
          />
          {currentAnswer && !currentAnswer.isComplete && (
            <span className="inline-block w-2 h-4 bg-gray-600 animate-pulse ml-1" />
          )}
          <div ref={scrollRef} />
        </div>

        {/* Enhanced Answer Panel - Shows when enhancement is in progress or complete */}
        {(enhancement.isEnhancing || enhancement.enhancedText) && (
          <div className="p-4 bg-blue-50 rounded-lg border-2 border-blue-200">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-medium text-sm text-blue-700 flex items-center gap-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Enhanced Answer
                {enhancement.enhancementType && (
                  <span className="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                    {enhancement.enhancementType.replace('_', ' ')}
                  </span>
                )}
              </h3>
              {enhancement.isEnhancing && (
                <span className="flex items-center gap-1 text-xs text-blue-500">
                  <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
                  Generating...
                </span>
              )}
            </div>
            
            <p className="text-gray-800 whitespace-pre-wrap leading-relaxed tracking-wide">
              {enhancement.enhancedText || 'Generating enhanced answer...'}
            </p>
              {enhancement.isEnhancing && (
                <span className="inline-block w-2 h-4 bg-blue-600 animate-pulse ml-1" />
              )}
              
              {/* Cancel button while enhancement is in progress */}
              {enhancement.isEnhancing && (
                <div className="flex gap-2 mt-4 pt-3 border-t border-blue-200">
                  <button
                    onClick={handleCancelEnhancement}
                    className="px-4 py-2 bg-red-50 text-red-700 text-sm font-medium rounded-md border border-red-300 hover:bg-red-100 transition-colors"
                  >
                    Cancel Enhancement
                  </button>
                </div>
              )}

              {/* Action buttons when enhancement is complete */}
            {!enhancement.isEnhancing && enhancement.enhancedText && (
              <div className="flex gap-2 mt-4 pt-3 border-t border-blue-200">
                <button
                  onClick={applyEnhancement}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
                >
                  Use This Answer
                </button>
                <button
                  onClick={cancelEnhancement}
                  className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded-md border border-gray-300 hover:bg-gray-50 transition-colors"
                >
                  Keep Original
                </button>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between text-sm mt-auto pt-4 border-t border-gray-100">
          <div className="flex items-center group relative cursor-help">
            <span className="font-medium text-gray-500 mr-2">Confidence:</span>
            {currentAnswer ? (
              <>
                <span
                  className={`px-2 py-1 rounded ${getConfidenceColor(currentAnswer.confidence)}`}
                >
                  {currentAnswer.confidence.charAt(0).toUpperCase() +
                    currentAnswer.confidence.slice(1)}
                </span>
                <div className="absolute bottom-full left-0 mb-2 w-64 p-2 bg-gray-800 text-white text-xs rounded shadow-lg hidden group-hover:block z-50">
                  {currentAnswer.confidence === 'high' &&
                    'High confidence: Answer is well-supported by your resume/context.'}
                  {currentAnswer.confidence === 'medium' &&
                    'Medium confidence: Standard answer, verify specific details.'}
                  {currentAnswer.confidence === 'low' &&
                    'Low confidence: Generic response, use with caution.'}
                  <div className="absolute -bottom-1 left-4 w-2 h-2 bg-gray-800 transform rotate-45"></div>
                </div>
              </>
            ) : (
              <span className="text-gray-400">--</span>
            )}
          </div>
          {currentAnswer?.isComplete && (
            <span className="text-green-600 text-xs font-medium">Complete</span>
          )}
        </div>
      </div>
    </div>
  );
};

export default AnswerDisplay;
