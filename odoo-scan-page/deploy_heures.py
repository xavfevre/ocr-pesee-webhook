"""Redéploie les 5 vues website « heures salariés » dans Odoo.

À lancer depuis ce dossier, avec les identifiants du compte technique :

    set ODOO_USER=...        (Windows ; export sous Linux/Mac)
    set ODOO_PWD=...
    python deploy_heures.py

Le script retrouve chaque vue par sa clé (website.mes_heures, etc.), écrit
l'arch depuis le fichier XML local, puis relit pour vérifier que le relais
Render est bien en place.
"""

import os
import ssl
import xmlrpc.client

URL = os.environ.get("ODOO_URL", "https://maquignon.odoo.com")
DB = os.environ.get("ODOO_DB", "maquignon")
USER = os.environ.get("ODOO_USER", "<USER>")
PWD = os.environ.get("ODOO_PWD", "<MDP>")

VUES = {
    "website.mes_heures": "mes_heures.xml",
    "website.heures_admin": "heures_admin.xml",
    "website.heures_horaires": "heures_horaires.xml",
    "website.heures_liens": "heures_liens.xml",
    "website.planning_rh": "planning_rh.xml",
}

MARQUEUR = "ocr-pesee-webhook.onrender.com/heures/rpc"

ctx = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", context=ctx).authenticate(DB, USER, PWD, {})
if not uid:
    raise SystemExit("Authentification Odoo échouée : vérifier ODOO_USER / ODOO_PWD")
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", context=ctx)


def x(model, method, *a, **k):
    return models.execute_kw(DB, uid, PWD, model, method, list(a), k)


dossier = os.path.dirname(os.path.abspath(__file__))
for cle, fichier in VUES.items():
    chemin = os.path.join(dossier, fichier)
    with open(chemin, encoding="utf-8") as f:
        arch = f.read()

    ids = x("ir.ui.view", "search", [[("key", "=", cle)]])
    if not ids:
        print(f"⚠ {cle} : vue introuvable (clé inconnue) — ignorée")
        continue

    x("ir.ui.view", "write", [ids, {"arch": arch}])
    relu = x("ir.ui.view", "read", [ids[0]], fields=["arch_db"])[0]["arch_db"]
    ok = MARQUEUR in relu
    print(f"{'✓' if ok else '✗'} {cle} (id {ids[0]}) : {len(arch)} octets écrits, relais Render {'présent' if ok else 'ABSENT'}")

print("\nTerminé. Tester ensuite /mes-heures depuis un téléphone NON connecté à Odoo.")
