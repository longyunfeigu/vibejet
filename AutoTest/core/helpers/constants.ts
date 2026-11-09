// Global test constants — import from here, never hardcode in test files

export const TEST_PREFIX = 'e2e';

// The frontend keeps the signed-in session (access + refresh token) in localStorage
// under this key (frontend/src/lib/authStore.ts).
export const SESSION_STORAGE_KEY = 'vibejet.session';

export const TIMEOUTS = {
  page_load: 30_000,
  api_response: 10_000,
  document_processing: 180_000,   // 3 min: KB file indexing
} as const;

export const POLL_INTERVALS = {
  fast: 3_000,
  normal: 5_000,
  slow: 10_000,
  very_slow: 15_000,
} as const;
