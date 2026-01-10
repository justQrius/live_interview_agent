# STORY-039: Session Store - WebSocket Protocol

**Phase**: 3A (Foundation)
**Priority**: P1 - Must Have
**Effort**: 0.5 days
**Dependencies**: STORY-038

## Description

Extend the WebSocket protocol to support session history operations: list sessions, load session, export session, delete session.

## Acceptance Criteria

- [ ] Add new message types to protocol.py
- [ ] Implement handlers for all session operations
- [ ] LIST_SESSIONS returns paginated session summaries
- [ ] LOAD_SESSION returns full session data
- [ ] EXPORT_SESSION returns formatted content
- [ ] DELETE_SESSION removes session with confirmation
- [ ] Error handling for invalid session IDs

## Technical Details

### Protocol Extensions

```python
# sidecar/src/protocol.py

class MessageType(Enum):
    # ... existing types
    
    # Session History
    LIST_SESSIONS = "LIST_SESSIONS"
    LOAD_SESSION = "LOAD_SESSION"
    EXPORT_SESSION = "EXPORT_SESSION"
    DELETE_SESSION = "DELETE_SESSION"
    
    # Responses
    SESSION_LIST = "SESSION_LIST"
    SESSION_DATA = "SESSION_DATA"
    SESSION_EXPORT = "SESSION_EXPORT"
    SESSION_DELETED = "SESSION_DELETED"
```

### Request/Response Formats

```python
# LIST_SESSIONS Request
{"type": "LIST_SESSIONS", "data": {"limit": 20, "offset": 0}}

# SESSION_LIST Response
{
    "type": "SESSION_LIST",
    "data": {
        "sessions": [
            {
                "id": "sess_abc123",
                "startedAt": 1704825600000,
                "endedAt": 1704829200000,
                "contextFiles": ["resume.pdf"],
                "transcriptionCount": 45,
                "answerCount": 12
            }
        ],
        "total": 15,
        "hasMore": false
    }
}

# LOAD_SESSION Request
{"type": "LOAD_SESSION", "data": {"sessionId": "sess_abc123"}}

# SESSION_DATA Response
{
    "type": "SESSION_DATA",
    "data": {
        "id": "sess_abc123",
        "startedAt": 1704825600000,
        "endedAt": 1704829200000,
        "contextFiles": ["resume.pdf"],
        "transcriptions": [...],
        "answers": [...]
    }
}

# EXPORT_SESSION Request
{"type": "EXPORT_SESSION", "data": {"sessionId": "sess_abc123", "format": "md"}}

# SESSION_EXPORT Response
{"type": "SESSION_EXPORT", "data": {"content": "# Interview Session\n...", "format": "md"}}

# DELETE_SESSION Request
{"type": "DELETE_SESSION", "data": {"sessionId": "sess_abc123"}}

# SESSION_DELETED Response
{"type": "SESSION_DELETED", "data": {"sessionId": "sess_abc123", "success": true}}
```

### Server Handlers

```python
# sidecar/src/server.py

async def _handle_list_sessions(self, websocket, message):
    data = message.data or {}
    limit = data.get("limit", 20)
    offset = data.get("offset", 0)
    
    sessions = self.session_store.list_sessions(limit=limit, offset=offset)
    
    response = Message(
        type=MessageType.SESSION_LIST,
        data={
            "sessions": [self._session_to_dict(s) for s in sessions],
            "total": len(sessions),
            "hasMore": len(sessions) == limit
        }
    )
    await websocket.send(response.to_json())
```

## Test Cases

1. **List empty**: List sessions on fresh install returns empty list
2. **List with data**: Create 3 sessions, list returns all 3
3. **Load session**: Load specific session, verify all data returned
4. **Load invalid**: Load non-existent session, returns error
5. **Export markdown**: Export session as markdown, verify format
6. **Export JSON**: Export session as JSON, verify valid JSON
7. **Delete session**: Delete session, verify removed from list

## Definition of Done

- [ ] All message types implemented
- [ ] Handlers registered in message router
- [ ] Error responses for invalid operations
- [ ] Integration tests for WebSocket flow
- [ ] Documentation of protocol in comments
