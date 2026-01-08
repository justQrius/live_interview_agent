import React, { useEffect, useState } from 'react';

interface LogEntry {
  timestamp: number;
  message: string;
  type: 'log' | 'error' | 'warn';
}

export const DebugPanel: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    console.log = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      if (message.includes('[ProviderSettings]') || message.includes('[SessionControls]') || message.includes('[SettingsPanel]')) {
        setLogs(prev => [...prev.slice(-19), { timestamp: Date.now(), message, type: 'log' }]);
      }
      originalLog.apply(console, args);
    };

    console.error = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      setLogs(prev => [...prev.slice(-19), { timestamp: Date.now(), message, type: 'error' }]);
      originalError.apply(console, args);
    };

    console.warn = (...args) => {
      const message = args.map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
      ).join(' ');
      
      setLogs(prev => [...prev.slice(-19), { timestamp: Date.now(), message, type: 'warn' }]);
      originalWarn.apply(console, args);
    };

    return () => {
      console.log = originalLog;
      console.error = originalError;
      console.warn = originalWarn;
    };
  }, []);

  if (!isExpanded && logs.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 w-96 bg-gray-900 text-white rounded-lg shadow-2xl z-50">
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h3 className="text-sm font-semibold">Debug Console</h3>
        <div className="flex gap-2">
          <button
            onClick={() => setLogs([])}
            className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
          >
            Clear
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded"
          >
            {isExpanded ? '▼' : '▲'}
          </button>
        </div>
      </div>
      
      {isExpanded && (
        <div className="p-3 max-h-96 overflow-y-auto font-mono text-xs">
          {logs.length === 0 ? (
            <div className="text-gray-500">No logs yet...</div>
          ) : (
            logs.map((log, idx) => (
              <div
                key={idx}
                className={`mb-2 ${
                  log.type === 'error' ? 'text-red-400' :
                  log.type === 'warn' ? 'text-yellow-400' :
                  'text-green-400'
                }`}
              >
                <div className="text-gray-500 text-[10px]">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </div>
                <div className="whitespace-pre-wrap break-words">{log.message}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};
