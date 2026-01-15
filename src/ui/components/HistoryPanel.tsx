import React, { useEffect, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { useWebSocket } from '../hooks/useWebSocket';
import { SessionViewer } from './SessionViewer';

interface HistoryPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

function formatDuration(startMs: number, endMs: number | null): string {
  if (!endMs) return 'In progress';
  const minutes = Math.round((endMs - startMs) / 60000);
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainingMins = minutes % 60;
  return `${hours}h ${remainingMins}m`;
}

function formatDateTime(timestamp: number): string {
  return new Date(timestamp).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ isOpen, onClose }) => {
  const { listSessions, deleteSession, exportSession } = useWebSocket();
  const savedSessions = useSessionStore((state) => state.savedSessions);
  const isHistoryLoading = useSessionStore((state) => state.isHistoryLoading);
  
  const [viewingSessionId, setViewingSessionId] = useState<string | null>(null);
  const [exportingId, setExportingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      listSessions();
      setViewingSessionId(null);
    }
  }, [isOpen]);

  const handleDelete = (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
      deleteSession(sessionId);
    }
  };

  const handleExport = async (e: React.MouseEvent, sessionId: string, format: 'md' | 'json') => {
    e.stopPropagation();
    setExportingId(sessionId);
    try {
      const content = await exportSession(sessionId, format);
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `session-${sessionId}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed', error);
    } finally {
      setExportingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" aria-labelledby="slide-over-title" role="dialog" aria-modal="true">
      <div className="absolute inset-0 overflow-hidden">
        {/* Background overlay */}
        <div 
          className="absolute inset-0 bg-black/50 dark:bg-black/70 backdrop-blur-sm transition-opacity" 
          onClick={onClose}
          aria-hidden="true"
        ></div>

        <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
          <div className="pointer-events-auto w-screen max-w-2xl transform transition ease-in-out duration-300">
            <div className="flex h-full flex-col overflow-hidden bg-background dark:bg-background shadow-2xl">
              
              {/* Conditional Rendering: Viewer or List */}
              {viewingSessionId ? (
                <SessionViewer 
                  sessionId={viewingSessionId} 
                  onBack={() => setViewingSessionId(null)} 
                />
              ) : (
                <>
                  {/* Header */}
                  <div className="px-6 py-5 border-b border-border bg-surface dark:bg-surface-elevated">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
                          <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <div>
                          <h2 className="text-xl font-semibold text-text-primary" id="slide-over-title">
                            Session History
                          </h2>
                          <p className="text-sm text-text-muted mt-0.5">
                            {savedSessions.length} session{savedSessions.length !== 1 ? 's' : ''} recorded
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-elevated dark:hover:bg-surface transition-colors"
                        onClick={onClose}
                      >
                        <span className="sr-only">Close panel</span>
                        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* List Content */}
                  <div className="relative flex-1 overflow-y-auto p-6">
                    {isHistoryLoading && savedSessions.length === 0 ? (
                      <div className="flex flex-col justify-center items-center h-48 gap-3">
                        <div className="w-10 h-10 rounded-full border-2 border-primary border-t-transparent animate-spin"></div>
                        <p className="text-sm text-text-muted">Loading sessions...</p>
                      </div>
                    ) : savedSessions.length === 0 ? (
                      <div className="text-center py-16">
                        <div className="w-16 h-16 rounded-full bg-surface-elevated dark:bg-surface mx-auto flex items-center justify-center mb-4">
                          <svg className="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </div>
                        <h3 className="text-lg font-medium text-text-primary mb-1">No sessions yet</h3>
                        <p className="text-sm text-text-muted">Your interview sessions will appear here</p>
                      </div>
                    ) : (
                      <ul className="space-y-4">
                        {savedSessions.map((session) => (
                          <li 
                            key={session.id} 
                            className="bg-surface dark:bg-surface-elevated border border-border rounded-xl overflow-hidden hover:border-primary/30 transition-all group"
                          >
                            <div className="p-5">
                              <div className="flex justify-between items-start mb-3">
                                <div>
                                  <h3 className="text-lg font-medium text-text-primary group-hover:text-primary transition-colors">
                                    {formatDateTime(session.startedAt)}
                                  </h3>
                                  <p className="text-sm text-text-muted flex items-center gap-2 mt-1">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {formatDuration(session.startedAt, session.endedAt)}
                                  </p>
                                </div>
                                <div className="flex items-center gap-1">
                                  {/* Export dropdown */}
                                  <div className="relative group/export">
                                    <button 
                                      className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-elevated dark:hover:bg-surface transition-colors"
                                      disabled={exportingId === session.id}
                                      title="Export"
                                    >
                                      {exportingId === session.id ? (
                                        <span className="block w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></span>
                                      ) : (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                        </svg>
                                      )}
                                    </button>
                                    <div className="absolute right-0 mt-1 w-36 bg-surface dark:bg-surface-elevated rounded-xl shadow-lg py-2 hidden group-hover/export:block border border-border z-10">
                                      <button
                                        onClick={(e) => handleExport(e, session.id, 'md')}
                                        className="w-full text-left px-4 py-2 text-sm text-text-secondary hover:bg-surface-elevated dark:hover:bg-surface hover:text-text-primary transition-colors"
                                      >
                                        Markdown
                                      </button>
                                      <button
                                        onClick={(e) => handleExport(e, session.id, 'json')}
                                        className="w-full text-left px-4 py-2 text-sm text-text-secondary hover:bg-surface-elevated dark:hover:bg-surface hover:text-text-primary transition-colors"
                                      >
                                        JSON
                                      </button>
                                    </div>
                                  </div>
                                  {/* Delete button */}
                                  <button
                                    onClick={(e) => handleDelete(e, session.id)}
                                    className="p-2 rounded-lg text-text-muted hover:text-destructive hover:bg-destructive/10 transition-colors"
                                    title="Delete"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              </div>
                              
                              {/* Stats */}
                              <div className="flex items-center gap-4 text-sm mb-4">
                                <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated dark:bg-surface rounded-lg">
                                  <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                  </svg>
                                  <span className="font-medium text-text-primary">{session.transcriptionCount}</span>
                                  <span className="text-text-muted">turns</span>
                                </div>
                                <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated dark:bg-surface rounded-lg">
                                  <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  <span className="font-medium text-text-primary">{session.answerCount}</span>
                                  <span className="text-text-muted">answers</span>
                                </div>
                                <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-elevated dark:bg-surface rounded-lg">
                                  <svg className="w-4 h-4 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                  </svg>
                                  <span className="font-medium text-text-primary">{session.contextFiles.length}</span>
                                  <span className="text-text-muted">files</span>
                                </div>
                              </div>

                              <button
                                onClick={() => setViewingSessionId(session.id)}
                                className="w-full flex justify-center items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white text-sm font-medium rounded-xl transition-all shadow-sm"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                                View Session
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
