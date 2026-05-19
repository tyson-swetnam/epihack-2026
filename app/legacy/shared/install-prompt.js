// shared/install-prompt.js
// Handle the `beforeinstallprompt` event and surface a small "Install"
// button on pages that opt in. Chromium-only (the event simply doesn't
// fire in Safari/Firefox); on those browsers we leave the install button
// hidden and let the user use the OS-level "Add to Home Screen".
//
// Usage on a page:
//
//   import { mountInstallButton } from '../shared/install-prompt.js';
//   mountInstallButton('#install-btn');
//
// The button must start with [hidden]; we un-hide it once the event fires.

let deferredPrompt = null;

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    // Stop the mini-infobar so we control where + when the button shows.
    e.preventDefault();
    deferredPrompt = e;
    // Tell any mounted buttons it's time to appear.
    window.dispatchEvent(new CustomEvent('sentinel:installable'));
  });
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null;
    window.dispatchEvent(new CustomEvent('sentinel:installed'));
  });
}

/**
 * Wire a DOM element (selector or node) to act as the install trigger.
 * The element starts hidden; it un-hides when the browser fires
 * `beforeinstallprompt` and hides again after the user accepts/dismisses.
 *
 * @param {string|Element} target
 */
export function mountInstallButton(target) {
  const btn = typeof target === 'string'
    ? document.querySelector(target)
    : target;
  if (!btn) return;

  // Default to hidden; reveal only when installable.
  btn.hidden = true;

  // If install fires before this mount runs, paint immediately.
  if (deferredPrompt) btn.hidden = false;

  window.addEventListener('sentinel:installable', () => { btn.hidden = false; });
  window.addEventListener('sentinel:installed',  () => { btn.hidden = true;  });

  // Hide if the app is already running standalone.
  const isStandalone =
    window.matchMedia && window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true; // iOS Safari
  if (isStandalone) btn.hidden = true;

  btn.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    btn.disabled = true;
    try {
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      // One-shot: the event can only be consumed once.
      deferredPrompt = null;
      btn.hidden = true;
      if (choice && choice.outcome === 'accepted') {
        console.info('[install] user accepted the install prompt');
      }
    } catch (e) {
      console.warn('[install] prompt failed:', e);
    } finally {
      btn.disabled = false;
    }
  });
}
