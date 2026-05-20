import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

import { AuthProvider } from '@/components/AuthProvider';
import { AppShell } from '@/components/AppShell';

// Inter exposed as a CSS variable so Tailwind's `font-sans` token
// (tailwind.config.ts → var(--font-inter)) picks it up.
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'AZ One Health Sentinel',
  description:
    'Anonymous One Health reporting — humans, animals, environment. No login. EXIF GPS stripped from photos by default. Locations coarsened to ZIP / 1 km before any public surface.',
  applicationName: 'AZ One Health Sentinel',
  authors: [{ name: 'EpiHack Arizona 2026' }],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
  themeColor: '#00796b',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // The phone-frame AppShell is in the layout so every screen is framed
  // identically; each page renders its own <AppTopBar/> as its first child
  // (so back-buttons / titles vary per screen, matching the reference).
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans antialiased">
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
