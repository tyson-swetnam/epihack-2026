// shared/i18n.js
// Minimal JSON-driven message bundle. English + Spanish (es).
// High-frequency strings only; longer prose stays in HTML for now and gets
// professionally translated in Phase 2.
//
// Usage:
//   import { t, currentLang, setLang, onLangChange, mountSwitcher } from
//          '../shared/i18n.js';
//   element.textContent = t('heat.checkin.title');
//
// Language is chosen in this order:
//   1. localStorage('sentinel.lang') -- explicit user choice persists
//   2. navigator.language starts with 'es' AND the page opted in via
//      <body data-i18n-default="auto"> (heat flows do)
//   3. 'en' fallback
//
// All strings live in MESSAGES below; missing keys fall back to English.

const MESSAGES = {
  en: {
    'nav.back':            'Back',
    'nav.next':            'Next',
    'nav.review':          'Review',
    'nav.submit':          'Submit',
    'nav.home':            'Back to app home',

    'common.required':     'Required',
    'common.optional':     'Optional',
    'common.unknown':      'Unknown',
    'common.yes':          'Yes',
    'common.no':           'No',
    'common.skip':         'Skip',
    'common.continue':     'Continue',

    'geo.use_location':    'Use my location',
    'geo.asking':          'Asking for location permission…',
    'geo.got':             'Got it',
    'geo.unsupported':     "This device can't share location. Enter your ZIP instead.",
    'geo.denied':          'Location not shared. Enter your ZIP below instead.',
    'geo.zip_placeholder': 'ZIP (e.g. 85003)',
    'geo.zip_label':       'ZIP code',

    'heat.checkin.title':       'Heat check-in',
    'heat.checkin.subtitle':    'Block-by-block outreach',
    'heat.selfreport.title':    'Heat self-report',
    'heat.selfreport.subtitle': 'Anonymous, takes about a minute',
    'heat.cooloff.title':       'Where can I cool off?',
    'heat.cooloff.subtitle':    'Nearest open cooling centers',

    'heat.subject.heading':       'Who are you checking on?',
    'heat.subject.age':           'Approximate age',
    'heat.subject.age.under18':   'Under 18',
    'heat.subject.age.18_39':     '18 to 39',
    'heat.subject.age.40_64':     '40 to 64',
    'heat.subject.age.65plus':    '65+',
    'heat.subject.sex':           'Sex',
    'heat.subject.sex.f':         'Female',
    'heat.subject.sex.m':         'Male',
    'heat.subject.sex.other':     'Other / prefer not to say',
    'heat.subject.unsheltered':   'Currently unsheltered?',
    'heat.subject.unsheltered.hint':'Default-on for outreach flows. Drives the vulnerability score.',
    'heat.subject.pet':           'With a pet?',
    'heat.subject.pet.hint':      'Filters out non-pet-friendly cooling centers.',

    'heat.where.heading':         'Where and when',
    'heat.where.time':            'Time of check-in',

    'heat.symptoms.heading':      'What are you seeing?',
    'heat.symptoms.lead':         'Tap all that apply. "None of the above" is a perfectly normal answer.',
    'heat.symptoms.confusion':    'Confusion / altered mental status',
    'heat.symptoms.hot_dry_skin': 'Hot dry skin (not sweating)',
    'heat.symptoms.heavy_sweating':'Heavy sweating',
    'heat.symptoms.headache':     'Headache',
    'heat.symptoms.dizziness':    'Dizziness',
    'heat.symptoms.muscle_cramps':'Muscle cramps',
    'heat.symptoms.none':         'None of the above',
    'heat.symptoms.coretemp':     'Core body temperature (°F, if you measured)',
    'heat.symptoms.coretemp.hint':'Optional. ≥ 104 °F is the heat-stroke threshold.',

    'heat.exposure.heading':      'Today\'s exposure',
    'heat.exposure.outdoor':      'Outdoor time today',
    'heat.exposure.outdoor.hint': 'Best guess in hours. ≥ 4 h adds 2 points to the score.',
    'heat.exposure.outdoor.value':'{n} h',
    'heat.exposure.ac':           'Access to air conditioning today?',
    'heat.exposure.ac.hint':      'Working AC is the single strongest indoor-mortality protector.',
    'heat.exposure.water':        'When did they last drink water?',
    'heat.exposure.water.under1': 'Within the last hour',
    'heat.exposure.water.1_3':    '1 to 3 hours ago',
    'heat.exposure.water.over3':  'More than 3 hours ago',
    'heat.exposure.water.unknown':"Don't know",
    'heat.exposure.meds':         'On thermoregulation-affecting medications?',
    'heat.exposure.meds.hint':    'Antipsychotics, anticholinergics, diuretics, beta-blockers, stimulants.',
    'heat.exposure.transport':    'Has transport available?',
    'heat.exposure.transport.hint':'If no, transport will be dispatched on Go-to-cooling-center.',

    'heat.consent.heading':       'What we keep and what we drop',
    'heat.consent.profile':       'Profile: consent.anonymous_heat',
    'heat.consent.accept':        'I have explained this and the subject (or their proxy) accepts.',

    'heat.submit.heading':        'Ready to send?',
    'heat.submit.running':        'Running the agent pipeline…',
    'heat.submit.score':          'Heat-vulnerability score',
    'heat.submit.score.outof':    'out of {max}',
    'heat.submit.nearest':        'Nearest open cooling center',
    'heat.submit.request_transport':'Request transport (211 Arizona)',
    'heat.submit.confirm':        'Tap again to confirm dispatch',
    'heat.submit.dispatched':     'Transport dispatched',
    'heat.submit.call_211':       'Call 211 Arizona',
    'heat.submit.cluster_note':   'This observation feeds the Cluster Detection Agent — 5 unsheltered heat-exhaustion check-ins in the same ZCTA within 2 h triggers a county heat-emergency alert to MCDPH.',

    'tc.go_to_cooling_center':    'Go to a cooling center',
    'tc.dispatch_chw':            'Dispatch CHW',
    'tc.call_911':                'Call 911 — possible heat stroke',
    'tc.check_in_only':           'Logged for follow-up',
    'tc.drink_water_advisory':    'Drink water, rest, recheck',

    'cooloff.list.heading':       'Nearest cooling centers',
    'cooloff.list.empty':         'No open centers found near you. Tap "Call 211" for live help.',
    'cooloff.center.distance':    '{km} km away',
    'cooloff.center.open':        'Open now',
    'cooloff.center.pets':        'Pet-friendly',
    'cooloff.center.transport':   'Transport eligible',
    'cooloff.center.open_maps':   'Open in Maps',
    'cooloff.center.call_211':    'Call 211',
  },

  es: {
    'nav.back':            'Atrás',
    'nav.next':            'Siguiente',
    'nav.review':          'Revisar',
    'nav.submit':          'Enviar',
    'nav.home':            'Volver al inicio',

    'common.required':     'Requerido',
    'common.optional':     'Opcional',
    'common.unknown':      'Desconocido',
    'common.yes':          'Sí',
    'common.no':           'No',
    'common.skip':         'Omitir',
    'common.continue':     'Continuar',

    'geo.use_location':    'Usar mi ubicación',
    'geo.asking':          'Solicitando permiso de ubicación…',
    'geo.got':             'Listo',
    'geo.unsupported':     'Este dispositivo no comparte la ubicación. Ingrese el código postal.',
    'geo.denied':          'Ubicación no compartida. Ingrese el código postal abajo.',
    'geo.zip_placeholder': 'Código postal (p. ej. 85003)',
    'geo.zip_label':       'Código postal',

    'heat.checkin.title':       'Chequeo por calor',
    'heat.checkin.subtitle':    'Visita comunitaria',
    'heat.selfreport.title':    'Reporte personal de calor',
    'heat.selfreport.subtitle': 'Anónimo, alrededor de un minuto',
    'heat.cooloff.title':       '¿Dónde puedo refrescarme?',
    'heat.cooloff.subtitle':    'Centros de enfriamiento cercanos',

    'heat.subject.heading':       '¿A quién está revisando?',
    'heat.subject.age':           'Edad aproximada',
    'heat.subject.age.under18':   'Menos de 18',
    'heat.subject.age.18_39':     '18 a 39',
    'heat.subject.age.40_64':     '40 a 64',
    'heat.subject.age.65plus':    '65 o más',
    'heat.subject.sex':           'Sexo',
    'heat.subject.sex.f':         'Femenino',
    'heat.subject.sex.m':         'Masculino',
    'heat.subject.sex.other':     'Otro / prefiero no decir',
    'heat.subject.unsheltered':   '¿Sin hogar actualmente?',
    'heat.subject.unsheltered.hint':'Activado por defecto para visitas comunitarias.',
    'heat.subject.pet':           '¿Con una mascota?',
    'heat.subject.pet.hint':      'Filtra centros que no admiten mascotas.',

    'heat.where.heading':         'Dónde y cuándo',
    'heat.where.time':            'Hora del chequeo',

    'heat.symptoms.heading':      '¿Qué observa?',
    'heat.symptoms.lead':         'Marque todo lo que aplique. "Nada de lo anterior" es una respuesta válida.',
    'heat.symptoms.confusion':    'Confusión / estado mental alterado',
    'heat.symptoms.hot_dry_skin': 'Piel caliente y seca (sin sudar)',
    'heat.symptoms.heavy_sweating':'Sudoración intensa',
    'heat.symptoms.headache':     'Dolor de cabeza',
    'heat.symptoms.dizziness':    'Mareos',
    'heat.symptoms.muscle_cramps':'Calambres musculares',
    'heat.symptoms.none':         'Nada de lo anterior',
    'heat.symptoms.coretemp':     'Temperatura corporal (°F, si la midió)',
    'heat.symptoms.coretemp.hint':'Opcional. ≥ 104 °F es el umbral de golpe de calor.',

    'heat.exposure.heading':      'Exposición de hoy',
    'heat.exposure.outdoor':      'Horas al aire libre hoy',
    'heat.exposure.outdoor.hint': 'Estimación en horas. ≥ 4 h suma 2 puntos.',
    'heat.exposure.outdoor.value':'{n} h',
    'heat.exposure.ac':           '¿Tiene aire acondicionado hoy?',
    'heat.exposure.ac.hint':      'AC funcionando es la mejor protección bajo techo.',
    'heat.exposure.water':        '¿Cuándo bebió agua por última vez?',
    'heat.exposure.water.under1': 'En la última hora',
    'heat.exposure.water.1_3':    'Hace 1 a 3 horas',
    'heat.exposure.water.over3':  'Hace más de 3 horas',
    'heat.exposure.water.unknown':'No sabe',
    'heat.exposure.meds':         '¿Toma medicamentos que afectan termorregulación?',
    'heat.exposure.meds.hint':    'Antipsicóticos, anticolinérgicos, diuréticos, beta-bloqueadores.',
    'heat.exposure.transport':    '¿Tiene transporte disponible?',
    'heat.exposure.transport.hint':'Si no, se enviará transporte al centro de enfriamiento.',

    'heat.consent.heading':       'Qué guardamos y qué descartamos',
    'heat.consent.profile':       'Perfil: consent.anonymous_heat',
    'heat.consent.accept':        'He explicado esto y la persona (o representante) acepta.',

    'heat.submit.heading':        '¿Listo para enviar?',
    'heat.submit.running':        'Ejecutando la cadena de agentes…',
    'heat.submit.score':          'Puntaje de vulnerabilidad por calor',
    'heat.submit.score.outof':    'de {max}',
    'heat.submit.nearest':        'Centro de enfriamiento más cercano',
    'heat.submit.request_transport':'Solicitar transporte (211 Arizona)',
    'heat.submit.confirm':        'Toque de nuevo para confirmar',
    'heat.submit.dispatched':     'Transporte enviado',
    'heat.submit.call_211':       'Llamar al 211 Arizona',
    'heat.submit.cluster_note':   'Esta observación alimenta el Agente de Detección de Conglomerados — 5 chequeos en el mismo ZCTA en 2 h activan una alerta de emergencia a MCDPH.',

    'tc.go_to_cooling_center':    'Vaya a un centro de enfriamiento',
    'tc.dispatch_chw':            'Enviar promotor de salud',
    'tc.call_911':                'Llame al 911 — posible golpe de calor',
    'tc.check_in_only':           'Registrado para seguimiento',
    'tc.drink_water_advisory':    'Beba agua, descanse, vuelva a revisar',

    'cooloff.list.heading':       'Centros de enfriamiento cercanos',
    'cooloff.list.empty':         'No se encontraron centros abiertos. Toque "Llamar al 211".',
    'cooloff.center.distance':    'a {km} km',
    'cooloff.center.open':        'Abierto ahora',
    'cooloff.center.pets':        'Admite mascotas',
    'cooloff.center.transport':   'Transporte disponible',
    'cooloff.center.open_maps':   'Abrir en Mapas',
    'cooloff.center.call_211':    'Llamar al 211',
  },

  // -----------------------------------------------------------------
  // Diné Bizaad (Navajo) -- PLACEHOLDER BUNDLE.
  //
  // Every key falls back to English at runtime via the `t()` helper.
  // The small set of keys present here is meant to make the language
  // switcher work and to mark the surfaces that a native-speaker
  // reviewer should translate first. DO NOT ship these strings
  // publicly without a Diné Bizaad speaker's review -- per plan/02
  // "Auth + data-sovereignty notes" the indigenous-language UI is
  // gated on native-speaker sign-off.
  // -----------------------------------------------------------------
  nv: {
    '_status':            'placeholder-needs-native-speaker-review',
    '_display_name':      'Diné Bizaad',
    '_display_name_en':   'Navajo',
    // The handful of strings worth attempting before review -- mark
    // these as "best guess" pending review. The runtime falls back
    // to English for everything else.
    'common.yes':         'Aooʼ',     // "Yes"
    'common.no':          'Dooda',         // "No"
    'common.continue':    'Tʼóó shįįʼ',  // "Continue" (best guess; review)
    'nav.back':           'Tʼáádiííʼ ', // placeholder
    'nav.submit':         'Submit',        // intentional EN fallback
  },

  // -----------------------------------------------------------------
  // Tohono O'odham -- PLACEHOLDER BUNDLE. Same caveats as Diné Bizaad.
  // -----------------------------------------------------------------
  oh: {
    '_status':            'placeholder-needs-native-speaker-review',
    '_display_name':      'Oʼodham ñiok',
    '_display_name_en':   "Tohono O'odham",
    'common.yes':         'Heuʼu',    // "Yes" -- review
    'common.no':          'Pi-a',          // "No" -- review
    'common.continue':    'Continue',      // EN fallback
    'nav.back':           'Back',          // EN fallback
    'nav.submit':         'Submit',        // EN fallback
  },
};

const STORAGE_KEY = 'sentinel.lang';
let _lang = 'en';
const _listeners = new Set();

function detectInitialLang() {
  // 1. Explicit storage choice always wins.
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && MESSAGES[saved]) return saved;
  } catch (_) { /* private mode */ }

  // 2. data-i18n-default="auto" on <body> opts the page into browser detection.
  const auto =
    document.body && document.body.getAttribute('data-i18n-default') === 'auto';
  if (auto && (navigator.language || '').toLowerCase().startsWith('es')) {
    return 'es';
  }
  return 'en';
}

export function currentLang() { return _lang; }

export function setLang(lang) {
  if (!MESSAGES[lang]) return;
  _lang = lang;
  try { localStorage.setItem(STORAGE_KEY, lang); } catch (_) {}
  document.documentElement.setAttribute('lang', lang);
  _listeners.forEach((cb) => { try { cb(lang); } catch (_) {} });
  applyAttributes();
}

export function onLangChange(cb) {
  _listeners.add(cb);
  return () => _listeners.delete(cb);
}

/**
 * Translate a key. Supports {placeholder} substitution.
 *   t('heat.exposure.outdoor.value', { n: 8 })
 */
export function t(key, vars) {
  const bundle = MESSAGES[_lang] || MESSAGES.en;
  const raw = bundle[key] || MESSAGES.en[key] || key;
  if (!vars) return raw;
  return raw.replace(/\{(\w+)\}/g, (_, k) =>
    Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : `{${k}}`);
}

/**
 * Walk the DOM for [data-i18n] / [data-i18n-attr] hooks and substitute.
 * Pages can mark up purely static strings without writing any JS.
 *
 *   <button data-i18n="nav.next">Next</button>
 *   <input data-i18n-attr="placeholder:geo.zip_placeholder" />
 */
export function applyAttributes(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (key) el.textContent = t(key);
  });
  root.querySelectorAll('[data-i18n-attr]').forEach((el) => {
    el.getAttribute('data-i18n-attr').split(';').forEach((pair) => {
      const [attr, key] = pair.split(':').map((s) => s && s.trim());
      if (attr && key) el.setAttribute(attr, t(key));
    });
  });
}

/**
 * Inject a tiny [EN | ES] switcher into a container.
 *   mountSwitcher(document.querySelector('.app-header'));
 */
export function mountSwitcher(host) {
  if (!host) return;
  if (host.querySelector('.lang-switch')) return;
  const wrap = document.createElement('div');
  wrap.className = 'lang-switch';
  wrap.setAttribute('role', 'group');
  wrap.setAttribute('aria-label', 'Language');
  ['en', 'es'].forEach((code) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = code === 'en' ? 'EN' : 'ES';
    b.setAttribute('aria-pressed', code === _lang ? 'true' : 'false');
    b.addEventListener('click', () => setLang(code));
    wrap.appendChild(b);
  });
  host.appendChild(wrap);
  onLangChange(() => {
    wrap.querySelectorAll('button').forEach((b, i) => {
      b.setAttribute('aria-pressed', ['en','es'][i] === _lang ? 'true' : 'false');
    });
  });
}

// Boot — defer until DOM exists so detectInitialLang can read <body>.
function boot() {
  _lang = detectInitialLang();
  document.documentElement.setAttribute('lang', _lang);
  applyAttributes();
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot, { once: true });
} else {
  boot();
}
