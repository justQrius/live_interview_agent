import '@testing-library/dom';
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// Runs cleanup after each test case
afterEach(() => {
  cleanup();
});
