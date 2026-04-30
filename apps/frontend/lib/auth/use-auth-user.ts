'use client';

import { useEffect, useState } from 'react';
import { getStoredAuthUser, type AuthUser } from '@/lib/auth/session';

/**
 * Reactive hook that returns the current authenticated user.
 *
 * Listens for the custom `auth-change` event (dispatched by
 * `storeAuthSession` / `clearAuthSession`) and the native `storage`
 * event (for cross-tab sync) so the UI updates instantly on
 * login/logout without requiring a hard refresh.
 */
export function useAuthUser(): AuthUser | null {
  const [user, setUser] = useState<AuthUser | null>(() => getStoredAuthUser());

  useEffect(() => {
    const sync = () => setUser(getStoredAuthUser());

    // Re-read on mount in case the value changed between SSR and hydration
    sync();

    window.addEventListener('auth-change', sync);
    window.addEventListener('storage', sync);

    return () => {
      window.removeEventListener('auth-change', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  return user;
}
