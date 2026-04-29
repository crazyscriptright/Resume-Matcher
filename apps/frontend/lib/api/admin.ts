/**
 * Admin API client — user management endpoints.
 */

import { apiFetch } from './client';

export interface AdminUser {
  user_id: string;
  email: string;
  role: string;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  users: AdminUser[];
}

export interface UpdateRoleResponse {
  message: string;
  user: AdminUser;
}

/** Fetch all users (admin only). */
export async function fetchUsers(): Promise<AdminUser[]> {
  const res = await apiFetch('/admin/users', { credentials: 'include' });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to fetch users (status ${res.status}).`);
  }

  const body: UserListResponse = await res.json();
  return body.users;
}

/** Update a user's role (admin only). */
export async function updateUserRole(
  userId: string,
  role: string
): Promise<UpdateRoleResponse> {
  const res = await apiFetch(`/admin/users/${userId}/role`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ role }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Failed to update role (status ${res.status}).`);
  }

  return res.json();
}
