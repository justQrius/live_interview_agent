import React, { useEffect, useState } from 'react';

interface LogEntry {
  timestamp: number;
  message: string;
  type: 'log' | 'error' | 'warn';
}

export const DebugPanel: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [height, setHeight] = useState(200);

  useEffect(() => {
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    console.log = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      if (message.includes('[ProviderSettings]') || message.includes('[SessionControls]') || message.includes('[SettingsPanel]')) {
        setLogs(prev => [...prev.slice(-49), { timestamp: Date.now(), message, type: 'log' }]);
      }
      originalLog.apply(console, args);
    };

    console.error = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      setLogs(prev => [...prev.slice(-49), { timestamp: Date.now(), message, type: 'error' }]);
      originalError.apply(console, args);
    };

    console.warn = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      setLogs(prev => [...prev.slice(-49), { timestamp: Date.now(), message, type: 'warn' }]);
      originalWarn.apply(console, args);
    };

    return () => {
      console.log = originalLog;
      console.error = originalError;
      console.warn = originalWarn;
    };
  }, []);

  const errorCount = logs.filter(l => l.type === 'error').length;
  const warnCount = logs.filter(l => l.type === 'warn').length;

  // Don't render if no logs and not expanded
  if (!isExpanded && logs.length === 0) return null;

  return (
    <div 
      className={`fixed bottom-0 left-0 right-0 z-50 bg-gray-900 dark:bg-gray-950 border-t border-gray-700 shadow-2xl transition-all duration-300 ${
        isExpanded ? '' : 'translate-y-[calc(100%-40px)]'
      }`}
      style={{ height: isExpanded ? height : 40 }}
    >
      {/* Header / Toggle Bar */}
      <div 
        className="h-10 px-4 flex items-center justify-between bg-gray-800 dark:bg-gray-900 border-b border-gray-700 cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
            <span className="text-sm font-medium text-gray-300">Debug Console</span>
          </div>
          
          {/* Counters */}
          <div className="flex items-center gap-2">
            {errorCount > 0 && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
                {errorCount}
              </span>
            )}
            {warnCount > 0 && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400"></span>
                {warnCount}
              </span>
            )}
            {logs.length > 0 && errorCount === 0 && warnCount === 0 && (
              <span className="text-xs text-gray-500">{logs.length} entries</span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); setLogs([]); }}
            className="text-xs px-3 py-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
          >
            Clear
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
            className="p-1 text-gray-400 hover:text-gray-200 transition-colors"
          >
            <svg 
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
        </div>
      </div>
      
      {/* Resize Handle */}
      {isExpanded && (
        <div 
          className="absolute top-0 left-0 right-0 h-1 cursor-ns-resize hover:bg-blue-500/50 transition-colors"
          onMouseDown={(e) => {
            e.preventDefault();
            const startY = e.clientY;
            const startHeight = height;
            
            const onMouseMove = (e: MouseEvent) => {
              const delta = startY - e.clientY;
              setHeight(Math.max(100, Math.min(500, startHeight + delta)));
            };
            
            const onMouseUp = () => {
              document.removeEventListener('mousemove', onMouseMove);
              document.removeEventListener('mouseup', onMouseUp);
            };
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
          }}
        />
      )}
      
      {/* Log Content */}
      {isExpanded && (
        <div className="h-[calc(100%-40px)] overflow-y-auto p-3 font-mono text-xs">
          {logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <span>No logs captured yet...</span>
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 py-1.5 px-2 rounded hover:bg-gray-800/50 ${
                    log.type === 'error' ? 'bg-red-500/10' :
                    log.type === 'warn' ? 'bg-yellow-500/10' :
                    ''
                  }`}
                >
                  <span className="text-gray-600 flex-shrink-0 tabular-nums">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className={`flex-shrink-0 w-12 ${
                    log.type === 'error' ? 'text-red-400' :
                    log.type === 'warn' ? 'text-yellow-400' :
                    'text-green-400'
                  }`}>
                    [{log.type.toUpperCase()}]
                  </span>
                  <span className={`whitespace-pre-wrap break-all ${
                    log.type === 'error' ? 'text-red-300' :
                    log.type === 'warn' ? 'text-yellow-300' :
                    'text-gray-300'
                  }`}>
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
