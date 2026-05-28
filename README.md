# App chauffeur — feuilles de travail Odoo (PWA + proxy Flask)

PWA mobile pour donner à chaque chauffeur ses tâches et remplir la feuille de travail
(`x_project_task_worksheet_template_1`) via l'API externe XML-RPC d'Odoo Online.

```
[index.html (PWA)] ⇄ [app.py (Flask/Render)] ⇄ [Odoo XML-RPC]
```

Auth chauffeur = **PIN** (champ `hr.employee.pin`). Le backend détient 1 seule clé API
de service et scope chaque requête au chauffeur connecté.

---

## 1. Backend (Render)

1. Crée un **utilisateur de service** dans Odoo + une **clé API**
   (sa fiche > Préférences > Sécurité du compte > Nouvelle clé API).
2. Nouveau *Web Service* Render à partir du repo :
   - Build : `pip install -r requirements.txt`
   - Start : `gunicorn app:app`
3. Variables d'environnement :
   - `ODOO_URL`   = https://maquignon.odoo.com
   - `ODOO_DB`    = maquignon
   - `ODOO_USER`  = login du user de service
   - `ODOO_API_KEY` = la clé API
   - `APP_SECRET` = chaîne aléatoire longue
4. Vérifie `https://ton-backend.onrender.com/health` → `{"ok":true,"uid":true}`.

## 2. Frontend (Netlify Drop)

- Dans `index.html`, renseigne `API_BASE` = URL de ton backend Render.
- (option) `SIGNATURE_FIELD` = nom du champ binaire pour activer le pad signature.
- Glisse le fichier sur https://app.netlify.com/drop. Installe-le sur l'écran d'accueil du tél.

## 3. À confirmer dans `app.py`

```python
DRIVER_FIELD    = "user_ids"   # mets le vrai champ si chauffeur dédié
WORKSHEET_MODEL = "x_project_task_worksheet_template_1"
WS_TASK_FIELD   = "x_project_task_id"
DONE_STAGE_NAME = "TRANSPORT REALISE"
```

Et chaque chauffeur doit avoir un **PIN** sur sa fiche employé.

---

## Diagnostic (à lancer en local pour confirmer les champs)

```python
import xmlrpc.client
URL="https://maquignon.odoo.com"; DB="maquignon"; USER="..."; KEY="..."
uid=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common").authenticate(DB,USER,KEY,{})
m=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
def fg(model): return m.execute_kw(DB,uid,KEY,model,"fields_get",[],{"attributes":["string","type","relation"]})

print("== Champs tâche pouvant porter le chauffeur ==")
for n,meta in fg("project.task").items():
    if meta.get("relation") in ("res.users","hr.employee") or "chauff" in n.lower():
        print(n, meta["type"], meta.get("relation"), "-", meta["string"])

print("\n== Champs feuille de travail ==")
for n,meta in fg("x_project_task_worksheet_template_1").items():
    if n.startswith("x_studio_"): print(n, meta["type"], "-", meta["string"])
```

---

## MVP livré
- Login PIN, liste des tâches du chauffeur, formulaire **généré dynamiquement** depuis
  les champs `x_studio_*` (texte, nombre, case, sélection, date, **photo**), upload photo
  redimensionnée, pad signature optionnel, enregistrement, "Terminer" (changement d'étape).

## Suite possible
- Signature + envoi du rapport PDF ("Signer/Envoyer le rapport" — logique FSM spécifique).
- Photos sur la tâche (PRISE EN CHARGE / LIVRAISON) : ajouter leurs champs avec `target:"task"`.
- Adresses chargement/livraison dans l'en-tête (ajouter les `x_studio_*` confirmés au `read`).
- Mode hors-ligne (file d'attente d'enregistrements).
- Restreindre le CORS à l'origine Netlify.
