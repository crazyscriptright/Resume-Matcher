'use client';

import { clearAuthSession } from '@/lib/auth/session';
import { useAuthUser } from '@/lib/auth/use-auth-user';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

export default function Header() {
  const router = useRouter();
  const user = useAuthUser();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Listen for global unauthorized events dispatched by `apiFetch` and
  // perform a client-side navigation (router.push) to avoid a full reload.
  useEffect(() => {
    function onUnauthorized(e: Event) {
      const detail = (e as CustomEvent)?.detail as { redirect?: string } | undefined;
      const target = detail?.redirect ?? '/login';
      // ensure we clear local session first
      try {
        clearAuthSession();
      } catch {}
      router.replace(target);
    }

    window.addEventListener('unauthorized', onUnauthorized as EventListener);
    return () => window.removeEventListener('unauthorized', onUnauthorized as EventListener);
  }, [router]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  const initials = (nameOrEmail?: string | null) => {
    if (!nameOrEmail) return '';
    const parts = nameOrEmail.split(/[@.\s]+/).filter(Boolean);
    return parts
      .slice(0, 2)
      .map((p) => p.charAt(0).toUpperCase())
      .join('');
  };

  const handleLogout = () => {
    clearAuthSession();
    setOpen(false);
    router.push('/login');
  };

  return (
    <div className="fixed top-4 right-4 z-50" ref={containerRef}>
      <div className="relative">
        {user && (
          <>
            <button
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label={user ? `Account menu for ${user.email}` : 'Account menu'}
              className="h-10 w-10 rounded-full border-2 border-black bg-white flex items-center justify-center font-mono font-bold text-sm"
            >
              {initials(user.email)}
            </button>

            {open && (
              <div className="mt-2 w-48 right-0 absolute z-50 border border-black bg-white shadow-sw-default rounded-none">
                <div className="p-3 border-b border-black">
                  <div className="font-bold text-sm">{user?.email ?? 'Guest'}</div>
                  <div className="text-xs text-steel-grey">{user?.role ?? 'visitor'}</div>
                </div>
                <div className="flex flex-col">
                  <Link
                    href="/settings"
                    className="px-3 py-2 text-sm hover:bg-paper-tint border-b border-black"
                  >
                    Settings
                  </Link>
                  {user?.role === 'admin' && (
                    <Link
                      href="/admin"
                      className="px-3 py-2 text-sm hover:bg-paper-tint border-b border-black"
                    >
                      Admin Dashboard
                    </Link>
                  )}
                  <button
                    onClick={handleLogout}
                    className="text-left px-3 py-2 text-sm hover:bg-paper-tint"
                  >
                    Logout
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
