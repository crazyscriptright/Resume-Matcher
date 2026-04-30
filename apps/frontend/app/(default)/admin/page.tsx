'use client';

import { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { useAuthUser } from '@/lib/auth/use-auth-user';
import { fetchUsers, updateUserRole, type AdminUser } from '@/lib/api/admin';

import ArrowLeft from 'lucide-react/dist/esm/icons/arrow-left';
import Loader2 from 'lucide-react/dist/esm/icons/loader-2';
import Shield from 'lucide-react/dist/esm/icons/shield';
import ShieldCheck from 'lucide-react/dist/esm/icons/shield-check';
import User from 'lucide-react/dist/esm/icons/user';
import Crown from 'lucide-react/dist/esm/icons/crown';

const VALID_ROLES = ['user', 'premium', 'admin'] as const;

const ROLE_CONFIG: Record<string, { label: string; icon: typeof User; color: string; bg: string }> =
  {
    user: {
      label: 'User',
      icon: User,
      color: 'text-steel-grey',
      bg: 'bg-gray-100',
    },
    premium: {
      label: 'Premium',
      icon: Crown,
      color: 'text-amber-700',
      bg: 'bg-amber-50',
    },
    admin: {
      label: 'Admin',
      icon: ShieldCheck,
      color: 'text-blue-700',
      bg: 'bg-blue-50',
    },
  };

export default function AdminPage() {
  const router = useRouter();
  const currentUser = useAuthUser();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Redirect non-admin users
  useEffect(() => {
    if (currentUser && currentUser.role !== 'admin') {
      router.replace('/dashboard');
    }
  }, [currentUser, router]);

  const loadUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchUsers();
      setUsers(data);
    } catch (err) {
      console.error('Failed to load users:', err);
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser?.role === 'admin') {
      loadUsers();
    }
  }, [currentUser?.role, loadUsers]);

  const handleRoleChange = async (userId: string, newRole: string) => {
    if (updatingUserId) return;

    setUpdatingUserId(userId);
    setError(null);
    setSuccessMessage(null);

    try {
      const result = await updateUserRole(userId, newRole);
      // Update local state
      setUsers((prev) =>
        prev.map((u) => (u.user_id === userId ? { ...u, role: newRole } : u))
      );
      setSuccessMessage(result.message);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      console.error('Failed to update role:', err);
      setError(err instanceof Error ? err.message : 'Failed to update role');
    } finally {
      setUpdatingUserId(null);
    }
  };

  const formatDate = (value: string) => {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!currentUser || currentUser.role !== 'admin') {
    return null;
  }

  return (
    <div className="min-h-screen w-full bg-[#F6F5EE] flex flex-col items-center p-4 md:p-8 font-sans">
      <div className="w-full max-w-5xl bg-white border border-black shadow-sw-lg p-8 md:p-12 relative">
        {/* Header */}
        <Button
          variant="link"
          className="absolute top-4 left-4"
          onClick={() => router.back()}
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Button>

        <div className="mb-8 mt-4 text-center">
          <div className="flex items-center justify-center gap-3 mb-2">
            <Shield className="w-8 h-8 text-blue-700" />
            <h1 className="font-serif text-4xl font-bold uppercase tracking-tight">
              Admin Panel
            </h1>
          </div>
          <p className="font-mono text-sm text-blue-700 font-bold uppercase">
            {'// '}User Management
          </p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 p-3 bg-green-50 border border-green-200 text-green-700 text-sm font-mono flex items-center gap-2">
            <ShieldCheck className="w-4 h-4" />
            {successMessage}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 p-3 bg-red-50 border border-red-200 text-red-700 text-sm font-mono flex items-center gap-2">
            <span>!</span> {error}
          </div>
        )}

        {/* Loading */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 animate-spin text-blue-700" />
            <span className="ml-3 font-mono text-sm uppercase text-steel-grey">
              Loading users...
            </span>
          </div>
        ) : (
          /* User Table */
          <div className="border border-black overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-[2fr_1fr_1.5fr_1fr] bg-black text-white font-mono text-xs uppercase tracking-wider">
              <div className="p-3 border-r border-gray-700">Email</div>
              <div className="p-3 border-r border-gray-700">Current Role</div>
              <div className="p-3 border-r border-gray-700">Registered</div>
              <div className="p-3">Change Role</div>
            </div>

            {/* Table Rows */}
            {users.length === 0 ? (
              <div className="p-8 text-center font-mono text-sm text-steel-grey">
                No users found.
              </div>
            ) : (
              users.map((user) => {
                const roleInfo = ROLE_CONFIG[user.role] || ROLE_CONFIG.user;
                const RoleIcon = roleInfo.icon;
                const isSelf = user.user_id === currentUser.user_id;
                const isUpdating = updatingUserId === user.user_id;

                return (
                  <div
                    key={user.user_id}
                    className={`grid grid-cols-[2fr_1fr_1.5fr_1fr] border-t border-black items-center ${
                      isSelf ? 'bg-blue-50/50' : 'bg-white hover:bg-gray-50'
                    } transition-colors`}
                  >
                    {/* Email */}
                    <div className="p-3 border-r border-gray-200 font-mono text-sm truncate flex items-center gap-2">
                      <span className="truncate">{user.email}</span>
                      {isSelf && (
                        <span className="shrink-0 text-[10px] font-bold text-blue-700 border border-blue-300 px-1.5 py-0.5 uppercase">
                          You
                        </span>
                      )}
                    </div>

                    {/* Role Badge */}
                    <div className="p-3 border-r border-gray-200">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-1 text-xs font-mono font-bold uppercase ${roleInfo.bg} ${roleInfo.color} border border-current/20`}
                      >
                        <RoleIcon className="w-3 h-3" />
                        {roleInfo.label}
                      </span>
                    </div>

                    {/* Date */}
                    <div className="p-3 border-r border-gray-200 font-mono text-xs text-steel-grey">
                      {formatDate(user.created_at)}
                    </div>

                    {/* Role Selector */}
                    <div className="p-3">
                      {isSelf ? (
                        <span className="font-mono text-xs text-steel-grey italic">
                          Protected
                        </span>
                      ) : (
                        <div className="relative">
                          {isUpdating && (
                            <div className="absolute inset-0 flex items-center justify-center bg-white/80 z-10">
                              <Loader2 className="w-4 h-4 animate-spin text-blue-700" />
                            </div>
                          )}
                          <select
                            value={user.role}
                            onChange={(e) =>
                              handleRoleChange(user.user_id, e.target.value)
                            }
                            disabled={isUpdating}
                            className="w-full font-mono text-xs border border-black bg-white px-2 py-1.5 uppercase cursor-pointer hover:bg-gray-50 focus:ring-1 focus:ring-blue-700 focus:outline-none rounded-none appearance-none"
                          >
                            {VALID_ROLES.map((r) => (
                              <option key={r} value={r}>
                                {ROLE_CONFIG[r]?.label || r}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Footer Stats */}
        {!isLoading && users.length > 0 && (
          <div className="mt-4 flex justify-between items-center font-mono text-xs text-steel-grey uppercase">
            <span>
              {users.length} user{users.length !== 1 ? 's' : ''} total
            </span>
            <div className="flex gap-4">
              {(['admin', 'premium', 'user'] as const).map((role) => {
                const count = users.filter((u) => u.role === role).length;
                const info = ROLE_CONFIG[role];
                return (
                  <span key={role} className={info.color}>
                    {count} {info.label}
                  </span>
                );
              })}
            </div>
          </div>
        )}

        {/* Refresh Button */}
        {!isLoading && (
          <div className="mt-6 flex justify-center">
            <Button
              variant="outline"
              size="sm"
              onClick={loadUsers}
              className="font-mono text-xs uppercase border-black rounded-none"
            >
              Refresh Users
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
