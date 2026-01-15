import React, { useState, useEffect, useRef } from 'react';

export type DocumentType = 
  | 'resume' 
  | 'job_description' 
  | 'company_info' 
  | 'industry_research' 
  | 'sample_qa' 
  | 'interviewer_info'
  | 'custom';

export const DOCUMENT_TYPES: Record<DocumentType, { label: string; description: string; icon: string }> = {
  resume: { label: 'Resume/CV', description: 'Your background and experience', icon: '📄' },
  job_description: { label: 'Job Description', description: 'Role requirements', icon: '📋' },
  company_info: { label: 'Company Info', description: 'About the company', icon: '🏢' },
  interviewer_info: { label: 'Interviewer Info', description: 'About the interviewer/hiring manager', icon: '👤' },
  industry_research: { label: 'Industry Research', description: 'Market insights', icon: '📊' },
  sample_qa: { label: 'Sample Q&A', description: 'Practice questions', icon: '❓' },
  custom: { label: 'Other', description: 'Custom document', icon: '📁' },
};

export const detectDocumentType = (filename: string): DocumentType => {
  const lowerName = filename.toLowerCase();
  
  // Check resume first (high priority)
  if (lowerName.includes('resume') || lowerName.includes('cv')) return 'resume';
  
  // Check interviewer info BEFORE company_info (more specific)
  if (lowerName.includes('interviewer') || lowerName.includes('hiring_manager') || 
      lowerName.includes('hiring manager') || lowerName.includes('recruiter')) return 'interviewer_info';
  
  // Job description
  if (lowerName.includes('job') || lowerName.includes('jd') || lowerName.includes('description')) return 'job_description';
  
  // Company info (check after interviewer to avoid false matches on "about")
  if (lowerName.includes('company') || (lowerName.includes('about') && !lowerName.includes('manager'))) return 'company_info';
  
  // Other categories
  if (lowerName.includes('research') || lowerName.includes('industry') || lowerName.includes('market')) return 'industry_research';
  if (lowerName.includes('qa') || lowerName.includes('question') || lowerName.includes('sample')) return 'sample_qa';
  
  return 'custom';
};

interface DocumentTypeSelectorProps {
  value: DocumentType;
  onChange: (type: DocumentType) => void;
  filename?: string;
}

const DocumentTypeSelector: React.FC<DocumentTypeSelectorProps> = ({ value, onChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const selectedType = DOCUMENT_TYPES[value] || DOCUMENT_TYPES.custom;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm bg-surface dark:bg-surface-elevated border border-border rounded-lg hover:bg-surface-elevated dark:hover:bg-surface hover:border-primary/30 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-primary/20 w-full md:w-auto min-w-[140px]"
        type="button"
      >
        <span className="text-lg leading-none" role="img" aria-hidden="true">
          {selectedType.icon}
        </span>
        <span className="text-text-primary font-medium truncate flex-1 text-left">
          {selectedType.label}
        </span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className={`h-4 w-4 text-text-muted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-1 w-64 bg-surface dark:bg-surface-elevated rounded-xl shadow-lg border border-border animate-in fade-in zoom-in-95 duration-100 origin-top-right">
          <div className="py-1 max-h-[300px] overflow-y-auto">
            {(Object.entries(DOCUMENT_TYPES) as [DocumentType, typeof DOCUMENT_TYPES[DocumentType]][]).map(([type, info]) => (
              <button
                key={type}
                onClick={() => {
                  onChange(type);
                  setIsOpen(false);
                }}
                className={`w-full text-left px-4 py-3 hover:bg-surface-elevated dark:hover:bg-surface transition-colors flex items-start gap-3 group ${
                  value === type ? 'bg-primary/5 dark:bg-primary/10' : ''
                }`}
              >
                <span className="text-xl mt-0.5" aria-hidden="true">{info.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className={`text-sm font-medium ${
                    value === type ? 'text-primary' : 'text-text-primary'
                  }`}>
                    {info.label}
                  </div>
                  <div className="text-xs text-text-muted truncate group-hover:text-text-secondary">
                    {info.description}
                  </div>
                </div>
                {value === type && (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-primary mt-1" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentTypeSelector;
