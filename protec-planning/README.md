# Planning chauffeur PROTEC + « Ma tournée » + Fiche de fin de travaux

Application Flask lisant/écrivant le module **Planning** d'Odoo v19 SaaS
(`planning.slot`) via XML-RPC. Aucun compte Odoo nécessaire pour les chauffeurs.

## Pages

| Route | Usage |
|---|---|
| `/` | Planning **semaine** (bureau) — grille jours × chauffeurs, filtre par chauffeur |
| `/mois?m=YYYY-MM` | Planning **mois** — bandeaux d'entête par semaine, filtre par chauffeur |
| `/ma-tournee?c=<id>&s=<sig>` | Page **mobile chauffeur** (lien signé HMAC, navigation jour par jour) |
| `/fiche/<slot_id>?t=<token>` | **Fiche de fin de travaux** (formulaire mobile, modèle PROTEC) |
| `/liens?token=<PLANNING_SECRET>` | Page **admin** : liens signés de chaque chauffeur (copie / WhatsApp) |
| `/health` | Healthcheck |

## Fiche de fin de travaux

Fidèle au modèle Excel PROTEC : date, immatriculation véhicule, heures
arrivée/départ, temps trajet A/R, opérateur(s), raison sociale + adresse,
tableau **Nature des travaux** (débouchage EU/EP, curage, poste de relevage,
bac à graisse, STEP, autre — quantités + temps), **commentaires**,
tableau **Déchets** (sable, graisse, refus dégrillage, matières de vidanges,
autre — badges STEP PROTEC/CCLST, volume m³, destination, temps dépotage).

À l'enregistrement : écrit les champs `x_fdt_*` sur le `planning.slot`
(dont le détail JSON dans `x_fdt_data`) + poste un résumé HTML dans le
chatter du créneau. Badge « ✓ FDT » visible sur les plannings bureau.

## Champs créés dans Odoo (planning.slot, champs manuels)

`x_fdt_fait`, `x_fdt_date`, `x_fdt_vehicule`, `x_fdt_heure_arrivee`,
`x_fdt_heure_depart`, `x_fdt_temps_trajet`, `x_fdt_operateurs`,
`x_fdt_commentaires`, `x_fdt_data` (JSON).

## Déploiement Render

Nouveau Web Service sur ce dépôt, **Root Directory = `protec-planning`**.

Variables d'environnement :

| Var | Valeur |
|---|---|
| `ODOO_URL` | `https://protec-s3t.odoo.com` |
| `ODOO_DB` | `protec-s3t` |
| `ODOO_USER` | login du compte technique |
| `ODOO_PASSWORD` | mot de passe / clé API |
| `PLANNING_SECRET` | secret HMAC (chaîne aléatoire ≥ 20 caractères) |

Build : `pip install -r requirements.txt` — Start : `gunicorn app:app --workers 2 --timeout 30`

## Distribution des liens chauffeurs

1. Ouvrir `/liens?token=<PLANNING_SECRET>`
2. Copier ou envoyer par WhatsApp le lien de chaque chauffeur
3. Le chauffeur le met en favori — rien à redéployer pour un nouveau chauffeur,
   son lien apparaît automatiquement sur la page.
