import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useVADFilter } from './useVADFilter';
import { useMicVAD } from '@ricky0123/vad-react';

// Mock useMicVAD
vi.mock('@ricky0123/vad-react', () => ({
  useMicVAD: vi.fn(),
  utils: {},
}));

describe('useVADFilter', () => {
  const mockStart = vi.fn();
  const mockPause = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (useMicVAD as any).mockReturnValue({
      start: mockStart,
      pause: mockPause,
      listening: false,
      userSpeaking: false,
      errored: false,
      loading: false,
    });
  });

  it('should initialize with default values', () => {
    const { result } = renderHook(() => useVADFilter({}));

    expect(result.current.listening).toBe(false);
    expect(result.current.userSpeaking).toBe(false);
    expect(result.current.errored).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it('should call useMicVAD with correct local asset paths', () => {
    renderHook(() => useVADFilter({}));

    expect(useMicVAD).toHaveBeenCalledWith(expect.objectContaining({
      baseAssetPath: '/assets/vad/',
      onnxWASMBasePath: '/assets/vad/',
    }));
  });

  it('should expose start and pause methods', () => {
    const { result } = renderHook(() => useVADFilter({}));

    result.current.start();
    expect(mockStart).toHaveBeenCalled();

    result.current.pause();
    expect(mockPause).toHaveBeenCalled();
  });

  it('should handle errors', () => {
    (useMicVAD as any).mockReturnValue({
      start: mockStart,
      pause: mockPause,
      listening: false,
      userSpeaking: false,
      errored: 'Some error', // vad-react returns string on error
      loading: false,
    });

    const { result } = renderHook(() => useVADFilter({}));

    expect(result.current.errored).toBe(true); // Wrapper converts to boolean
  });
});
