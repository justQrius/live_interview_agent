/**
 * Frontend Logger Utility
 * 
 * Provides structured logging that integrates with Tauri's log plugin.
 * Logs are automatically saved to the app's log directory.
 * 
 * Log file location:
 * - Windows: %APPDATA%/com.live-interview-agent/logs/
 * - macOS: ~/Library/Logs/com.live-interview-agent/
 * - Linux: ~/.config/com.live-interview-agent/logs/
 */

import { trace, debug, info, warn, error, attachConsole } from '@tauri-apps/plugin-log';

// Attach console to forward browser console.log to the log file
let consoleAttached = false;

async function ensureConsoleAttached(): Promise<void> {
  if (consoleAttached) return;
  try {
    await attachConsole();
    consoleAttached = true;
  } catch (e) {
    // Silently fail if running outside Tauri
    console.debug('[Logger] Running outside Tauri, using console only');
  }
}

// Initialize on module load
ensureConsoleAttached();

/**
 * Create a scoped logger for a specific component
 */
export function createLogger(component: string) {
  const formatMessage = (message: string) => `[${component}] ${message}`;
  
  return {
    trace: (message: string) => {
      const msg = formatMessage(message);
      console.debug(msg);
      trace(msg).catch(() => {});
    },
    debug: (message: string) => {
      const msg = formatMessage(message);
      console.debug(msg);
      debug(msg).catch(() => {});
    },
    info: (message: string) => {
      const msg = formatMessage(message);
      console.info(msg);
      info(msg).catch(() => {});
    },
    warn: (message: string) => {
      const msg = formatMessage(message);
      console.warn(msg);
      warn(msg).catch(() => {});
    },
    error: (message: string, err?: unknown) => {
      const msg = err ? `${formatMessage(message)}: ${String(err)}` : formatMessage(message);
      console.error(msg);
      error(msg).catch(() => {});
    },
  };
}

// Pre-create common loggers for easy import
export const wsLogger = createLogger('WebSocket');
export const audioLogger = createLogger('Audio');
export const uiLogger = createLogger('UI');
export const storeLogger = createLogger('Store');
