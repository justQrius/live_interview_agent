# STORY-046: Document Type Selector UI

**Phase**: 3B (Enhanced Context)
**Priority**: P2 - Should Have
**Effort**: 0.5 days
**Dependencies**: STORY-042

## Description

Add a document type selector dropdown to the file upload UI. Users must specify the document type (resume, job_description, company_info, etc.) when uploading files.

## Acceptance Criteria

- [ ] Create `DocumentTypeSelector` dropdown component
- [ ] Integrate with existing `ContextLoader` component
- [ ] Show all 6 document types with descriptions
- [ ] Default to intelligent type detection based on filename
- [ ] Include document type in UPLOAD_CONTEXT message
- [ ] Visual indication of document types in file list

## Technical Details

### Component

```typescript
// src/ui/components/DocumentTypeSelector.tsx

type DocumentType = 'resume' | 'job_description' | 'company_info' | 
                    'industry_research' | 'sample_qa' | 'custom';

interface DocumentTypeSelectorProps {
  value: DocumentType;
  onChange: (type: DocumentType) => void;
  filename?: string;  // For auto-detection
}

const DOCUMENT_TYPES: Record<DocumentType, { label: string; description: string; icon: string }> = {
  resume: { 
    label: 'Resume/CV', 
    description: 'Your background and experience',
    icon: '📄'
  },
  job_description: { 
    label: 'Job Description', 
    description: 'Role requirements and responsibilities',
    icon: '📋'
  },
  company_info: { 
    label: 'Company Info', 
    description: 'About the company, culture, mission',
    icon: '🏢'
  },
  industry_research: { 
    label: 'Industry Research', 
    description: 'Market trends, competitors, insights',
    icon: '📊'
  },
  sample_qa: { 
    label: 'Sample Q&A', 
    description: 'Practice questions and answers',
    icon: '❓'
  },
  custom: { 
    label: 'Other', 
    description: 'Custom document type',
    icon: '📁'
  },
};
```

### Auto-Detection Logic

```typescript
function detectDocumentType(filename: string): DocumentType {
  const lower = filename.toLowerCase();
  
  if (lower.includes('resume') || lower.includes('cv')) {
    return 'resume';
  }
  if (lower.includes('job') || lower.includes('jd') || lower.includes('description')) {
    return 'job_description';
  }
  if (lower.includes('company') || lower.includes('about')) {
    return 'company_info';
  }
  if (lower.includes('research') || lower.includes('industry') || lower.includes('market')) {
    return 'industry_research';
  }
  if (lower.includes('qa') || lower.includes('question') || lower.includes('sample')) {
    return 'sample_qa';
  }
  
  return 'custom';
}
```

## Test Cases

1. **Manual selection**: Select each document type, verify correct value
2. **Auto-detection**: Upload "resume.pdf", verify auto-selects resume
3. **Override auto-detection**: Change auto-detected type, verify persists
4. **Upload message**: Verify document type included in WebSocket message
5. **File list display**: Verify document type icon/label shown

## Definition of Done

- [ ] Component implemented with styling
- [ ] Auto-detection working
- [ ] Integration with ContextLoader
- [ ] Unit tests passing
