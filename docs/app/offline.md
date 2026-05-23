# Offline retry queue

!!! note "Stub"
    Authored in Phase 3. Source: `app/src/lib/offline-queue.ts`.

In-flight reports are queued in `localStorage` if the network is
unreachable; the client retries with exponential back-off when the next
`online` event fires. Photos are re-uploaded blob-first; their digest is
already part of the report payload, so retries are idempotent server-side.
