"use client";

import { getStoredAccessToken } from '@/lib/auth/session';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';

/**
 * Simple client-side guard: if no valid access token is stored and the
 * current path is not public (login/register/print), redirect to login.
 */
export default function RequireAuth(): null {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!pathname) return;

    const publicPrefixes = ['/login', '/register', '/print', '/public'];
    const isPublic = publicPrefixes.some((p) => pathname.startsWith(p));
    if (isPublic) return;

    const token = getStoredAccessToken();
    if (!token) {
      const redirect = encodeURIComponent(window.location.pathname + window.location.search);
      router.replace(`/login?redirect=${redirect}`);
    }
  }, [pathname, router]);

  return null;
}
