import { AuthForm } from '@/components/auth/auth-form';

export default function RegisterPage() {
  return (
    <AuthForm
      mode="register"
      title="Create account"
      description="Create a new account with your email address and password."
      alternateHref="/login"
      alternateLabel="Sign in"
      alternatePrompt="Already have an account?"
    />
  );
}
