# Planning chauffeur PROTEC + « Ma tournée » + Fiche de fin de travaux

Application Flask lisant/écrivant le module **Planning** d'Odoo v19 SaaS
(`planning.slot`) via XML-RPC. Aucun compte Odoo nécessaire pour les chauffeurs.

## Plannings bureau = pages du site Odoo (comme Maquignon)

Les vues **semaine** et **mois** du bureau sont des pages QWeb publiées sur le
site `protec-s3t.odoo.com` (copies des vues dans `odoo-views/`) :

| Page Odoo | Vue | Usage |
|---|---|---|
| `/planning-semaine?w=<offset>&c=<chauffeur>` | id 4162, clé `website.planning_protec_semaine` | Grille jours × chauffeurs, filtre chauffeur |
| `/planning-mois?m=YYYY-MM&c=<chauffeur>` | id 4163, clé `website.planning_protec_mois` | Bandeaux d'entête par semaine |

Particularité QWeb v19 SaaS : `dateutil.tz` et `pytz` indisponibles dans le
rendu — le décalage Europe/Paris est calculé dans le template (heure d'été
française = dernier dimanche de mars → dernier dimanche d'octobre).

## Pages de l'app Render (chauffeurs)

| Route | Usage |
|---|---|
| `/protec/` | Planning **semaine** (bureau) — grille jours × chauffeurs, filtre par chauffeur |
| `/protec/mois?m=YYYY-MM` | Planning **mois** — bandeaux d'entête par semaine, filtre par chauffeur |
| `/protec/ma-tournee?c=<id>&s=<sig>` | Page **mobile chauffeur** (lien signé HMAC, navigation jour par jour) |
| `/protec/fiche/<slot_id>?t=<token>` | **Fiche de fin de travaux** (formulaire mobile, modèle PROTEC) |
| `/protec/liens?token=<PROTEC_PLANNING_SECRET>` | Page **admin** : liens signés de chaque chauffeur (copie / WhatsApp) |
| `/protec/health` | Healthcheck |

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

Le module est monté sous `/protec` dans le service Render existant (`ocr-pesee-webhook`) — aucun service séparé à créer. Ajouter simplement les variables d'environnement ci-dessous au service existant.

Variables d'environnement :

| Var | Valeur |
|---|---|
| `PROTEC_ODOO_USER` | login du compte technique Odoo |
| `PROTEC_ODOO_PASSWORD` | mot de passe / clé API |
| `PROTEC_PLANNING_SECRET` | secret HMAC (chaîne aléatoire ≥ 20 caractères) |

(`PROTEC_ODOO_URL` et `PROTEC_ODOO_DB` sont facultatives — valeurs protec-s3t par défaut.)

## Distribution des liens chauffeurs

1. Ouvrir `/protec/liens?token=<PROTEC_PLANNING_SECRET>`
2. Copier ou envoyer par WhatsApp le lien de chaque chauffeur
3. Le chauffeur le met en favori — rien à redéployer pour un nouveau chauffeur,
   son lien apparaît automatiquement sur la page.
