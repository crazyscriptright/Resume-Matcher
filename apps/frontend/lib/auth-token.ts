/**
 * Auth token management - uses both localStorage and cookies
 *
 * - localStorage: For client-side access (React context, hooks)
 * - Cookie: For server-side access (Next.js server components, fetch credentials)
 */

const TOKEN_KEY = 'auth_token';

/**
 * Set auth token in both localStorage and as a cookie
 */
export function setAuthToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
  }

  // Set cookie for server-side and automatic credential inclusion
  if (typeof document !== 'undefined') {
    // Set as a regular cookie (will be sent with credentials: 'include')
    // Note: In production, set Secure and SameSite attributes
    document.cookie = `${TOKEN_KEY}=${encodeURIComponent(token)}; path=/; max-age=${24 * 60 * 60}`;
  }
}

/**
 * Get auth token from localStorage (client-side)
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Clear auth token from both localStorage and cookies
 */
export function clearAuthToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }

  if (typeof document !== 'undefined') {
    // Clear the cookie by setting max-age to 0
    document.cookie = `${TOKEN_KEY}=; path=/; max-age=0`;
  }
}
