/**
 * Centralized environment configuration
 * Single source of truth for API URLs and environment variables
 */

const DEFAULT_PUBLIC_API_URL = '/';

/**
 * Normalize API URL from environment
 */
function normalizeApiUrl(value: string): string {
  if (!value) return DEFAULT_PUBLIC_API_URL;
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

/**
 * Convert API URL to API base (with /api/v1 suffix)
 * If API_URL is '/', uses relative path (proxied by Next.js rewrites)
 * Otherwise uses absolute URL to backend
 */
function toApiBase(apiUrl: string): string {
  if (apiUrl === '/' || apiUrl === '') {
    return '/api/v1';
  }
  return `${apiUrl}/api/v1`;
}

/**
 * Resolve runtime API base
 * For browser: reads from window.__NEXT_DATA__ (populated at build time)
 * For server: uses env var directly
 */
function resolveRuntimeApiBase(apiBase: string): string {
  if (typeof window !== 'undefined') {
    return apiBase;
  }
  return apiBase;
}

// ============================================================================
// Exported Environment Configuration
// ============================================================================

/** Raw API URL from NEXT_PUBLIC_API_URL env var */
export const API_URL = normalizeApiUrl(
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_PUBLIC_API_URL
);

/** Full API base URL with /api/v1 suffix */
export const API_BASE = resolveRuntimeApiBase(toApiBase(API_URL));

/**
 * Get API URL for auth and other direct fetch calls
 * Use this in client components that make direct fetch() calls
 * Example: fetch(`${getAuthApiBase()}/auth/login`, ...)
 */
export const getAuthApiBase = () => API_BASE;

/**
 * Get API URL for context/hooks
 * Use this in React contexts and custom hooks
 */
export const getApiUrl = () => API_URL;
