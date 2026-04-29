import RequireAuth from '@/components/auth/require-auth';
import { LocalizedErrorBoundary } from '@/components/common/error-boundary';
import { ResumePreviewProvider } from '@/components/common/resume_previewer_context';
import { LanguageProvider } from '@/lib/context/language-context';
import { StatusCacheProvider } from '@/lib/context/status-cache';

export default function DefaultLayout({ children }: { children: React.ReactNode }) {
  return (
    <StatusCacheProvider>
      <LanguageProvider>
        <ResumePreviewProvider>
          <LocalizedErrorBoundary>
            <RequireAuth />
            <main className="min-h-screen flex flex-col">{children}</main>
          </LocalizedErrorBoundary>
        </ResumePreviewProvider>
      </LanguageProvider>
    </StatusCacheProvider>
  );
}
