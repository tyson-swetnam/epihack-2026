/* dashboard/shared/auth-stub.js
 *
 * Placeholder agency sign-in toggle. In production this is replaced
 * by federated agency SSO (ADHS Entra ID, MCDPH Active Directory,
 * AZGFD employee portal, Coconino HHS) plus the corresponding
 * data-use agreement (DUA) for each agency's view of the knowledge
 * graph. None of those exist yet; this stub keeps the demo navigable.
 *
 *   - Selecting an agency in the picker navigates the browser to the
 *     matching landing page (dashboard/<agency>/index.html).
 *   - The current agency is highlighted (matches body[data-agency]).
 *
 * The auth-stub deliberately writes to localStorage only (no cookies,
 * no network) so that running the demo in a private window leaves
 * no residue.
 */

const AGENCIES = [
  { slug: 'adhs',     label: 'ADHS — Vector-Borne & Zoonotic Diseases' },
  { slug: 'mcdph',    label: 'Maricopa County DPH — Heat Surveillance' },
  { slug: 'azgfd',    label: 'AZ Game & Fish — Wildlife Health Program' },
  { slug: 'coconino', label: 'Coconino County HHS' }
];

/**
 * Render the agency-picker stub into the header.
 * @param {HTMLElement} mount  element to mount into
 * @param {string} currentSlug currently-active agency slug
 */
export function mountAuthStub(mount, currentSlug) {
  if (!mount) return;
  mount.innerHTML = '';
  mount.classList.add('auth-stub');

  const label = document.createElement('label');
  label.setAttribute('for', 'auth-stub-select');
  label.textContent = 'Signed in as:';
  mount.appendChild(label);

  const select = document.createElement('select');
  select.id = 'auth-stub-select';
  AGENCIES.forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.slug;
    opt.textContent = a.label;
    if (a.slug === currentSlug) opt.selected = true;
    select.appendChild(opt);
  });
  select.addEventListener('change', () => {
    const target = select.value;
    try { localStorage.setItem('dashboard.agency', target); } catch (_) {}
    // Navigate to the matching landing page, computing the relative
    // path from the current depth (we don't know whether we're on
    // /dashboard/index.html or /dashboard/<agency>/<page>.html).
    const here = window.location.pathname;
    let base;
    if (here.includes('/dashboard/') && !/\/dashboard\/?$/.test(here)
        && !/\/dashboard\/index\.html$/.test(here)) {
      base = '../';
    } else {
      base = './';
    }
    window.location.href = `${base}${target}/index.html`;
  });
  mount.appendChild(select);

  const note = document.createElement('span');
  note.className = 'auth-note';
  note.textContent =
    'Stub. Production: agency SSO + per-agency DUA.';
  mount.appendChild(note);
}

/**
 * Expose the agency list (e.g. for the landing page's audience cards
 * to keep their copy in sync with the picker).
 */
export function agencies() {
  return AGENCIES.slice();
}
