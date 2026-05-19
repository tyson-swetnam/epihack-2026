import type { Metadata, Viewport } from 'next';
import './globals.css';

import { AuthProvider } from '@/components/AuthProvider';
import { AuthBadge } from '@/components/AuthBadge';

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
  themeColor: '#1F3A93',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <header className="app-header">
            <div className="crumbs">
              <a href="/epihack-2026/index.html">&laquo; EpiHack AZ 2026</a>
            </div>
            <div className="header-row">
              <h1>AZ One Health Sentinel</h1>
              <AuthBadge />
            </div>
          </header>
          <main className="container">{children}</main>
          <footer className="app-footer">
            Source: Ending Pandemics Academy · University of Arizona Mel &amp;
            Enid Zuckerman College of Public Health · Global Health Institute.
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
