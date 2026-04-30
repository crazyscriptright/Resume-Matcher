'use client';

import { useSearchParams } from 'next/navigation';
import { AuthForm } from './auth-form';

type AuthMode = 'login' | 'register';

interface AuthFormWrapperProps {
  mode: AuthMode;
  title: string;
  description: string;
  alternateHref: string;
  alternateLabel: string;
  alternatePrompt: string;
}

function normalizeRedirectTarget(value: string | null): string {
  if (!value || !value.startsWith('/')) {
    return '/dashboard';
  }

  return value;
}

export function AuthFormWrapper(props: AuthFormWrapperProps) {
  const searchParams = useSearchParams();
  const redirectTo = normalizeRedirectTarget(searchParams.get('redirect'));

  return <AuthForm {...props} redirectTo={redirectTo} />;
}
