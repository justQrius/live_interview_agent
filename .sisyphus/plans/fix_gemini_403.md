# Fix Gemini 403 CachedContent Error

## Context
The application crashed with a `403 PERMISSION_DENIED` error from Gemini: `CachedContent not found (or permission denied)`.
This occurs when the client tries to use a Context Cache ID that has been deleted or expired on Google's servers, but the local `GeminiCacheManager` still believes it is valid.

## Problem Analysis
- **Location**: `sidecar/src/providers/llm/gemini.py`
- **Cause**: The `generate_response` method blindly uses `self._cached_content_name` if set.
- **Missing Logic**: No handling for specific cache-related errors (403/404).
- **Impact**: Immediate crash during generation if cache is invalid.

## Implementation Plan (Executed)
1.  **Modify `GeminiLLMProvider.generate_response`**:
    -   Wrap the prompt generation `_build_prompt` inside the retry loop.
    -   Add `try/except` block to catch `403` or `404` errors containing "CachedContent".
2.  **Add Fallback Logic**:
    -   If a cache error is detected:
        -   Log a warning.
        -   Set `self._cached_content_name = None` (clearing the bad cache ref).
        -   `continue` to the next retry iteration.
3.  **Result**:
    -   The next iteration calls `_build_prompt` again.
    -   Since `_cached_content_name` is `None`, it automatically inserts the full RAG context.
    -   Generation succeeds using standard RAG (graceful degradation).

## Verification
-   Created reproduction test `tests/test_gemini_cache_fallback.py`.
-   Verified it failed before fix (Crash).
-   Verified it passed after fix (Success with fallback).
-   Ran existing `tests/test_gemini_llm_provider.py` to ensure no regressions.

## Status
-   [x] Analysis
-   [x] Reproduction
-   [x] Fix Implementation
-   [x] Verification
