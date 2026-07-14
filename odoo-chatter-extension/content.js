/* Odoo Chatter Manager — script de contenu
 * Applique les réglages (pleine largeur, position du chatter) via des
 * attributs data-* sur <html>, et injecte un bouton flottant de bascule.
 */

const OCX_DEFAULTS = {
  fullwidth: true,
  chatter: "side", // "side" | "below" | "hidden"
  chatterWidth: 35, // % en mode côté
  fab: true, // bouton flottant
};

const OCX_CHATTER_CYCLE = ["side", "below", "hidden"];
const OCX_CHATTER_ICONS = { side: "◨", below: "⬓", hidden: "◻" };
const OCX_CHATTER_LABELS = {
  side: "Chatter : côté",
  below: "Chatter : en bas",
  hidden: "Chatter : masqué",
};

let ocxSettings = { ...OCX_DEFAULTS };

function ocxApply() {
  const html = document.documentElement;
  html.setAttribute("data-ocx-fullwidth", ocxSettings.fullwidth ? "1" : "0");
  html.setAttribute("data-ocx-chatter", ocxSettings.chatter);
  html.style.setProperty("--ocx-chatter-width", ocxSettings.chatterWidth + "%");
  ocxUpdateFab();
}

function ocxSave(patch) {
  ocxSettings = { ...ocxSettings, ...patch };
  chrome.storage.sync.set(patch);
  ocxApply();
}

/* ---------- Détection d'Odoo ----------
 * L'extension est déclarée sur tous les sites : on ne s'active
 * (observateur DOM, bouton flottant) que si la page est un Odoo. */

function ocxLooksLikeOdoo() {
  return !!document.querySelector(
    ".o_web_client, .o_action_manager, .o_form_view, " +
      'script[src*="/web/assets/"], link[href*="/web/assets/"]'
  );
}

/* ---------- Bouton flottant ---------- */

function ocxIsFormWithChatter() {
  return !!document.querySelector(
    ".o-mail-Form-chatter, .o_FormRenderer_chatterContainer"
  );
}

function ocxUpdateFab() {
  let fab = document.getElementById("ocx-fab");
  const wanted = ocxSettings.fab && ocxIsFormWithChatter();

  if (!wanted) {
    if (fab) fab.remove();
    return;
  }
  if (!fab) {
    fab = document.createElement("button");
    fab.id = "ocx-fab";
    fab.type = "button";
    fab.addEventListener("click", () => {
      const i = OCX_CHATTER_CYCLE.indexOf(ocxSettings.chatter);
      const next = OCX_CHATTER_CYCLE[(i + 1) % OCX_CHATTER_CYCLE.length];
      ocxSave({ chatter: next });
    });
    document.body.appendChild(fab);
  }
  fab.textContent = OCX_CHATTER_ICONS[ocxSettings.chatter] || "◨";
  fab.title =
    (OCX_CHATTER_LABELS[ocxSettings.chatter] || "") +
    " — cliquer pour basculer (Alt+Maj+C)";
}

/* Odoo est une SPA : on surveille le DOM pour (ré)injecter le bouton
 * quand on arrive sur une fiche avec chatter. */
function ocxObserve() {
  const observer = new MutationObserver(() => {
    // Débounce léger pour ne pas travailler à chaque mutation
    clearTimeout(ocxObserve._t);
    ocxObserve._t = setTimeout(ocxUpdateFab, 200);
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

/* ---------- Synchronisation des réglages ---------- */

/* Tout changement fait depuis le popup (ou un autre onglet) est appliqué
 * immédiatement, quel que soit le domaine de la page. */
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "sync") return;
  const patch = {};
  for (const [key, { newValue }] of Object.entries(changes)) {
    if (key in OCX_DEFAULTS) patch[key] = newValue;
  }
  if (Object.keys(patch).length) {
    ocxSettings = { ...ocxSettings, ...patch };
    ocxApply();
  }
});

/* ---------- Raccourcis clavier (relayés par le service worker) ---------- */

chrome.runtime.onMessage.addListener((msg) => {
  if (!msg || !msg.type) return;
  if (msg.type === "ocx-cycle-chatter") {
    const i = OCX_CHATTER_CYCLE.indexOf(ocxSettings.chatter);
    ocxSave({ chatter: OCX_CHATTER_CYCLE[(i + 1) % OCX_CHATTER_CYCLE.length] });
  } else if (msg.type === "ocx-toggle-fullwidth") {
    ocxSave({ fullwidth: !ocxSettings.fullwidth });
  }
});

/* ---------- Initialisation ---------- */

/* Attend qu'Odoo soit détecté (le web client se charge en différé) avant
 * d'installer l'observateur DOM. Abandonne au bout de ~10 s sur les sites
 * qui ne sont pas des Odoo, pour ne rien leur coûter. */
function ocxBoot() {
  ocxApply();
  if (ocxLooksLikeOdoo()) {
    ocxObserve();
    ocxUpdateFab();
    return;
  }
  let tries = 0;
  const timer = setInterval(() => {
    if (ocxLooksLikeOdoo()) {
      clearInterval(timer);
      ocxObserve();
      ocxUpdateFab();
    } else if (++tries >= 10) {
      clearInterval(timer);
    }
  }, 1000);
}

chrome.storage.sync.get(OCX_DEFAULTS, (stored) => {
  ocxSettings = { ...OCX_DEFAULTS, ...stored };
  if (document.body) {
    ocxBoot();
  } else {
    document.addEventListener("DOMContentLoaded", ocxBoot);
  }
});

/* Appliquer au plus tôt les attributs (avant le chargement du storage)
 * pour éviter un flash de mise en page. */
ocxApply();
