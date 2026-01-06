---
name: documentation
description: Use this when the user mentions "write docs", "update documentation", or "create README". Generates technical documentation, API refs, and user guides.
allowed-tools: "Read,Write,Glob,Grep"
version: "1.0.0"
---

# Documentation - Technical Writing Workflow

Guides creation of clear documentation for humans and AI agents.

## Overview

This skill:
- Creates appropriate documentation type
- Follows consistent templates
- Validates accuracy
- Writes for both humans and AI

## Documentation Types

### Technical Documentation
- API documentation
- Architecture docs
- Configuration references

### User Documentation
- READMEs
- Getting started guides
- Troubleshooting guides

### LLM-Friendly Documentation
- CLAUDE.md files
- Structured formats for AI parsing

## Instructions

### Step 1: Identify Scope

- What needs documenting?
- Who is the audience?
- What format is appropriate?

### Step 2: Gather Information

- Read relevant code
- Understand functionality
- Test any examples

### Step 3: Create Documentation

Use appropriate template below.

### Step 4: Validate

- Verify accuracy
- Test code examples (run them!)
- Check links

## Templates

### README Template

```markdown
# [Project Name]

[One-line description of what this does]

## Quick Start

```bash
# Fastest path to working example
npm install
npm start
```

## Installation

[Detailed setup steps]

## Usage

[Common use cases with code examples]

## API Reference

[Key functions/methods]

## Configuration

[Options and environment variables]

## Contributing

[How to contribute]

## License

[License type]
```

### API Documentation Template

```markdown
## [Endpoint/Method Name]

[Description of what it does]

### Request

- **Method**: GET/POST/PUT/DELETE
- **Path**: `/api/resource/:id`
- **Headers**: 
  - `Authorization`: Bearer token (required)
  - `Content-Type`: application/json

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | Resource identifier |
| limit | number | No | Max results (default: 10) |

### Request Body

```json
{
  "name": "Example",
  "active": true
}
```

### Response

**Success (200)**:
```json
{
  "id": "abc123",
  "name": "Example",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

**Error (400)**:
```json
{
  "error": "validation_error",
  "message": "Name is required"
}
```

### Errors

| Code | Description |
|------|-------------|
| 400 | Bad request - invalid input |
| 401 | Unauthorized - missing/invalid token |
| 404 | Not found - resource doesn't exist |
| 500 | Server error - internal failure |
```

### CLAUDE.md Template

```markdown
# [Project Name]

## Quick Reference

**Commands:**
- `/command-1` - Description
- `/command-2` - Description

**Key Files:**
- `path/to/important.ts` - What it does

## Workflow

[How to use this project]

## Conventions

[Code style, patterns to follow]

## Don't Do This

- ❌ [Anti-pattern 1]
- ❌ [Anti-pattern 2]

## Testing

[How to run tests]
```

## Output

- Documentation file(s) at appropriate location
- Verified code examples
- Working links

## Quality Checklist

- [ ] Clear headings and organization
- [ ] Working code examples (tested!)
- [ ] Accurate and up-to-date
- [ ] Appropriate detail for audience
- [ ] Both happy path and error cases
- [ ] Links verified
