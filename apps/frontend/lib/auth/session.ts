export interface AuthUser {
  user_id: string;
  email: string;
  role: string;
}

export interface AuthSession {
  accessToken: string;
  expiresAt: number;
  user: AuthUser;
}

const AUTH_TOKEN_KEY = 'resume-matcher-auth-token';
const AUTH_USER_KEY = 'resume-matcher-auth-user';
const AUTH_EXPIRES_AT_KEY = 'resume-matcher-auth-expires-at';
const MASTER_RESUME_KEY_PREFIX = 'resume-matcher-master-resume-id';

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function getStoredAccessToken(): string | null {
  if (!isBrowser()) {
    return null;
  }

  const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) {
    return null;
  }

  const expiresAt = Number(window.localStorage.getItem(AUTH_EXPIRES_AT_KEY) ?? '0');
  if (expiresAt && Date.now() >= expiresAt) {
    clearAuthSession();
    return null;
  }

  return token;
}

export function getStoredAuthUser(): AuthUser | null {
  if (!isBrowser()) {
    return null;
  }

  const rawUser = window.localStorage.getItem(AUTH_USER_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    clearAuthSession();
    return null;
  }
}

export function getStoredAuthSession(): AuthSession | null {
  if (!isBrowser()) {
    return null;
  }

  const accessToken = getStoredAccessToken();
  const user = getStoredAuthUser();

  if (!accessToken || !user) {
    return null;
  }

  const expiresAt = Number(window.localStorage.getItem(AUTH_EXPIRES_AT_KEY) ?? '0');
  return { accessToken, user, expiresAt };
}

export function storeAuthSession(session: AuthSession): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(AUTH_TOKEN_KEY, session.accessToken);
  window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(session.user));
  window.localStorage.setItem(AUTH_EXPIRES_AT_KEY, String(session.expiresAt));
}

export function clearAuthSession(): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(AUTH_TOKEN_KEY);
  window.localStorage.removeItem(AUTH_USER_KEY);
  window.localStorage.removeItem(AUTH_EXPIRES_AT_KEY);
}

function getMasterResumeStorageKey(userId?: string | null): string {
  return userId ? `${MASTER_RESUME_KEY_PREFIX}:${userId}` : MASTER_RESUME_KEY_PREFIX;
}

export function getStoredMasterResumeId(userId?: string | null): string | null {
  if (!isBrowser()) {
    return null;
  }

  return window.localStorage.getItem(getMasterResumeStorageKey(userId));
}

export function storeMasterResumeId(resumeId: string, userId?: string | null): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(getMasterResumeStorageKey(userId), resumeId);
}

export function clearStoredMasterResumeId(userId?: string | null): void {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(getMasterResumeStorageKey(userId));
}
