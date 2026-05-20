import Link from 'next/link';
import type { ReactNode } from 'react';
import { ArrowLeft, ShieldPlus } from 'lucide-react';

/**
 * Mobile phone-frame shell, ported from Elbaraaa/OneHealth
 * (plan/08-mobile-ux-revamp.md, Phase 1). A centered 390 px "screen"
 * on a dark dotted backdrop. `next/link` applies the app basePath
 * automatically, so hrefs stay relative ("/", "/report").
 */

interface AppShellProps {
  children: ReactNode;
  className?: string;
  flat?: boolean;
}

interface AppTopBarProps {
  title?: string;
  backHref?: string;
  /** Render the One Health brand on the left instead of a plain title. */
  brand?: boolean;
  /** Slot on the right of the bar (e.g. the auth chip). */
  right?: ReactNode;
}

export function AppShell({ children, className = '', flat }: AppShellProps) {
  return (
    <div className="phone-page">
      <div
        className={`phone-screen ${flat ? 'phone-screen-flat' : ''} ${className}`}
      >
        {children}
      </div>
    </div>
  );
}

export function AppTopBar({
  title = 'One Health Sentinel',
  backHref,
  brand,
  right,
}: AppTopBarProps) {
  return (
    <header className="relative flex h-11 items-center justify-center border-b border-slate-200 bg-white/80 px-4 text-public-teal">
      {backHref ? (
        <Link
          href={backHref}
          className="focus-ring absolute left-3 grid size-8 place-items-center rounded-md text-public-teal"
          aria-label="Go back"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
        </Link>
      ) : null}

      {brand ? (
        <Link
          href="/"
          className="focus-ring absolute left-3 inline-flex items-center gap-2 rounded-md text-xs font-extrabold text-public-teal"
        >
          <ShieldPlus className="size-4" aria-hidden="true" />
          One Health Sentinel
        </Link>
      ) : (
        <p className="text-xs font-medium">{title}</p>
      )}

      {right ? <span className="absolute right-3">{right}</span> : null}
    </header>
  );
}
