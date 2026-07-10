# Brief Claude Code — Version Web
## Maquignon Lefevre Converter — Migration Desktop → Web App

---

## Objectif

Réécrire l'application `convertisseur_lefevre_app.py` (Python/tkinter) en
**application web moderne** avec les mêmes fonctionnalités.

Le code métier (parser Excel, connecteur Odoo XML-RPC, export Excel) est
**réutilisable tel quel** — seule l'interface graphique change.

---

## Stack technique recommandée

### Backend — FastAPI (Python)
- Réutilise directement `Config`, `parse_lefevre()`, `OdooConnector`, `generate_excel()`
- API REST + **Server-Sent Events** (SSE) pour la progression en temps réel
- Stockage config : fichier JSON local (même logique que l'app desktop)

### Frontend — React + Tailwind CSS
- Interface identique à l'app desktop (5 onglets)
- Thème sombre bleu marine (couleurs déjà définies dans le code)
- Upload drag & drop pour le fichier Excel
- Tableau de prévisualisation des lignes parsées
- Flux SSE pour afficher les logs d'import en temps réel

### Déploiement
- **Option A** : standalone — `uvicorn main:app` → accessible sur `http://localhost:8000`
- **Option B** : Docker — `docker-compose up`
- Pas de base de données requise (tout en mémoire + config JSON)

---

## Architecture des fichiers à créer

```
lefevre_web/
├── backend/
│   ├── main.py              # FastAPI app — routes API
│   ├── core/
│   │   ├── parser.py        # parse_lefevre(), detect_columns(), etc.  ← COPIER depuis app desktop
│   │   ├── odoo.py          # class OdooConnector                       ← COPIER depuis app desktop
│   │   ├── excel.py         # generate_excel()                          ← COPIER depuis app desktop
│   │   └── config.py        # class Config                              ← COPIER depuis app desktop
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── TabFichier.jsx       # Onglet 1 : upload + paramètres + résumé
│   │   │   ├── TabConnexion.jsx     # Onglet 2 : config Odoo + champs Studio
│   │   │   ├── TabApercu.jsx        # Onglet 3 : tableau des lignes parsées
│   │   │   ├── TabJournal.jsx       # Onglet 4 : logs temps réel
│   │   │   ├── TabMapping.jsx       # Onglet 5 : éditeur mapping natures
│   │   │   ├── StatusBar.jsx        # Barre de statut + progressbar
│   │   │   └── Header.jsx           # Header Maquignon
│   │   └── api.js                   # Fonctions fetch vers le backend
│   ├── package.json
│   └── vite.config.js
└── docker-compose.yml       # optionnel
```

---

## API Backend à créer (FastAPI)

### Routes

```python
# Upload + parsing
POST   /api/parse
       Body: multipart/form-data { file: xlsx, sheet: str? }
       Response: { header_info, stats, rows_preview, sheets_available }

# Export Excel
POST   /api/export
       Body: { parsed_rows, header_info, order_ref, customer, customer_code, order_date }
       Response: fichier .xlsx en streaming

# Config
GET    /api/config
       Response: { odoo, commande, fields, nature_mapping }

POST   /api/config
       Body: config complète
       Response: { ok: true }

# Test connexion Odoo
POST   /api/odoo/test
       Body: { url, database, username, password }
       Response: { ok, version, error? }

# Vérification champs Studio
POST   /api/odoo/check-fields
       Body: { url, database, username, password, fields: {} }
       Response: { results: { ref_pierre: true/false, ... } }

# Diagnostic produit
POST   /api/odoo/diagnose-product
       Body: { url, database, username, password, code: "TUF0000-PS" }
       Response: { lines: ["..."] }

# Import Odoo — SSE pour progression temps réel
POST   /api/odoo/import/start
       Body: { odoo_config, order_config, fields_config, parsed_rows }
       Response: { session_id }

GET    /api/odoo/import/stream/{session_id}
       Response: text/event-stream
       Events:
         data: {"type":"log","msg":"Connexion...","tag":"info"}
         data: {"type":"progress","value":45}
         data: {"type":"done","order_id":37528,"url":"https://..."}
         data: {"type":"error","msg":"..."}
```

### Gestion de session d'import (SSE)

```python
# backend/main.py
import asyncio
from fastapi.responses import StreamingResponse

sessions = {}  # session_id → asyncio.Queue

@app.post("/api/odoo/import/start")
async def start_import(data: ImportRequest, background_tasks: BackgroundTasks):
    session_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    sessions[session_id] = queue
    background_tasks.add_task(run_import, session_id, data, queue)
    return {"session_id": session_id}

@app.get("/api/odoo/import/stream/{session_id}")
async def stream_import(session_id: str):
    queue = sessions.get(session_id)
    async def event_generator():
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error"):
                break
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Fonctionnalités Frontend par onglet

### Onglet 1 — Fichier & Import

```
┌─────────────────────────────────────────────────────────┐
│ FICHIER LEFEVRE                                         │
│ [Drag & drop zone — ou cliquer pour sélectionner]      │
│ Feuille : [dropdown des sheets] ← rempli après upload  │
│                                                         │
│ Détection : Feuille=Feuil1 | Unité=cm | En-tête=ligne8 │
├─────────────────────────────────────────────────────────┤
│ PARAMÈTRES COMMANDE                                     │
│ Référence commande : [BC20260708          ]             │
│ Client (nom Odoo)  : [LEFEVRE             ]             │
│ Code client Odoo   : [LEF001              ]             │
│ Date commande      : [08/07/2026 00:00:00 ]             │
├─────────────────────────────────────────────────────────┤
│ [Analyser]   [Exporter Excel]   [Importer dans Odoo]   │
├─────────────────────────────────────────────────────────┤
│ RÉSUMÉ                                                  │
│ Chantier : LE PALAIS - PAVILLON DES OFFICIERS           │
│ Sections : 2  | Sous-sections : 30  | Lignes : 568      │
│ Cubage : 11.437561 m³  | Produits inconnus : 0         │
└─────────────────────────────────────────────────────────┘
```

### Onglet 2 — Connexion Odoo

```
┌─────────────────────────────────────┐
│ CONNEXION ODOO                      │
│ URL       : [https://...odoo.com]   │
│ Base      : [maquignon           ]  │
│ Utilisateur:[email@...           ]  │
│ Mot de passe:[***************    ]  │
│ [Tester la connexion]               │
│ ✓ Connecté — Odoo 19.0              │
├─────────────────────────────────────┤
│ CHAMPS STUDIO                       │
│ Réf. Pierre   : [x_studio_ref_pierre]│
│ Nbr. pièces   : [x_studio_nbr     ] │
│ Longueur (m)  : [x_studio_long    ] │
│ Largeur (m)   : [x_studio_larg    ] │
│ Hauteur (m)   : [x_studio_haut    ] │
│ Poids (kg)    : [x_studio_poids   ] │
│ [Vérifier champs Studio]            │
├─────────────────────────────────────┤
│ DIAGNOSTIC PRODUIT                  │
│ Code : [TUF0000-PS] [Diagnostiquer] │
├─────────────────────────────────────┤
│ [Enregistrer la configuration]      │
└─────────────────────────────────────┘
```

### Onglet 3 — Aperçu données

Tableau avec colonnes :
Type | Section | Sous-section | Réf. Pierre | Nature | Nbr | Long(m) | Larg(m) | Haut(m) | Vol.m³ | Produit Odoo | Mappé

Colorisation :
- Lignes `section` → fond bleu #2E6DA4
- Lignes `subsection` → fond bleu clair #5B9BD5
- Lignes `line` non mappées → fond rouge sombre

### Onglet 4 — Journal

Zone de log scrollable, messages colorés par tag :
- `ok` → vert `#27AE60`
- `warn` → orange `#F39C12`
- `err` → rouge `#E74C3C`
- `info` → bleu `#5B9BD5`

Progressbar en bas de page pendant l'import.

Lien cliquable vers le devis Odoo créé (`https://maquignon.odoo.com/web#id=37528...`).

### Onglet 5 — Mapping

Tableau éditable :
| Nature Lefevre | Code produit Odoo | Libellé |
|---|---|---|
| Usseau | TUF0000-PS | [TUF0000-PS] Tuffeau... |
| Tuffeau | TUF0000-PS | ... |

Boutons : Ajouter / Modifier / Supprimer / Enregistrer

Formulaire d'édition inline :
- Nature Lefevre (texte)
- Code produit Odoo (texte — extrait auto si collé avec crochets)
- Libellé (texte optionnel)

---

## Code métier à extraire depuis `convertisseur_lefevre_app.py`

Les blocs suivants sont **réutilisables sans modification** dans `backend/core/` :

```
Lignes 104-169   → core/config.py      class Config + DEFAULT_CONFIG
Lignes 174-508   → core/parser.py      safe_str/num + detect_* + parse_lefevre()
Lignes 510-775   → core/odoo.py        class OdooConnector (corriger product_uom→product_uom_id pour v19)
Lignes 777-888   → core/excel.py       generate_excel() + fmt_num()
```

La classe `LefevreMaquignonApp` (lignes 891-1917) est à **remplacer** par le frontend web.

---

## Corrections v19 à appliquer lors de la migration

Dans `core/odoo.py` (extrait de `OdooConnector.create_order_line_product`) :

```python
# AVANT (v18)
vals["product_uom"] = uom_id

# APRÈS (v19)
vals["product_uom_id"] = uom_id
```

Vérifier aussi `product_uom_qty` — peut avoir changé en v19.

---

## Configuration et stockage

### Backend
Config stockée dans `~/.maquignon_lefevre/config.json`
(même structure que l'app desktop — compatible)

### Frontend
- Config Odoo (URL, db, user, pass) → envoyée au backend pour chaque requête
  OU stockée en localStorage (mais mot de passe → préférer backend)
- Parsed rows → state React entre les onglets (pas de persistance nécessaire)
- Mapping → sauvegardé côté backend via `POST /api/config`

---

## Lancement de l'application

```bash
# Backend
cd lefevre_web/backend
pip install fastapi uvicorn pandas openpyxl python-multipart
uvicorn main:app --reload --port 8000

# Frontend (dev)
cd lefevre_web/frontend
npm install
npm run dev   # → http://localhost:5173 avec proxy vers :8000

# Frontend (prod — servir par FastAPI)
npm run build  # → dist/
# FastAPI sert dist/ comme fichiers statiques
```

---

## Thème visuel (couleurs de l'app desktop à reproduire)

```css
--bg:         #0F1923;   /* fond principal */
--sidebar:    #1A2535;   /* header/sidebar */
--card:       #1E2D40;   /* cartes */
--border:     #2A3F58;   /* bordures */
--accent:     #2E6DA4;   /* bleu sections */
--accent2:    #5B9BD5;   /* bleu clair */
--success:    #27AE60;
--warning:    #F39C12;
--error:      #E74C3C;
--text:       #ECF0F1;
--text-dim:   #8B9BB4;
--entry-bg:   #152030;
```

---

## Points d'attention pour Claude Code

1. **SSE vs WebSocket** : SSE suffit (communication unidirectionnelle backend→frontend)
   — plus simple à implémenter et compatible sans proxy spécial.

2. **Upload fichier** : le fichier Excel est uploadé une seule fois à `/api/parse`,
   le backend stocke le résultat parsé en mémoire (ou fichier temp) pour les actions suivantes.

3. **Sécurité mot de passe** : ne pas logger le mot de passe Odoo côté backend.
   Option : stocker un token de session après `connect()`.

4. **Import long** : l'import de 568 lignes prend ~2 minutes — le SSE est indispensable
   pour donner le feedback à l'utilisateur (pas de timeout HTTP).

5. **Compatibilité** : l'app doit fonctionner sur le réseau local Maquignon
   (pas forcément internet). Docker ou `uvicorn` direct.

6. **Export Excel** : générer le fichier `.xlsx` côté backend et le streamer
   en téléchargement (`Content-Disposition: attachment`).

---

## Fichier source de référence

`convertisseur_lefevre_app.py` — version desktop complète fournie en pièce jointe.

---

*Généré le 08/07/2026 — Carrières Maquignon*
