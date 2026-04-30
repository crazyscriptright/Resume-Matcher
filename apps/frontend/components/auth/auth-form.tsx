'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiPost } from '@/lib/api/client';
import {
    clearAuthSession,
    getStoredAuthSession,
    storeAuthSession,
    type AuthSession,
} from '@/lib/auth/session';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

type AuthMode = 'login' | 'register';

type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    user_id: string;
    email: string;
    role: string;
  };
};

interface AuthFormProps {
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

async function submitAuth(mode: AuthMode, email: string, password: string): Promise<AuthSession> {
  const endpoint = mode === 'login' ? '/auth/login' : '/auth/register';
  const response = await apiPost(endpoint, { email, password });
  const responseText = await response.text();
  let payload: AuthResponse | { detail?: string } | null = null;

  if (responseText) {
    try {
      payload = JSON.parse(responseText) as AuthResponse | { detail?: string };
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const message =
      payload && typeof payload === 'object' && 'detail' in payload && payload.detail
        ? payload.detail
        : responseText || 'Auth failed';
    throw new Error(message);
  }

  if (!payload || typeof payload !== 'object' || !('access_token' in payload)) {
    throw new Error('Invalid auth response.');
  }

  return {
    accessToken: payload.access_token,
    expiresAt: Date.now() + payload.expires_in * 1000,
    user: payload.user,
  };
}

export function AuthForm({
  mode,
  title,
  description,
  alternateHref,
  alternateLabel,
  alternatePrompt,
  redirectTo,
}: AuthFormProps & { redirectTo?: string }) {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const finalRedirectTo = redirectTo || normalizeRedirectTarget(null);

  useEffect(() => {
    const session = getStoredAuthSession();
    if (session) {
      router.replace(finalRedirectTo);
      return;
    }

    clearAuthSession();
    setIsReady(true);
  }, [finalRedirectTo, router]);

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    void (async () => {
      try {
        const session = await submitAuth(mode, email.trim().toLowerCase(), password);
        storeAuthSession(session);
        // Notify status cache to refresh with the new auth token
        window.dispatchEvent(new Event('system-status-change'));
        router.replace(finalRedirectTo);
      } catch (submissionError) {
        setError(
          submissionError instanceof Error ? submissionError.message : 'Authentication failed.'
        );
        setIsSubmitting(false);
      }
    })();
  };

  if (!isReady) {
    return null;
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-canvas">
      {/* Grid Background */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(29,78,216,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(29,78,216,0.08)_1px,transparent_1px)] bg-[size:32px_32px]" />

      {/* Decorative Blur Elements */}
      <div className="absolute left-[-10rem] top-[-10rem] h-80 w-80 rounded-full bg-blue-700/8 blur-3xl" />
      <div className="absolute bottom-[-8rem] right-[-6rem] h-72 w-72 rounded-full bg-amber-400/12 blur-3xl" />
      <div className="absolute top-1/3 right-1/4 h-48 w-48 rounded-full bg-blue-700/5 blur-2xl" />

      {/* Decorative Border Frame - Top Left */}
      <div className="absolute top-4 left-4 h-24 w-24 border border-blue-700/20 md:border-blue-700/30 pointer-events-none" />

      {/* Decorative Border Frame - Bottom Right */}
      <div className="absolute bottom-4 right-4 h-32 w-32 border border-blue-700/20 md:border-blue-700/30 pointer-events-none" />

      <main className="relative mx-auto grid min-h-screen max-w-7xl items-center px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
        <section className="mb-8 lg:mb-0 lg:pr-12">
          <div className="inline-flex items-center border border-black bg-paper px-3 py-1 font-mono text-xs uppercase tracking-[0.3em] shadow-sw-sm">
            Resume Matcher / {mode}
          </div>
          <h1 className="mt-6 max-w-3xl font-serif text-4xl leading-none tracking-tight text-ink sm:text-6xl lg:text-7xl">
            Tailor resumes with a single sign-in.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-steel-grey sm:text-lg">
            {description} Role assignment stays server-side only. No dropdowns, no admin toggle, no
            OTP.
          </p>

          {/* <div className="mt-10 grid max-w-2xl gap-3 sm:grid-cols-3">
            {[
              'Email + password only',
              'Admin role is server-managed',
              'JWT session stored locally',
            ].map((item) => (
              <div
                key={item}
                className="border border-black bg-paper px-4 py-3 text-sm shadow-sw-sm"
              >
                {item}
              </div>
            ))}
          </div> */}
        </section>

        <section className="lg:pl-8">
          <Card className="border-2 border-black shadow-sw-default">
            <CardHeader>
              <CardTitle className="text-3xl">{title}</CardTitle>
              <CardDescription>{alternatePrompt}</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-5" onSubmit={handleSubmit}>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    maxLength={128}
                    required
                  />
                </div>

                {error ? (
                  <div className="border border-black bg-red-50 px-4 py-3 font-mono text-sm text-red-700">
                    {error}
                  </div>
                ) : null}

                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting ? 'Working...' : title}
                </Button>

                <p className="font-mono text-sm text-steel-grey">
                  {alternatePrompt}{' '}
                  <Link
                    href={alternateHref}
                    className="text-blue-700 underline-offset-4 hover:underline"
                  >
                    {alternateLabel}
                  </Link>
                </p>
              </form>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
