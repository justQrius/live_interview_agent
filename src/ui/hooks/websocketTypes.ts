// WebSocket message types (as per architecture)
export type MessageType =
  | 'START_SESSION'
  | 'STOP_SESSION'
  | 'UPLOAD_CONTEXT'
  | 'CALIBRATE_VOICE'
  | 'MANUAL_QUESTION'
  | 'AUDIO_CHUNK'
  | 'TRANSCRIPTION'
  | 'ANSWER_CHUNK'
  | 'ERROR'
  | 'STATUS';

export interface WebSocketMessage {
  type: MessageType;
  data?: unknown;
}
