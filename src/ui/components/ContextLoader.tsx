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
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  
  // Staging state for hybrid classification
  const [stagedFiles, setStagedFiles] = useState<StagedFile[]>([]);
  const [isInferring, setIsInferring] = useState(false);

  // Handle DOCUMENT_TYPE_SUGGESTIONS message from backend
  useEffect(() => {
    const handleMessage = (message: { type: string; data?: unknown }) => {
      if (message.type === 'DOCUMENT_TYPE_SUGGESTIONS') {
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
      }
    };

    addMessageHandler(handleMessage);
    return () => removeMessageHandler(handleMessage);
  }, [addMessageHandler, removeMessageHandler]);

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
      
      // Request LLM-based type inference
      sendMessage({
        type: 'INFER_DOCUMENT_TYPES',
        data: { files: inferencePayload }
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
      return <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">High</span>;
    } else if (confidence >= 0.5) {
      return <span className="text-xs px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700">Medium</span>;
    } else {
      return <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700">Low</span>;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-border p-5 dark:shadow-none transition-colors">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-blue-600 dark:text-blue-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <div>
          <h2 className="text-base font-semibold text-text-primary">Context Documents</h2>
          <p className="text-xs text-text-muted">{loadedContextFiles.length} file{loadedContextFiles.length !== 1 ? 's' : ''} loaded</p>
        </div>
      </div>
      
      <div className="space-y-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          multiple
          accept=".pdf,.docx,.txt,.md"
        />
        
        {/* Upload Zone */}
        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && !isInferring && fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-200 cursor-pointer ${
            isDragging 
              ? 'border-primary bg-blue-50 dark:bg-blue-900/20' 
              : 'border-border hover:border-primary/50 hover:bg-slate-50 dark:hover:bg-slate-800/50'
          } ${(isUploading || isInferring) ? 'opacity-60 cursor-not-allowed' : ''}`}
        >
          <div className="flex flex-col items-center gap-2">
            {isUploading ? (
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            ) : isInferring ? (
              <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-8 h-8 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
            <div>
              <p className="text-sm font-medium text-text-primary">
                {isUploading ? 'Processing...' : isInferring ? 'Analyzing...' : 'Drop files or click to upload'}
              </p>
              <p className="text-xs text-text-muted mt-1">PDF, DOCX, TXT, MD supported</p>
            </div>
          </div>
        </div>

        {/* Staged Files - Pending Confirmation */}
        {stagedFiles.length > 0 && (
          <div className="border-2 border-blue-200 dark:border-blue-800 rounded-xl p-4 bg-blue-50/50 dark:bg-blue-900/10">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-2 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a10 10 0 11-20 0 10 10 0 0120 0z" />
              </svg>
              Review ({stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''})
            </h3>
            <p className="text-xs text-blue-600 dark:text-blue-400 mb-3">
              AI detected document types. Adjust if needed.
            </p>
            
            <ul className="space-y-2 max-h-40 overflow-y-auto">
              {stagedFiles.map((file) => (
                <li key={file.id} className="flex items-center justify-between p-2.5 bg-surface rounded-lg border border-border gap-2">
                  <div className="flex items-center gap-2 overflow-hidden flex-1">
                    <DocumentTypeSelector 
                      value={file.inferredType} 
                      onChange={(newType) => updateStagedFileType(file.id, newType)}
                      filename={file.name}
                    />
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-sm text-text-primary truncate" title={file.name}>
                        {file.name}
                      </span>
                      <div className="flex items-center gap-2 text-xs text-text-muted">
                        <span>{formatFileSize(file.size)}</span>
                        {file.isInferring ? (
                          <span className="text-blue-600 dark:text-blue-400 animate-pulse">Analyzing...</span>
                        ) : (
                          <>
                            {getConfidenceBadge(file.confidence)}
                            <span className="truncate" title={file.reason}>{file.reason}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                  <button 
                    onClick={() => removeStagedFile(file.id)}
                    className="text-text-muted hover:text-destructive transition-colors p-1"
                    title="Remove file"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
            
            <div className="flex gap-2 mt-3">
              <button
                onClick={confirmUpload}
                disabled={isInferring || isUploading}
                className="flex-1 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 disabled:from-slate-300 disabled:to-slate-400 dark:disabled:from-slate-700 dark:disabled:to-slate-800 text-white text-sm font-medium py-2 px-4 rounded-lg transition-all shadow-sm hover:shadow"
              >
                {isUploading ? 'Uploading...' : 'Confirm Upload'}
              </button>
              <button
                onClick={() => setStagedFiles([])}
                disabled={isUploading}
                className="bg-surface border border-border text-text-secondary hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium py-2 px-4 rounded-lg transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Loaded Files */}
        {loadedContextFiles.length > 0 && (
          <div className="mt-4">
            <h3 className="text-sm font-medium text-text-secondary mb-2">
              Loaded ({loadedContextFiles.length})
            </h3>
            
            <ul className="space-y-2 max-h-48 overflow-y-auto">
              {loadedContextFiles.map((file) => (
                <li key={file.id} className="flex flex-col p-2.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-border gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 overflow-hidden flex-1">
                      <DocumentTypeSelector 
                        value={file.type} 
                        onChange={(newType) => updateContextFile(file.id, { type: newType })}
                        filename={file.name}
                      />
                      <div className="flex flex-col overflow-hidden">
                        <span className="text-sm text-text-primary truncate" title={file.name}>
                          {file.name}
                        </span>
                        
                        {/* Status Message */}
                        {file.status === 'processing' && (
                          <span className="text-xs text-blue-600 dark:text-blue-400 truncate" title={file.processingMessage}>
                            {file.processingMessage || 'Processing...'}
                          </span>
                        )}
                        {file.status === 'error' && (
                          <span className="text-xs text-destructive truncate" title={file.processingMessage}>
                            Error: {file.processingMessage}
                          </span>
                        )}
                        {file.status === 'pending' && (
                          <span className="text-xs text-text-muted">Queued...</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {/* Extraction Result (Sparkles) */}
                      {file.extractionResult && (
                        <div className="group relative">
                          <span className="text-amber-500 cursor-help" aria-label="View Insights">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clipRule="evenodd" />
                            </svg>
                          </span>
                          <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-48 bg-slate-800 dark:bg-slate-700 text-white text-xs p-2 rounded-lg z-10 shadow-lg">
                            <p className="font-semibold mb-1">Extraction Insights:</p>
                            <p>{file.extractionResult.storyCount} stories</p>
                            <p>{file.extractionResult.hasFacts ? 'Facts extracted' : 'No facts found'}</p>
                            <p>{file.extractionResult.hasSummary ? 'Summary generated' : 'No summary'}</p>
                          </div>
                        </div>
                      )}

                      {/* Status Indicators */}
                      {file.status === 'ready' && (
                        <span className="text-success" title="Processing Complete">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                      
                      {file.status === 'error' && (
                        <div className="group relative">
                          <span className="text-destructive cursor-help">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </span>
                          <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-48 bg-red-800 text-white text-xs p-2 rounded-lg z-10 shadow-lg">
                            {file.processingMessage || 'Unknown error occurred'}
                          </div>
                        </div>
                      )}

                      <button 
                        onClick={() => removeContextFile(file.id)}
                        className="text-text-muted hover:text-destructive transition-colors p-1"
                        title="Remove file"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {file.status === 'processing' && (
                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1 mt-1 overflow-hidden">
                      <div 
                        className="bg-primary h-1 rounded-full transition-all duration-300" 
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
          <div className="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg text-center">
            <p className="text-sm text-text-muted italic">No documents loaded yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ContextLoader;
