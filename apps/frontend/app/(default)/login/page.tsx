import { AuthForm } from '@/components/auth/auth-form';

export default function LoginPage() {
  return (
    <AuthForm
      mode="login"
      title="Sign in"
      description="Sign in to access your resumes, tailoring tools, and settings."
      alternateHref="/register"
      alternateLabel="Create an account"
      alternatePrompt="Need an account?"
    />
  );
}
