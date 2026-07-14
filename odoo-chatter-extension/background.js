/* Odoo Chatter Manager — service worker
 * Relaie les raccourcis clavier vers l'onglet actif. */

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
