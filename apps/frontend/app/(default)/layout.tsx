import { ProtectedRoute } from '@/components/auth/protected-route';
import { LocalizedErrorBoundary } from '@/components/common/error-boundary';
import { Navbar } from '@/components/common/navbar';
import { ResumePreviewProvider } from '@/components/common/resume_previewer_context';
import { LanguageProvider } from '@/lib/context/language-context';
import { StatusCacheProvider } from '@/lib/context/status-cache';

export default function DefaultLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <StatusCacheProvider>
        <LanguageProvider>
          <ResumePreviewProvider>
            <LocalizedErrorBoundary>
              <Navbar />
              <main className="min-h-screen flex flex-col">{children}</main>
            </LocalizedErrorBoundary>
          </ResumePreviewProvider>
        </LanguageProvider>
      </StatusCacheProvider>
    </ProtectedRoute>
  );
}
