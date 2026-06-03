# Migration Odoo V18 → V19 — maquignon.odoo.com

> Instance **Odoo Online (SaaS)**. L'upgrade du cœur Odoo et des
> personnalisations **Studio** est réalisé automatiquement par la plateforme
> d'Odoo. Ce dossier sert à **valider** que les personnalisations (champs
> Studio, actions serveur, champs calculés, rapports) et l'intégration du
> webhook OCR fonctionnent toujours après la bascule.

## 1. Principe de validation

Odoo fournit une **base de TEST en v19** avant de migrer la production.
On capture l'état AVANT (v18) et APRÈS (v19 test), puis on compare
objectivement avec `verify_migration.py`.

```
v18 (prod)  ──snapshot──►  snapshot_v18.json  ┐
                                              ├──► compare ──► régressions ?
v19 (test)  ──snapshot──►  snapshot_v19.json  ┘
```

## 2. Procédure pas à pas

### Étape 0 — Pré-requis
- Un compte technique avec accès API. **En SaaS, génère une clé API**
  (Préférences utilisateur → *Sécurité du compte* → *Nouvelle clé API*) et
  utilise-la comme `ODOO_PASSWORD`.
- `pip install` non requis : le script n'utilise que la lib standard Python.

### Étape 1 — Snapshot de la PROD v18 (AVANT migration)
```bash
export ODOO_URL=https://maquignon.odoo.com
export ODOO_DB=maquignon
export ODOO_USER=compte.technique@maquignon.fr
export ODOO_PASSWORD=<cle_api>

python migration/verify_migration.py snapshot --out migration/snapshot_v18.json
```

### Étape 2 — Demander l'upgrade
- Va sur https://upgrade.odoo.com (ou *Gestionnaire de bases* → *Upgrade*).
- Choisis **19.0** comme version cible et le type **Test** d'abord.
- Odoo te fournit une base de test (souvent `maquignon-test.odoo.com` ou une
  URL dédiée).

### Étape 3 — Snapshot de la base de TEST v19 (APRÈS migration)
```bash
python migration/verify_migration.py snapshot \
    --url https://<url-base-test-v19> \
    --db <db-test-v19> \
    --user "$ODOO_USER" --password "$ODOO_PASSWORD" \
    --out migration/snapshot_v19.json
```

### Étape 4 — Comparer
```bash
python migration/verify_migration.py compare \
    migration/snapshot_v18.json migration/snapshot_v19.json
```
- Code retour **0** = aucune régression bloquante.
- Code retour **1** = champs / actions / rapports manquants → voir la liste.

## 3. Checklist de validation manuelle (sur la base de TEST v19)

### 🔧 Personnalisations Studio
- [ ] Le modèle de worksheet FSM existe toujours et porte le **même nom
      technique** (`x_project_task_worksheet_template_1_line`). ⚠️ S'il a été
      renommé, mettre à jour `ODOO_WORKSHEET_MODEL` côté Render.
- [ ] Tous les champs `x_studio_*` sont présents (voir diff automatique).
- [ ] La photo (`x_studio_photo_bon`) s'affiche et se télécharge.
- [ ] La relation worksheet → tâche (`x_project_task_id`) est intacte.

### ⚙️ Actions serveur & automatisations
- [ ] Les actions serveur listées dans le snapshot v18 existent en v19.
- [ ] Les **webhooks/automatisations** qui déclenchent `/ocr-pesee` et
      `/add-section` se déclenchent toujours (créer un enregistrement test).
- [ ] Le code Python des actions serveur ne lève pas d'erreur (tester un
      déclenchement manuel).

### 🧮 Champs calculés
- [ ] Chaque champ marqué `computed` dans le diff renvoie une valeur cohérente.
- [ ] Les champs calculés **stockés** sont recalculés correctement (ouvrir
      quelques enregistrements et vérifier).
- [ ] `x_studio_poids_net` (utilisé par le webhook) reste fiable.

### 📄 Rapports (QWeb / PDF)
- [ ] Chaque rapport listé dans le snapshot s'imprime sans erreur.
- [ ] La mise en page et les champs `x_studio_*` apparaissent dans le PDF.
- [ ] Les sections de commande (`display_type='line_section'`) créées par le
      webhook s'affichent correctement dans le devis/la commande.

### 🔌 Intégration webhook (test de bout en bout)
- [ ] Pointer une variable d'env temporaire vers la base de test v19.
- [ ] Déposer une photo de bon de pesée sur une worksheet.
- [ ] Vérifier `/health`, puis le déclenchement `/ocr-pesee` :
      statut « ⏳ » → champs remplis → statut « ✅ ».
- [ ] Vérifier la création de la section sur la commande liée.
- [ ] Vérifier l'authentification API (clé API vs mot de passe).

## 4. Points d'attention v19 spécifiques à cette intégration

| Risque | Détail | Action |
|--------|--------|--------|
| Nom de modèle Studio | Le worksheet auto-généré peut être renommé | Variable `ODOO_WORKSHEET_MODEL` (aucun code à toucher) |
| Auth API | SaaS v19 durcit l'accès externe | Basculer `ODOO_PASSWORD` sur une **clé API** |
| Champs `x_studio_*` | Normalement préservés | Validés par le diff automatique |
| XML-RPC | Toujours supporté en v19 | Aucun changement de protocole |

> **Note :** les « breaking changes » serveur de la v19 (SQL() builder, type
> hints, `models.Constraint()`, OWL 3.x, `_check_company_auto`) concernent le
> code de **modules custom**. Ce projet n'en contient pas : seul un client
> XML-RPC externe (le webhook) parle à Odoo. Aucune de ces contraintes ne
> s'applique au code de ce dépôt.
