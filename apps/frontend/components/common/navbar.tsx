'use client';

import { useAuth } from '@/lib/context/auth-context';
import { useRouter } from 'next/navigation';

export function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    router.push('/auth');
  };

  return (
    <nav className="border-b border-black bg-white p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <h1 className="font-serif text-lg font-bold text-black">Resume Matcher</h1>
        <div className="flex items-center gap-4">
          <span className="font-mono text-sm text-gray-600">{user.email}</span>
          <button
            onClick={handleLogout}
            className="px-4 py-2 border border-black bg-transparent hover:bg-black hover:text-white font-sans text-sm font-medium transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
