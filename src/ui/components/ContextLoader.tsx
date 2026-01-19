import React, { useRef, useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSessionStore } from '../store/sessionStore';
import DocumentTypeSelector, { detectDocumentType, DocumentType } from './DocumentTypeSelector';

interface StagedFile {
  id: string;
  name: string;
  size: number;
  content: string; // base64
  inferredType: DocumentType;
  confidence: number;
  reason: string;
  isInferring: boolean;
}

const ContextLoader: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { sendMessage, isConnected, addMessageHandler, removeMessageHandler } = useWebSocket();
  const loadedContextFiles = useSessionStore((state) => state.loadedContextFiles);
  const addContextFile = useSessionStore((state) => state.addContextFile);
  const updateContextFile = useSessionStore((state) => state.updateContextFile);
  const removeContextFile = useSessionStore((state) => state.removeContextFile);
  const setContextStatus = useSessionStore((state) => state.setContextStatus);
  const contextStatus = useSessionStore((state) => state.contextStatus);
  const ragState = useSessionStore((state) => state.ragState);
  const setRagLoading = useSessionStore((state) => state.setRagLoading);
  const setRagRefreshing = useSessionStore((state) => state.setRagRefreshing);
  const setRagClearing = useSessionStore((state) => state.setRagClearing);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  
  // Staging state for hybrid classification
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [isInferring, setIsInferring] = useState(false);

  // Load RAG state on mount (only when connection state changes)
  useEffect(() => {
    if (isConnected) {
      setRagLoading(true);
      sendMessage({ type: 'LOAD_RAG_STATE', data: {} });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  // Handle messages from backend
  useEffect(() => {
    const handleMessage = (message: { type: string; data?: unknown }) => {
      if (message.type === 'DOCUMENT_TYPE_SUGGESTIONS') {
        // After analysis, still analyzing until user confirms upload
        const data = message.data as {
          suggestions: Array<{
            id: string;
            filename: string;
            documentType: DocumentType;
            confidence: number;
            reason: string;
          }>;
        };

        // Update staged files with inferred types
        setStagedFiles(prev => prev.map(file => {
          const suggestion = data.suggestions.find(s => s.id === file.id);
          if (suggestion) {
            return {
              ...file,
              inferredType: suggestion.documentType,
              confidence: suggestion.confidence,
              reason: suggestion.reason,
              isInferring: false
            };
          }
          return { ...file, isInferring: false };
        }));
        setIsInferring(false);
        // Keep 'analyzing' status until user confirms upload
      } else if (message.type === 'PREPARATION_READY') {
        // RAG processing is complete
        setContextStatus('rag_ready');
      }
    };

    addMessageHandler(handleMessage);
    return () => removeMessageHandler(handleMessage);
  }, [addMessageHandler, removeMessageHandler, setContextStatus]);

  // Track context status based on loaded files
  useEffect(() => {
    if (loadedContextFiles.length === 0) {
      setContextStatus('empty');
      return;
    }

    const allReady = loadedContextFiles.every(f => f.status === 'ready');
    const anyError = loadedContextFiles.some(f => f.status === 'error');
    const anyProcessing = loadedContextFiles.some(f => f.status === 'processing');

    if (anyError) {
      setContextStatus('error');
    } else if (allReady) {
      // All files ready, but RAG might still be processing
      // Check if we have preparation summary (RAG ready indicator)
      const preparationStatus = useSessionStore.getState().preparationStatus;
      if (preparationStatus === 'ready') {
        setContextStatus('rag_ready');
      } else {
        setContextStatus('cache_ready');
      }
    } else if (anyProcessing) {
      // Files are being processed (extraction, RAG, etc.)
      setContextStatus('uploading');
    }
  }, [loadedContextFiles, setContextStatus]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await stageFiles(Array.from(e.target.files));
    }
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await stageFiles(Array.from(e.dataTransfer.files));
    }
  };

  const stageFiles = async (files: File[]) => {
    if (!isConnected) {
      console.error('Cannot stage: WebSocket disconnected');
      return;
    }

    const newStagedFiles: StagedFile[] = [];
    const inferencePayload: Array<{ id: string; filename: string; content: string }> = [];

    for (const file of files) {
      try {
        const base64Content = await readFileAsBase64(file);
        const id = crypto.randomUUID();
        const heuristicType = detectDocumentType(file.name);
        
        newStagedFiles.push({
          id,
          name: file.name,
          size: file.size,
          content: base64Content,
          inferredType: heuristicType, // Start with heuristic
          confidence: 0.5, // Medium confidence for heuristic
          reason: 'Analyzing...',
          isInferring: true
        });
        
        inferencePayload.push({
          id,
          filename: file.name,
          content: base64Content
        });
      } catch (error) {
        console.error(`Failed to read file ${file.name}:`, error);
      }
    }

    if (newStagedFiles.length > 0) {
      setStagedFiles(prev => [...prev, ...newStagedFiles]);
      setIsInferring(true);
      setContextStatus('analyzing');
      
      // Fetch API keys for LLM-based document type inference
      const apiKeys: Record<string, string> = {};
      const providers = ['gemini', 'groq', 'openai', 'anthropic', 'deepgram'];
      
      try {
        await Promise.all(providers.map(async (provider) => {
          try {
            const key = await invoke<string>('get_api_key', { provider });
            if (key) {
              apiKeys[provider] = key;
            }
          } catch {
            // Ignore missing keys
          }
        }));
      } catch (e) {
        console.warn('Failed to fetch API keys for inference:', e);
      }
      
      // Request LLM-based type inference (with API keys for provider initialization)
      sendMessage({
        type: 'INFER_DOCUMENT_TYPES',
        data: { files: inferencePayload, apiKeys }
      });
    }
  };

  const updateStagedFileType = (fileId: string, newType: DocumentType) => {
    setStagedFiles(prev => prev.map(f => 
      f.id === fileId 
        ? { ...f, inferredType: newType, confidence: 1.0, reason: 'User selected' } 
        : f
    ));
  };

  const removeStagedFile = (fileId: string) => {
    setStagedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const confirmUpload = async () => {
    if (stagedFiles.length === 0) return;

    setIsUploading(true);
    setContextStatus('uploading');
    
    // Fetch API keys for sidecar auto-initialization
    const apiKeys: Record<string, string> = {};
    const providers = ['gemini', 'groq', 'openai', 'anthropic', 'deepgram'];
    
    try {
      await Promise.all(providers.map(async (provider) => {
        try {
          const key = await invoke<string>('get_api_key', { provider });
          if (key) {
            apiKeys[provider] = key;
          }
        } catch (e) {
          // Ignore missing keys
        }
      }));
    } catch (e) {
      console.warn('Failed to fetch API keys for upload:', e);
    }

    const filesData = stagedFiles.map(file => ({
      name: file.name,
      content: file.content,
      documentType: file.inferredType
    }));

    // Add to loaded files
    stagedFiles.forEach(file => {
      addContextFile({
        id: file.id,
        name: file.name,
        type: file.inferredType,
        size: file.size,
        uploadDate: Date.now(),
        preview: `${file.inferredType} (${Math.round(file.confidence * 100)}% confidence)`,
        status: 'pending',
        progress: 0,
        processingMessage: 'Queued...'
      });
    });

    // Send to backend
    sendMessage({
      type: 'UPLOAD_CONTEXT',
      data: { 
        files: filesData,
        apiKeys
      }
    });

    // Clear staged files
    setStagedFiles([]);
    setIsUploading(false);
  };

  const readFileAsBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.8) {
      return <span className="text-[10px] px-1 py-0.5 rounded bg-green-100 text-green-700">High</span>;
    } else if (confidence >= 0.5) {
      return <span className="text-[10px] px-1 py-0.5 rounded bg-yellow-100 text-yellow-700">Med</span>;
    } else {
      return <span className="text-[10px] px-1 py-0.5 rounded bg-red-100 text-red-700">Low</span>;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Refresh Gemini cache for existing documents
  const handleRefreshCache = async () => {
    if (!isConnected) return;
    
    setRagRefreshing(true);
    
    // Fetch API keys for cache refresh
    const apiKeys: Record<string, string> = {};
    const providers = ['gemini', 'groq', 'openai', 'anthropic', 'deepgram'];
    
    try {
      await Promise.all(providers.map(async (provider) => {
        try {
          const key = await invoke<string>('get_api_key', { provider });
          if (key) {
            apiKeys[provider] = key;
          }
        } catch {
          // Ignore missing keys
        }
      }));
    } catch (e) {
      console.warn('Failed to fetch API keys for cache refresh:', e);
    }
    
    sendMessage({
      type: 'REFRESH_CACHE',
      data: { apiKeys }
    });
  };

  // Clear all RAG data (ChromaDB, MemoryStore, manifest)
  const handleClearAllData = () => {
    if (!isConnected) return;
    
    setRagClearing(true);
    setShowClearConfirm(false);
    
    sendMessage({
      type: 'CLEAR_ALL_DATA',
      data: {}
    });
  };

  return (
    <div className="space-y-3">
      {/* Minimal Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-primary">Context Documents</h2>
        <div className="flex items-center gap-2">
          {(loadedContextFiles.length > 0 || ragState.hasDocuments) && (
            <span className="text-xs text-text-muted">
              {loadedContextFiles.length || ragState.documentCount} loaded
            </span>
          )}
          {/* Clear All Data button */}
          {(loadedContextFiles.length > 0 || ragState.hasDocuments) && (
            <button
              onClick={() => setShowClearConfirm(true)}
              disabled={ragState.isClearing}
              className="text-xs text-text-muted hover:text-destructive transition-colors"
              title="Clear all data"
            >
              {ragState.isClearing ? (
                <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Cache Expired Warning */}
      {contextStatus === 'cache_expired' && ragState.hasDocuments && (
        <div className="flex items-center justify-between p-2.5 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-xs text-amber-800 dark:text-amber-300">
              Cache expired • {ragState.documentCount} docs available
            </span>
          </div>
          <button
            onClick={handleRefreshCache}
            disabled={ragState.isRefreshing}
            className="flex items-center gap-1 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium py-1 px-2.5 rounded transition-colors"
          >
            {ragState.isRefreshing ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Refreshing...</span>
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh Cache</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Existing Docs from Previous Session */}
      {ragState.hasDocuments && loadedContextFiles.length === 0 && contextStatus !== 'cache_expired' && (
        <div className="p-2.5 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800/50 rounded-lg">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-xs text-green-800 dark:text-green-300">
              {ragState.documentCount} docs restored from previous session
            </span>
          </div>
          <ul className="mt-2 space-y-1">
            {ragState.documents.slice(0, 3).map((doc, idx) => (
              <li key={idx} className="text-[10px] text-green-700 dark:text-green-400 truncate pl-6">
                • {doc.filename} ({doc.documentType})
              </li>
            ))}
            {ragState.documentCount > 3 && (
              <li className="text-[10px] text-green-600 dark:text-green-500 pl-6">
                +{ragState.documentCount - 3} more...
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Clear Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface border border-border rounded-xl p-4 max-w-sm mx-4 shadow-xl">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Clear All Data?</h3>
            <p className="text-xs text-text-muted mb-4">
              This will permanently delete all uploaded documents, extracted data, and cached context. 
              You'll need to re-upload your documents.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="text-xs text-text-secondary hover:text-text-primary py-1.5 px-3 rounded border border-border transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleClearAllData}
                className="bg-destructive hover:bg-red-600 text-white text-xs font-medium py-1.5 px-3 rounded transition-colors"
              >
                Clear Everything
              </button>
            </div>
          </div>
        </div>
      )}
      
      <div className="space-y-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          multiple
          accept=".pdf,.docx,.txt,.md"
        />
        
        {/* Compact Upload Zone */}
        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && !isInferring && fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-4 text-center transition-all duration-200 cursor-pointer ${
            isDragging 
              ? 'border-primary bg-blue-50 dark:bg-blue-900/20' 
              : 'border-border hover:border-primary/50 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          } ${(isUploading || isInferring) ? 'opacity-60 cursor-not-allowed' : ''}`}
        >
          <div className="flex flex-col items-center gap-1.5">
            {isUploading ? (
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            ) : isInferring ? (
              <div className="w-6 h-6 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-6 h-6 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
            <div>
              <p className="text-xs font-medium text-text-primary">
                {isUploading ? 'Processing...' : isInferring ? 'Analyzing...' : 'Drop files here'}
              </p>
            </div>
          </div>
        </div>

        {/* Staged Files - Compact */}
        {stagedFiles.length > 0 && (
          <div className="border border-blue-200 dark:border-blue-800/50 rounded-lg p-3 bg-blue-50/30 dark:bg-blue-900/10">
            <h3 className="text-xs font-medium text-blue-800 dark:text-blue-300 mb-2 flex items-center gap-1.5">
              Review ({stagedFiles.length})
            </h3>
            
            <ul className="space-y-1.5 max-h-32 overflow-y-auto mb-3">
              {stagedFiles.map((file) => (
                <li key={file.id} className="flex items-center justify-between p-2 bg-surface rounded border border-border gap-2">
                  <div className="flex items-center gap-2 overflow-hidden flex-1">
                    <div className="scale-90 origin-left">
                      <DocumentTypeSelector 
                        value={file.inferredType} 
                        onChange={(newType) => updateStagedFileType(file.id, newType)}
                        filename={file.name}
                      />
                    </div>
                    <div className="flex flex-col overflow-hidden min-w-0">
                      <span className="text-xs text-text-primary truncate" title={file.name}>
                        {file.name}
                      </span>
                      <div className="flex items-center gap-2 text-[10px] text-text-muted">
                        <span>{formatFileSize(file.size)}</span>
                        {!file.isInferring && getConfidenceBadge(file.confidence)}
                      </div>
                    </div>
                  </div>
                  <button 
                    onClick={() => removeStagedFile(file.id)}
                    className="text-text-muted hover:text-destructive transition-colors"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
            
            <div className="flex gap-2">
              <button
                onClick={confirmUpload}
                disabled={isInferring || isUploading}
                className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white text-xs font-medium py-1.5 px-3 rounded-lg transition-all shadow-sm"
              >
                {isUploading ? 'Uploading...' : 'Confirm Upload'}
              </button>
              <button
                onClick={() => setStagedFiles([])}
                disabled={isUploading}
                className="bg-surface border border-border text-text-secondary hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-medium py-1.5 px-3 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Loaded Files - Compact List */}
        {loadedContextFiles.length > 0 && (
          <div className="max-h-48 overflow-y-auto pr-1 scrollbar-thin">
            <ul className="space-y-1.5">
              {loadedContextFiles.map((file) => (
                <li key={file.id} className="flex flex-col p-2 bg-slate-50 dark:bg-slate-800/30 rounded border border-border gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 overflow-hidden flex-1">
                      <div className="scale-90 origin-left">
                        <DocumentTypeSelector 
                          value={file.type} 
                          onChange={(newType) => updateContextFile(file.id, { type: newType })}
                          filename={file.name}
                        />
                      </div>
                      <div className="flex flex-col overflow-hidden min-w-0">
                        <span className="text-xs text-text-primary truncate" title={file.name}>
                          {file.name}
                        </span>
                        
                        {/* Status Message */}
                        {file.status === 'processing' && (
                          <span className="text-[10px] text-blue-600 dark:text-blue-400 truncate">
                            {file.processingMessage || 'Processing...'}
                          </span>
                        )}
                        {file.status === 'error' && (
                          <span className="text-[10px] text-destructive truncate">
                            Error: {file.processingMessage}
                          </span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-1.5">
                      {/* Status Indicators */}
                      {file.status === 'ready' && (
                        <span className="text-success" title="Ready">
                          <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                      
                      <button 
                        onClick={() => removeContextFile(file.id)}
                        className="text-text-muted hover:text-destructive transition-colors"
                        title="Remove file"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {file.status === 'processing' && (
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-0.5 mt-0.5 overflow-hidden">
                      <div 
                        className="bg-primary h-0.5 rounded-full transition-all duration-300" 
                        style={{ width: `${file.progress || 0}%` }}
                      />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {loadedContextFiles.length === 0 && stagedFiles.length === 0 && (
          <div className="p-3 bg-slate-50 dark:bg-slate-800/30 rounded border border-border border-dashed text-center">
            <p className="text-xs text-text-muted italic">No documents loaded</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextLoader;
