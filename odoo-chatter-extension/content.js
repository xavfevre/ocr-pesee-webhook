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

/* ---------- Messages (popup + raccourcis clavier) ---------- */

chrome.runtime.onMessage.addListener((msg) => {
  if (!msg || !msg.type) return;
  if (msg.type === "ocx-settings-changed") {
    ocxSettings = { ...ocxSettings, ...msg.settings };
    ocxApply();
  } else if (msg.type === "ocx-cycle-chatter") {
    const i = OCX_CHATTER_CYCLE.indexOf(ocxSettings.chatter);
    ocxSave({ chatter: OCX_CHATTER_CYCLE[(i + 1) % OCX_CHATTER_CYCLE.length] });
  } else if (msg.type === "ocx-toggle-fullwidth") {
    ocxSave({ fullwidth: !ocxSettings.fullwidth });
  }
});

/* ---------- Initialisation ---------- */

chrome.storage.sync.get(OCX_DEFAULTS, (stored) => {
  ocxSettings = { ...OCX_DEFAULTS, ...stored };
  ocxApply();
  if (document.body) {
    ocxObserve();
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      ocxApply();
      ocxObserve();
    });
  }
});

/* Appliquer au plus tôt les attributs (avant le chargement du storage)
 * pour éviter un flash de mise en page. */
ocxApply();
