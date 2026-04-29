'use client';

import { useTranslations } from '@/lib/i18n';
import Link from 'next/link';

export default function Hero() {
  const { t } = useTranslations();

  const buttonClass =
    'group relative border border-black bg-transparent px-8 py-3 font-mono text-sm font-bold uppercase text-blue-700 transition-[transform,box-shadow,background-color,color] duration-150 ease-out hover:bg-blue-700 hover:text-background hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-sw-default active:translate-x-0 active:translate-y-0 active:shadow-none cursor-pointer';
  const linkPillClass =
    'inline-flex items-center gap-2 border border-black bg-background px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.18em] text-black transition-transform duration-150 hover:-translate-y-[1px] hover:shadow-sw-sm';

  return (
    <section
      className="relative h-screen w-full overflow-hidden bg-background p-4 md:p-12 lg:p-24"
      style={{
        backgroundImage:
          'linear-gradient(rgba(29, 78, 216, 0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(29, 78, 216, 0.1) 1px, transparent 1px)',
        backgroundSize: '40px 40px',
      }}
    >
      <div className="pointer-events-none absolute left-[-6rem] top-[-6rem] h-64 w-64 rounded-full border border-black bg-blue-200/30 shadow-sw-sm" />
      <div className="pointer-events-none absolute right-[-4rem] top-[15%] h-40 w-40 rounded-full border border-black bg-orange-100/50 shadow-sw-sm" />
      <div className="pointer-events-none absolute bottom-[-5rem] left-[18%] h-56 w-56 rotate-12 border border-black bg-green-100/40 shadow-sw-sm" />

      <div className="flex h-full w-full flex-col items-center justify-center border border-black text-blue-700 bg-background shadow-sw-xl">
        <div className="mb-6 border border-black bg-blue-700 px-4 py-2 font-mono text-xs font-bold uppercase tracking-[0.3em] text-white shadow-sw-sm">
          Open source resume tailoring
        </div>

        <h1 className="mb-12 text-center font-mono text-6xl font-bold uppercase leading-none tracking-tighter md:text-8xl lg:text-9xl selection:bg-blue-700 selection:text-white">
          {t('home.brandLine1')}
          <br />
          {t('home.brandLine2')}
        </h1>

        <div className="flex flex-col gap-4 md:flex-row md:gap-12">
          <a
            href="https://github.com/srbhr/Resume-Matcher"
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClass}
          >
            GitHub
          </a>
          <a
            href="https://resumematcher.fyi"
            target="_blank"
            rel="noopener noreferrer"
            className={buttonClass}
          >
            {t('home.docs')}
          </a>
          <Link href="/dashboard" className={buttonClass}>
            {t('home.launchApp')}
          </Link>
        </div>
      </div>
    </section>
  );
}
