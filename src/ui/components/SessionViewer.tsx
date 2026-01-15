import React, { useEffect, useMemo, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';

interface SessionViewerProps {
  sessionId: string;
  onBack: () => void;
}

interface TimelineItem {
  type: 'transcription' | 'answer';
  timestamp: number;
  data: any; // Using any here to simplify union of different shapes, or could be precise
}

export const SessionViewer: React.FC<SessionViewerProps> = ({ sessionId, onBack }) => {
  const { loadSession, exportSession } = useWebSocket();
  const selectedSession = useSessionStore((state) => state.selectedSession);
  const isHistoryLoading = useSessionStore((state) => state.isHistoryLoading);
  
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadSession(sessionId);
  }, [sessionId]);

  const timelineItems = useMemo(() => {
    if (!selectedSession || selectedSession.id !== sessionId) return [];

    const items: TimelineItem[] = [];

    selectedSession.transcriptions.forEach((t) => {
      items.push({
        type: 'transcription',
        timestamp: t.timestamp,
        data: t,
      });
    });

    selectedSession.answers.forEach((a) => {
      items.push({
        type: 'answer',
        timestamp: a.timestamp || 0,
        data: a,
      });
    });

    return items.sort((a, b) => a.timestamp - b.timestamp);
  }, [selectedSession, sessionId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportSession(sessionId, 'md');
      // In a real app we might show a success toast or save the file
      // For now, the sidecar usually handles the file saving or returns content
      // The requirement just says "Export button"
    } catch (error) {
      console.error('Export failed', error);
    } finally {
      setExporting(false);
    }
  };

  if (isHistoryLoading) {
    return (
      <div className="flex items-center justify-center h-full p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!selectedSession || selectedSession.id !== sessionId) {
    return (
      <div className="p-6 text-center text-gray-500">
        Session data not found.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 bg-surface dark:bg-surface-elevated border-b border-border sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 hover:bg-surface-elevated dark:hover:bg-surface rounded-lg transition-colors"
            aria-label="Go back"
          >
            <svg className="w-6 h-6 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">
              {new Date(selectedSession.startedAt).toLocaleString()}
            </h2>
            <div className="text-sm text-text-muted">
              {timelineItems.length} events | {selectedSession.contextFiles.length} context files
            </div>
          </div>
        </div>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="bg-surface-elevated dark:bg-surface text-text-primary px-4 py-2 rounded-lg hover:bg-primary/10 disabled:opacity-50 transition-colors flex items-center gap-2 border border-border"
        >
          {exporting ? (
            <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></span>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          )}
          Export
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {timelineItems.map((item, index) => {
          if (item.type === 'transcription') {
            const t = item.data;
            return (
              <div key={`transcription-${index}`} className={`flex flex-col ${t.speaker === 'User' ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[80%] rounded-xl p-4 ${
                  t.speaker === 'User' 
                    ? 'bg-primary/5 dark:bg-primary/10 border border-primary/20' 
                    : 'bg-surface dark:bg-surface-elevated border border-border'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-bold uppercase ${
                      t.speaker === 'User' ? 'text-primary' : 'text-accent'
                    }`}>
                      {t.speaker}
                    </span>
                    <span className="text-xs text-text-muted">
                      {new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-text-primary leading-relaxed">{t.text}</p>
                </div>
              </div>
            );
          } else {
            const a = item.data;
            return (
              <div key={`answer-${index}`} className="flex flex-col items-center my-8">
                <div className="w-full max-w-3xl bg-surface dark:bg-surface-elevated rounded-xl border border-border overflow-hidden">
                  <div className="bg-gradient-to-r from-indigo-500/10 to-purple-500/10 dark:from-indigo-500/20 dark:to-purple-500/20 px-6 py-3 border-b border-border flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white uppercase bg-gradient-to-r from-indigo-500 to-purple-600 px-2.5 py-1 rounded-md">
                        AI Assistant
                      </span>
                      <span className="text-xs text-text-secondary">re: {a.question.slice(0, 40)}{a.question.length > 40 ? '...' : ''}</span>
                    </div>
                    <div className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                      a.confidence === 'high' ? 'bg-success/10 text-success' :
                      a.confidence === 'medium' ? 'bg-warning/10 text-warning' :
                      'bg-destructive/10 text-destructive'
                    }`}>
                      {a.confidence} confidence
                    </div>
                  </div>
                  <div className="p-6">
                    <div className="prose prose-sm dark:prose-invert max-w-none text-text-primary">
                      {a.answer}
                    </div>
                  </div>
                </div>
              </div>
            );
          }
        })}
        
        {timelineItems.length === 0 && (
            <div className="text-center py-12 text-text-muted italic">
                No conversation data recorded for this session.
            </div>
        )}
      </div>
    </div>
  );
};
