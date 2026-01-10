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
          className="absolute inset-0 bg-gray-500 bg-opacity-75 transition-opacity" 
          onClick={onClose}
          aria-hidden="true"
        ></div>

        <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
          <div className="pointer-events-auto w-screen max-w-2xl transform transition ease-in-out duration-500 sm:duration-700">
            <div className="flex h-full flex-col overflow-y-scroll bg-white shadow-xl">
              
              {/* Conditional Rendering: Viewer or List */}
              {viewingSessionId ? (
                <SessionViewer 
                  sessionId={viewingSessionId} 
                  onBack={() => setViewingSessionId(null)} 
                />
              ) : (
                <>
                  {/* Header */}
                  <div className="px-4 py-6 sm:px-6 border-b border-gray-200">
                    <div className="flex items-start justify-between">
                      <h2 className="text-xl font-semibold text-gray-900" id="slide-over-title">
                        Session History
                      </h2>
                      <div className="ml-3 flex h-7 items-center">
                        <button
                          type="button"
                          className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                          onClick={onClose}
                        >
                          <span className="sr-only">Close panel</span>
                          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor" aria-hidden="true">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* List Content */}
                  <div className="relative mt-6 flex-1 px-4 sm:px-6">
                    {isHistoryLoading && savedSessions.length === 0 ? (
                      <div className="flex justify-center items-center h-48">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                      </div>
                    ) : savedSessions.length === 0 ? (
                      <div className="text-center text-gray-500 mt-12">
                        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <h3 className="mt-2 text-sm font-medium text-gray-900">No sessions found</h3>
                        <p className="mt-1 text-sm text-gray-500">Your interview history will appear here.</p>
                      </div>
                    ) : (
                      <ul className="space-y-4 pb-6">
                        {savedSessions.map((session) => (
                          <li key={session.id} className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
                            <div className="p-4">
                              <div className="flex justify-between items-start mb-2">
                                <div>
                                  <h3 className="text-lg font-medium text-gray-900">
                                    {formatDateTime(session.startedAt)}
                                  </h3>
                                  <p className="text-sm text-gray-500 flex items-center gap-2 mt-1">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {formatDuration(session.startedAt, session.endedAt)}
                                  </p>
                                </div>
                                <div className="flex space-x-2">
                                  <div className="relative group">
                                    <button 
                                      className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
                                      disabled={exportingId === session.id}
                                      title="Export"
                                    >
                                      {exportingId === session.id ? (
                                        <span className="block w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></span>
                                      ) : (
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                        </svg>
                                      )}
                                    </button>
                                    <div className="absolute right-0 mt-2 w-32 bg-white rounded-md shadow-lg py-1 hidden group-hover:block border border-gray-100 z-10">
                                      <button
                                        onClick={(e) => handleExport(e, session.id, 'md')}
                                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                      >
                                        Markdown
                                      </button>
                                      <button
                                        onClick={(e) => handleExport(e, session.id, 'json')}
                                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                                      >
                                        JSON
                                      </button>
                                    </div>
                                  </div>
                                  <button
                                    onClick={(e) => handleDelete(e, session.id)}
                                    className="p-2 text-red-400 hover:text-red-600 rounded-full hover:bg-red-50"
                                    title="Delete"
                                  >
                                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                  </button>
                                </div>
                              </div>
                              
                              <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 bg-gray-50 p-2 rounded">
                                <div className="flex items-center gap-1">
                                  <span className="font-medium">{session.transcriptionCount}</span> turns
                                </div>
                                <div className="flex items-center gap-1">
                                  <span className="font-medium">{session.answerCount}</span> answers
                                </div>
                                <div className="flex items-center gap-1">
                                  <span className="font-medium">{session.contextFiles.length}</span> files
                                </div>
                              </div>

                              <button
                                onClick={() => setViewingSessionId(session.id)}
                                className="mt-3 w-full flex justify-center items-center px-4 py-2 border border-blue-600 text-sm font-medium rounded-md text-blue-600 bg-white hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                              >
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
