#!/usr/bin/env python3
"""Construit la version personnelle de l'extension : tout débloqué,
aucun paiement, aucune dépendance à ExtensionPay.

Usage : python3 build_perso.py [dossier_sortie]
"""
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC.parent / "dist" / "odoo-chatter-manager-perso"

FILES = [
    "manifest.json", "config.js", "ExtPay.js", "background.js",
    "content.js", "content.css", "popup.html", "popup.css", "popup.js",
]

BACKGROUND_PERSO = """\
/* Odoo Chatter Manager (Perso) — service worker sans paiement.
 * Tout est débloqué en permanence. */

const OCX_STATUS = {
  paid: true,
  trialStartedAt: null,
  trialActive: false,
  premium: true,
  offline: false,
};

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;
  if (msg.type === "ocx-get-status") {
    sendResponse(OCX_STATUS);
    return false;
  }
  // ocx-open-payment : rien à faire dans la version perso.
});

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
    // Onglet sans script de contenu : on ignore.
  }
});
"""

EXTPAY_STUB = """\
/* Simulacre ExtPay pour la version perso : aucun appel réseau. */
var ExtPay = () => ({
  openPaymentPage() {},
  openTrialPage() {},
  openLoginPage() {},
  getUser: async () => ({ paid: true, trialStartedAt: null }),
  startBackground() {},
  onPaid: { addListener() {} },
  onTrialStarted: { addListener() {} },
});
"""

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in FILES:
    shutil.copy(SRC / f, OUT / f)
shutil.copytree(SRC / "icons", OUT / "icons")

# Manifest : nom distinct, pas de script sur extensionpay.com
manifest = json.loads((OUT / "manifest.json").read_text())
manifest["name"] = "Odoo Chatter Manager (Perso)"
manifest["description"] = "Version personnelle, tout débloqué. " + manifest["description"]
manifest["content_scripts"] = [
    cs for cs in manifest["content_scripts"]
    if "https://extensionpay.com/*" not in cs.get("matches", [])
]
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

(OUT / "background.js").write_text(BACKGROUND_PERSO)
(OUT / "ExtPay.js").write_text(EXTPAY_STUB)

print(f"Version perso construite dans : {OUT}")
