'use client';

/**
 * Replays any queued offline reports (plan/09 Phase D): once on mount and
 * whenever the browser fires `online`. Renders nothing. Uses createReportRaw
 * (the throwing variant) so a still-failing send is simply kept in the queue.
 */
import { useEffect } from 'react';

import { createReportRaw } from '@/lib/api-client';
import { flushQueue } from '@/lib/offline-queue';

export function OfflineFlusher() {
  useEffect(() => {
    const flush = () => {
      void flushQueue((payload) => createReportRaw(payload)).catch(() => {});
    };
    flush();
    window.addEventListener('online', flush);
    return () => window.removeEventListener('online', flush);
  }, []);

  return null;
}
