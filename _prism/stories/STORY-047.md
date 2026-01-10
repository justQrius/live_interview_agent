# STORY-047: Pre-Interview Preparation

**Phase**: 3B (Enhanced Context)
**Priority**: P2 - Should Have
**Effort**: 1 day
**Dependencies**: STORY-045

## Description

Implement pre-interview preparation feature that synthesizes all uploaded documents into a briefing summary. This helps the LLM "prepare" before the interview starts.

## Acceptance Criteria

- [ ] Add "Prepare for Interview" button to UI
- [ ] Call LLM to generate preparation summary
- [ ] Summary includes key talking points, potential weaknesses, company insights
- [ ] Store preparation summary for session use
- [ ] Display preparation summary in UI
- [ ] Add PREPARE_INTERVIEW WebSocket message type

## Technical Details

### Backend Preparation Logic

```python
# sidecar/src/context/enhanced_manager.py

async def prepare_for_interview(self) -> str:
    """
    Generate pre-interview preparation summary.
    
    Returns:
        Preparation briefing text
    """
    if not self.documents_by_type:
        return "No documents uploaded. Upload your resume and job description for personalized preparation."
    
    prep_prompt = self._build_preparation_prompt()
    
    # Use LLM to generate preparation summary
    summary = await self.llm.generate_preparation(prep_prompt)
    
    self.preparation_summary = summary
    return summary

def _build_preparation_prompt(self) -> str:
    """Build prompt for preparation generation."""
    sections = []
    
    if DocumentType.RESUME in self.documents_by_type:
        resume_text = self._get_document_summary(DocumentType.RESUME)
        sections.append(f"## CANDIDATE BACKGROUND\n{resume_text}")
    
    if DocumentType.JOB_DESCRIPTION in self.documents_by_type:
        jd_text = self._get_document_summary(DocumentType.JOB_DESCRIPTION)
        sections.append(f"## ROLE REQUIREMENTS\n{jd_text}")
    
    if DocumentType.COMPANY_INFO in self.documents_by_type:
        company_text = self._get_document_summary(DocumentType.COMPANY_INFO)
        sections.append(f"## COMPANY CONTEXT\n{company_text}")
    
    return f"""Based on the following documents, prepare a comprehensive interview briefing:

{chr(10).join(sections)}

Generate:
1. **Key Talking Points**: 3-5 points that align the candidate's experience with role requirements
2. **Potential Challenges**: 2-3 areas where the candidate may need to address gaps
3. **Company-Specific Insights**: 2-3 talking points that reference company values/products
4. **STAR Story Suggestions**: 2-3 specific experiences from the resume that could be used for behavioral questions
5. **Questions to Ask**: 2-3 intelligent questions the candidate could ask

Keep the briefing concise and actionable. Use bullet points.
"""
```

### WebSocket Protocol

```python
# Request
{"type": "PREPARE_INTERVIEW", "data": {}}

# Response
{
    "type": "PREPARATION_READY", 
    "data": {
        "summary": "## Interview Preparation Briefing\n\n### Key Talking Points\n..."
    }
}
```

## Test Cases

1. **Prepare with all docs**: Upload resume + JD + company, generate summary
2. **Prepare with resume only**: Generate summary with available info
3. **No documents**: Return helpful message about uploading docs
4. **Summary quality**: Verify summary contains expected sections
5. **UI display**: Summary renders properly with markdown

## Definition of Done

- [ ] Preparation logic implemented
- [ ] WebSocket handler added
- [ ] LLM integration working
- [ ] Unit tests passing
- [ ] Integration with frontend
