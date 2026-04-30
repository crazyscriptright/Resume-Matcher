import { AuthFormWrapper } from '@/components/auth/auth-form-wrapper';
import { Suspense } from 'react';

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-canvas" />}>
      <AuthFormWrapper
        mode="register"
        title="Create account"
        description="Create a new account with your email address and password."
        alternateHref="/login"
        alternateLabel="Sign in"
        alternatePrompt="Already have an account?"
      />
    </Suspense>
  );
}
