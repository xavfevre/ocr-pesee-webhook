/* Odoo Chatter Manager — service worker
 * - Raccourcis clavier relayés vers l'onglet actif
 * - Statut Premium (ExtensionPay) : achat ou essai gratuit en cours */

importScripts("config.js", "ExtPay.js");

const extpay = ExtPay(OCX_EXTPAY_ID);
extpay.startBackground();

/* ---------- Statut Premium ---------- */

async function ocxGetStatus() {
  try {
    const user = await extpay.getUser();
    const trialStart = user.trialStartedAt ? user.trialStartedAt.getTime() : null;
    const trialActive = !!trialStart && Date.now() - trialStart < OCX_TRIAL_MS;
    const status = {
      paid: !!user.paid,
      trialStartedAt: trialStart,
      trialActive,
      premium: !!user.paid || trialActive,
      offline: false,
    };
    chrome.storage.local.set({ ocxPremiumCache: status });
    return status;
  } catch (e) {
    // Hors ligne ou extension pas encore enregistrée sur extensionpay.com :
    // on retombe sur le dernier statut connu (essai recalculé, il peut
    // avoir expiré entre-temps).
    const { ocxPremiumCache } = await chrome.storage.local.get("ocxPremiumCache");
    const base = ocxPremiumCache || { paid: false, trialStartedAt: null };
    const trialActive =
      !!base.trialStartedAt && Date.now() - base.trialStartedAt < OCX_TRIAL_MS;
    return {
      paid: !!base.paid,
      trialStartedAt: base.trialStartedAt || null,
      trialActive,
      premium: !!base.paid || trialActive,
      offline: true,
    };
  }
}

async function ocxBroadcastPremium() {
  const status = await ocxGetStatus();
  const tabs = await chrome.tabs.query({});
  for (const tab of tabs) {
    if (!tab.id) continue;
    chrome.tabs
      .sendMessage(tab.id, { type: "ocx-premium-changed", status })
      .catch(() => {});
  }
}

extpay.onPaid.addListener(ocxBroadcastPremium);
if (extpay.onTrialStarted) {
  extpay.onTrialStarted.addListener(ocxBroadcastPremium);
}

/* ---------- Messages ---------- */

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;

  if (msg.type === "ocx-get-status") {
    ocxGetStatus().then(sendResponse);
    return true; // réponse asynchrone
  }

  if (msg.type === "ocx-open-payment") {
    extpay.openPaymentPage();
  }
});

/* ---------- Raccourcis clavier ---------- */

chrome.commands.onCommand.addListener(async (command) => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab || !tab.id) return;

  const type =
    command === "cycle-chatter"
      ? "ocx-cycle-chatter"
      : command === "toggle-fullwidth"
        ? "ocx-toggle-fullwidth"
        : null;
  if (!type) return;

  try {
    await chrome.tabs.sendMessage(tab.id, { type });
  } catch (e) {
    // Onglet sans script de contenu (pas une page Odoo) : on ignore.
  }
});
