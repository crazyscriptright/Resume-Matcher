import { AuthFormWrapper } from '@/components/auth/auth-form-wrapper';
import { Suspense } from 'react';

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-canvas" />}>
      <AuthFormWrapper
        mode="login"
        title="Sign in"
        description="Sign in to access your resumes, tailoring tools, and settings."
        alternateHref="/register"
        alternateLabel="Create an account"
        alternatePrompt="Need an account?"
      />
    </Suspense>
  );
}
