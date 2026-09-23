#!/usr/bin/env python3
"""Construit la version Firefox de l'extension à partir des mêmes sources
que la version Chrome. Seul le manifest change (background.scripts au lieu
de service_worker, identifiant Gecko) ; tout le JS/CSS est réutilisé tel
quel car Firefox expose l'API chrome.* en alias de browser.*, et ExtPay
embarque son propre polyfill cross-navigateur.

Usage : python3 build_firefox.py [dossier_sortie]
"""
import json
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else SRC.parent / "dist" / "odoo-chatter-manager-firefox"

FILES = [
    "config.js", "ExtPay.js", "background.js",
    "content.js", "content.css", "popup.html", "popup.css", "popup.js",
]

if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
for f in FILES:
    shutil.copy(SRC / f, OUT / f)
shutil.copytree(SRC / "icons", OUT / "icons")

manifest = json.loads((SRC / "manifest.json").read_text())

# Firefox MV3 : les background scripts s'exécutent en page d'arrière-plan
# non persistante (event page), pas en vrai service worker. C'est la forme
# la plus largement supportée (Firefox 109+).
manifest["background"] = {"scripts": ["background.js"]}

# Identifiant requis par AMO pour la signature/les mises à jour.
manifest["browser_specific_settings"] = {
    "gecko": {
        "id": "odoo-chatter-manager@xavfevre.dev",
        "strict_min_version": "140.0",
        # L'extension ne collecte aucune donnée utilisateur (voir privacy.html).
        "data_collection_permissions": {"required": ["none"]},
    }
}

(OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(f"Version Firefox construite dans : {OUT}")
