import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';

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

const AnswerDisplay: React.FC = () => {
  const currentTranscription = useSessionStore((state) => state.currentTranscription);
  const interimTranscript = useSessionStore((state) => state.interimTranscript);
  const currentAnswer = useSessionStore((state) => state.currentAnswer);
  const transcriptionHistory = useSessionStore((state) => state.transcriptionHistory);
  const answerHistory = useSessionStore((state) => state.answerHistory);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);

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
          <h3 className="font-medium text-sm text-gray-600 mb-2">Answer:</h3>
          <p className="text-gray-800 whitespace-pre-wrap leading-relaxed tracking-wide">
            {currentAnswer?.answerText || 'AI-generated answer will stream here...'}
          </p>
          {currentAnswer && !currentAnswer.isComplete && (
            <span className="inline-block w-2 h-4 bg-gray-600 animate-pulse ml-1" />
          )}
          <div ref={scrollRef} />
        </div>

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
