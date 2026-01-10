import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PreparationButton } from '../PreparationButton';
import { useSessionStore } from '../../store/sessionStore';

const mockRequestPreparation = vi.fn();
vi.mock('../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    requestPreparation: mockRequestPreparation,
  }),
}));

describe('PreparationButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSessionStore.setState({
      preparationStatus: 'not_started',
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should render correct text when not started', () => {
    render(<PreparationButton />);
    expect(screen.getByRole('button')).toHaveTextContent('Prepare Interview');
    expect(screen.getByRole('button')).not.toBeDisabled();
  });

  it('should render loading state when preparing', () => {
    useSessionStore.setState({ preparationStatus: 'preparing' });
    render(<PreparationButton />);
    expect(screen.getByRole('button')).toHaveTextContent('Preparing...');
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it('should render ready state when ready', () => {
    useSessionStore.setState({ preparationStatus: 'ready' });
    render(<PreparationButton />);
    expect(screen.getByRole('button')).toHaveTextContent('Preparation Ready');
    expect(screen.getByRole('button')).not.toBeDisabled(); // Could be clicked again to re-generate
  });

  it('should render error state when error', () => {
    useSessionStore.setState({ preparationStatus: 'error' });
    render(<PreparationButton />);
    expect(screen.getByRole('button')).toHaveTextContent('Preparation Failed - Retry');
  });

  it('should call requestPreparation when clicked', async () => {
    const user = userEvent.setup();
    render(<PreparationButton />);
    
    await user.click(screen.getByRole('button'));
    
    expect(mockRequestPreparation).toHaveBeenCalled();
  });

  it('should not call requestPreparation when disabled', async () => {
    const user = userEvent.setup();
    render(<PreparationButton disabled={true} />);
    
    expect(screen.getByRole('button')).toBeDisabled();
    await user.click(screen.getByRole('button'));
    
    expect(mockRequestPreparation).not.toHaveBeenCalled();
  });

  it('should disable button when passed disabled prop', () => {
    render(<PreparationButton disabled={true} />);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
