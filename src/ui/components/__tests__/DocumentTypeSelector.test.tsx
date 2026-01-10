import { render, screen, fireEvent } from '@testing-library/react';
import DocumentTypeSelector, { detectDocumentType, DOCUMENT_TYPES } from '../DocumentTypeSelector';
import { describe, it, expect, vi } from 'vitest';

describe('DocumentTypeSelector', () => {
  it('renders correctly with default type', () => {
    const handleChange = vi.fn();
    render(<DocumentTypeSelector value="custom" onChange={handleChange} />);
    
    // Check if the button shows the label
    expect(screen.getByText(DOCUMENT_TYPES.custom.label)).toBeInTheDocument();
    expect(screen.getByText(DOCUMENT_TYPES.custom.icon)).toBeInTheDocument();
  });

  it('renders all document types in dropdown', () => {
    const handleChange = vi.fn();
    render(<DocumentTypeSelector value="custom" onChange={handleChange} />);
    
    // Open dropdown
    const button = screen.getByRole('button', { name: DOCUMENT_TYPES.custom.label });
    fireEvent.click(button);
    
    // Check if all options are present
    Object.values(DOCUMENT_TYPES).forEach(type => {
      // Use getAllByText because the label is shown in the button (if selected) and the dropdown
      const elements = screen.getAllByText(type.label);
      expect(elements.length).toBeGreaterThan(0);
      expect(screen.getByText(type.description)).toBeInTheDocument();
    });
  });

  it('calls onChange when an option is selected', () => {
    const handleChange = vi.fn();
    render(<DocumentTypeSelector value="custom" onChange={handleChange} />);
    
    // Open dropdown
    const button = screen.getByRole('button', { name: DOCUMENT_TYPES.custom.label });
    fireEvent.click(button);
    
    // Select "Resume/CV"
    const resumeOption = screen.getByText(DOCUMENT_TYPES.resume.label);
    // Find the button wrapping the text to click it
    const optionButton = resumeOption.closest('button');
    expect(optionButton).toBeInTheDocument();
    fireEvent.click(optionButton!);
    
    expect(handleChange).toHaveBeenCalledWith('resume');
  });
});

describe('detectDocumentType', () => {
  it('detects resume from filename', () => {
    expect(detectDocumentType('my_resume.pdf')).toBe('resume');
    expect(detectDocumentType('CV_2024.docx')).toBe('resume');
  });

  it('detects job description from filename', () => {
    expect(detectDocumentType('job_description.txt')).toBe('job_description');
    expect(detectDocumentType('jd_senior_dev.pdf')).toBe('job_description');
  });

  it('detects company info from filename', () => {
    expect(detectDocumentType('company_about.pdf')).toBe('company_info');
    expect(detectDocumentType('about_google.docx')).toBe('company_info');
  });

  it('detects industry research from filename', () => {
    expect(detectDocumentType('market_research.pdf')).toBe('industry_research');
    expect(detectDocumentType('industry_analysis.txt')).toBe('industry_research');
  });

  it('detects sample Q&A from filename', () => {
    expect(detectDocumentType('sample_qa.pdf')).toBe('sample_qa');
    expect(detectDocumentType('interview_questions.docx')).toBe('sample_qa');
  });

  it('defaults to custom for unknown filenames', () => {
    expect(detectDocumentType('random_file.pdf')).toBe('custom');
    expect(detectDocumentType('notes.txt')).toBe('custom');
  });
});
