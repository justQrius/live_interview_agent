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
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-4">Context Documents</h2>
      
      <div className="space-y-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileSelect}
          className="hidden"
          multiple
          accept=".pdf,.docx,.txt,.md"
        />
        
        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={!isConnected || isUploading || isInferring}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
        >
          {isUploading ? (
            <span>Processing...</span>
          ) : isInferring ? (
            <span>Analyzing...</span>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
              <span>Add Documents</span>
            </>
          )}
        </button>

        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors duration-200 ${
            isDragging 
              ? 'border-blue-500 bg-blue-50' 
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <p className="text-gray-500 text-sm">Drag and drop files here</p>
          <p className="text-gray-400 text-xs mt-1">PDF, DOCX, TXT, MD supported</p>
        </div>

        {/* Staged Files - Pending Confirmation */}
        {stagedFiles.length > 0 && (
          <div className="mt-4 border-2 border-blue-200 rounded-lg p-3 bg-blue-50">
            <h3 className="text-sm font-medium text-blue-800 mb-2 flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              Review & Confirm ({stagedFiles.length} file{stagedFiles.length > 1 ? 's' : ''})
            </h3>
            <p className="text-xs text-blue-600 mb-3">
              AI detected document types. Adjust if needed, then confirm.
            </p>
            
            <ul className="space-y-2 max-h-48 overflow-y-auto">
              {stagedFiles.map((file) => (
                <li key={file.id} className="flex items-center justify-between p-2 bg-white rounded border border-blue-200 gap-2">
                  <div className="flex items-center gap-2 overflow-hidden flex-1">
                    <DocumentTypeSelector 
                      value={file.inferredType} 
                      onChange={(newType) => updateStagedFileType(file.id, newType)}
                      filename={file.name}
                    />
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-sm text-gray-700 truncate" title={file.name}>
                        {file.name}
                      </span>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span>{formatFileSize(file.size)}</span>
                        {file.isInferring ? (
                          <span className="text-blue-600 animate-pulse">Analyzing...</span>
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
                    className="text-gray-400 hover:text-red-500 transition-colors p-1"
                    title="Remove file"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </li>
              ))}
            </ul>
            
            <div className="flex gap-2 mt-3">
              <button
                onClick={confirmUpload}
                disabled={isInferring || isUploading}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium py-2 px-4 rounded transition duration-200"
              >
                {isUploading ? 'Uploading...' : 'Confirm Upload'}
              </button>
              <button
                onClick={() => setStagedFiles([])}
                disabled={isUploading}
                className="bg-gray-200 hover:bg-gray-300 text-gray-700 text-sm font-medium py-2 px-4 rounded transition duration-200"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Loaded Files */}
        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Loaded Documents ({loadedContextFiles.length}):
          </h3>
          
          {loadedContextFiles.length === 0 ? (
            <div className="p-3 bg-gray-50 rounded text-sm text-gray-500 text-center italic">
              No documents loaded
            </div>
          ) : (
            <ul className="space-y-2 max-h-60 overflow-y-auto">
              {loadedContextFiles.map((file) => (
                <li key={file.id} className="flex flex-col p-2 bg-gray-50 rounded border border-gray-200 gap-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 overflow-hidden flex-1">
                      <DocumentTypeSelector 
                        value={file.type} 
                        onChange={(newType) => updateContextFile(file.id, { type: newType })}
                        filename={file.name}
                      />
                      <div className="flex flex-col overflow-hidden">
                        <span className="text-sm text-gray-700 truncate" title={file.name}>
                          {file.name}
                        </span>
                        
                        {/* Status Message */}
                        {file.status === 'processing' && (
                          <span className="text-xs text-gray-500 truncate" title={file.processingMessage}>
                            {file.processingMessage || 'Processing...'}
                          </span>
                        )}
                        {file.status === 'error' && (
                          <span className="text-xs text-red-500 truncate" title={file.processingMessage}>
                            Error: {file.processingMessage}
                          </span>
                        )}
                        {file.status === 'pending' && (
                          <span className="text-xs text-gray-400">Queued...</span>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {/* Extraction Result (Sparkles) */}
                      {file.extractionResult && (
                        <div className="group relative">
                          <span className="text-yellow-500 cursor-help" aria-label="View Insights">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M5 2a1 1 0 011 1v1h1a1 1 0 010 2H6v1a1 1 0 01-2 0V6H3a1 1 0 010-2h1V3a1 1 0 011-1zm0 10a1 1 0 011 1v1h1a1 1 0 110 2H6v1a1 1 0 11-2 0v-1H3a1 1 0 110-2h1v-1a1 1 0 011-1zM12 2a1 1 0 01.967.744L14.146 7.2 17.5 9.134a1 1 0 010 1.732l-3.354 1.935-1.18 4.455a1 1 0 01-1.933 0L9.854 12.8 6.5 10.866a1 1 0 010-1.732l3.354-1.935 1.18-4.455A1 1 0 0112 2z" clipRule="evenodd" />
                            </svg>
                          </span>
                          <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-48 bg-gray-800 text-white text-xs p-2 rounded z-10 shadow-lg">
                            <p className="font-semibold mb-1">Extraction Insights:</p>
                            <p>{file.extractionResult.storyCount} stories</p>
                            <p>{file.extractionResult.hasFacts ? '✓ Facts extracted' : '• No facts found'}</p>
                            <p>{file.extractionResult.hasSummary ? '✓ Summary generated' : '• No summary'}</p>
                          </div>
                        </div>
                      )}

                      {/* Status Indicators */}
                      {file.status === 'ready' && (
                        <span className="text-green-500" title="Processing Complete">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                      
                      {file.status === 'error' && (
                        <div className="group relative">
                          <span className="text-red-500 cursor-help">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                            </svg>
                          </span>
                          <div className="absolute bottom-full right-0 mb-2 hidden group-hover:block w-48 bg-red-800 text-white text-xs p-2 rounded z-10 shadow-lg">
                            {file.processingMessage || 'Unknown error occurred'}
                          </div>
                        </div>
                      )}

                      <button 
                        onClick={() => removeContextFile(file.id)}
                        className="text-gray-400 hover:text-red-500 transition-colors p-1"
                        title="Remove file"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {file.status === 'processing' && (
                    <div className="w-full bg-gray-200 rounded-full h-1 mt-1 overflow-hidden">
                      <div 
                        className="bg-blue-600 h-1 rounded-full transition-all duration-300" 
                        style={{ width: `${file.progress || 0}%` }}
                      ></div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default ContextLoader;
