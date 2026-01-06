import React, { useEffect, useRef } from 'react';
import { useSessionStore } from '../store/sessionStore';

const AnswerDisplay: React.FC = () => {
  const currentTranscription = useSessionStore((state) => state.currentTranscription);
  const currentAnswer = useSessionStore((state) => state.currentAnswer);
  const scrollRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="bg-white rounded-lg shadow-md p-6 h-full min-h-[600px] flex flex-col">
      <h2 className="text-xl font-semibold mb-4">AI Answer</h2>
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
          <p className="text-gray-800">
            {currentTranscription?.text || 'Detected question will appear here...'}
          </p>
        </div>

        <div className="p-4 bg-green-50 rounded-lg min-h-[300px]">
          <h3 className="font-medium text-sm text-gray-600 mb-2">Answer:</h3>
          <p className="text-gray-800 whitespace-pre-wrap">
            {currentAnswer?.answerText || 'AI-generated answer will stream here...'}
          </p>
          {currentAnswer && !currentAnswer.isComplete && (
            <span className="inline-block w-2 h-4 bg-gray-600 animate-pulse ml-1" />
          )}
          <div ref={scrollRef} />
        </div>

        <div className="flex items-center justify-between text-sm mt-auto pt-4 border-t border-gray-100">
          <div className="text-gray-500">
            <span className="font-medium">Confidence:</span>{' '}
            {currentAnswer ? (
              <span
                className={`px-2 py-1 rounded ${getConfidenceColor(currentAnswer.confidence)}`}
              >
                {currentAnswer.confidence.charAt(0).toUpperCase() +
                  currentAnswer.confidence.slice(1)}
              </span>
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
