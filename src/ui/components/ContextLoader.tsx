import React, { useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { useWebSocket } from '../hooks/useWebSocket';
import { useSessionStore } from '../store/sessionStore';
import DocumentTypeSelector, { detectDocumentType } from './DocumentTypeSelector';

const ContextLoader: React.FC = () => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { sendMessage, isConnected } = useWebSocket();
  const loadedContextFiles = useSessionStore((state) => state.loadedContextFiles);
  const addContextFile = useSessionStore((state) => state.addContextFile);
  const updateContextFile = useSessionStore((state) => state.updateContextFile);
  const removeContextFile = useSessionStore((state) => state.removeContextFile);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await processFiles(Array.from(e.target.files));
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
      await processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const processFiles = async (files: File[]) => {
    if (!isConnected) {
      console.error('Cannot upload: WebSocket disconnected');
      return;
    }

    setIsUploading(true);
    const filesData = [];

    for (const file of files) {
      try {
        const base64Content = await readFileAsBase64(file);
        const docType = detectDocumentType(file.name);
        
        filesData.push({
          name: file.name,
          content: base64Content,
          type: docType
        });

        addContextFile({
          id: crypto.randomUUID(),
          name: file.name,
          type: docType,
          size: file.size,
          uploadDate: Date.now(),
          preview: 'Uploading...'
        });
      } catch (error) {
        console.error(`Failed to read file ${file.name}:`, error);
      }
    }

    if (filesData.length > 0) {
      // Fetch API keys to allow sidecar to auto-initialize extraction
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

      sendMessage({
        type: 'UPLOAD_CONTEXT',
        data: { 
          files: filesData,
          apiKeys // Include keys so sidecar can extract metadata immediately
        }
      });
    }
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
          accept=".pdf,.docx,.txt"
        />
        
        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={!isConnected || isUploading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-medium py-2 px-4 rounded-lg transition duration-200 flex items-center justify-center gap-2"
        >
          {isUploading ? (
            <span>Processing...</span>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
              </svg>
              <span>Upload Documents</span>
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
          <p className="text-gray-400 text-xs mt-1">PDF, DOCX, TXT supported</p>
        </div>

        <div className="mt-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">
            Loaded Documents ({loadedContextFiles.length}):
          </h3>
          
          {loadedContextFiles.length === 0 ? (
            <div className="p-3 bg-gray-50 rounded text-sm text-gray-500 text-center italic">
              No documents loaded
            </div>
          ) : (
            <ul className="space-y-2 max-h-40 overflow-y-auto">
              {loadedContextFiles.map((file) => (
                <li key={file.id} className="flex items-center justify-between p-2 bg-gray-50 rounded border border-gray-200 gap-2">
                  <div className="flex items-center gap-2 overflow-hidden flex-1">
                    <DocumentTypeSelector 
                      value={file.type} 
                      onChange={(newType) => updateContextFile(file.id, { type: newType })}
                      filename={file.name}
                    />
                    <span className="text-sm text-gray-700 truncate" title={file.name}>
                      {file.name}
                    </span>
                  </div>
                  <button 
                    onClick={() => removeContextFile(file.id)}
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
          )}
        </div>
      </div>
    </div>
  );
};

export default ContextLoader;
