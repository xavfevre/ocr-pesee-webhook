# Export comptable Sage — interface web (/export-compta)

*Étape 3 du projet codes clients Sage, construite le 13/08/2026 sur le modèle
de la page /protec/ebp. Objectif : remplacer les actions serveur Odoo payantes.*

## Utilisation

Menu **Comptabilité → 📤 Export Sage** (menu 1059, action act_url 2088 —
ouvre la page Render dans un nouvel onglet, jeton inclus), ou directement :
`https://ocr-pesee-webhook.onrender.com/export-compta/?token=<maquignon.compta_key>`

1. Choisir la **société** et le **mois** (12 derniers proposés) ;
2. L'aperçu liste chaque journal avec pièces / lignes / total débit,
   téléchargeable individuellement (⬇ .txt) ;
3. **ZIP complet** : tous les journaux + `nouveaux_clients_*.txt` (clients des
   écritures du mois jamais transmis à Sage — champ `x_sage_envoye_le` vide) ;
   la case « marquer comme transmis » date les fiches du jour.

## Journaux couverts, par société

- **ventes + banques** : format « écritures groupées par (compte, analytique) »
  — réplique exacte de l'action Odoo 1459 ;
- **caisses** (type cash, ex. CAIS Châtel, Espèces Maquignon) **et journaux de
  session PoS** (ex. **CLO « Cloture CAISSE » Châtel**, type OD, détecté via
  `pos.config`) : format « ligne à ligne tickets comptoir » — réplique exacte
  de l'action 1671 (repli du libellé sur le partenaire des lignes sœurs,
  analytique vidé sur clés composées, comme l'original).

CSV `;`, encodage cp1252, mêmes noms de fichiers, mêmes colonnes :
`Numéro de pièce;Numéro facture;Code journal;Date facture;Code client;Référence
client;Nom client;Code compte;Libellé compte;Date échéance;Débit;Crédit;URL
Facture;Plan;Analytique;Type écriture`. Le code client (411) vient de
`partner_id.ref` — fiabilisé par les étapes 1-2.

## Conformité vérifiée le 13/08/2026

- Journal VE (SARL Maquignon, juin 2026, 1 075 lignes) : fichier **identique
  octet pour octet** à celui de l'action 1459 ✅
- Journal CLO (Châtel, juin 2026, 453 lignes) : **identique** à l'action 1671 ✅

## Fichier nouveaux clients

`Code Client;Intitulé Client;Adresse;Code Postal;Ville;Siret;N° TVA
intracommunautaire;Email;Téléphone` — fiches mères uniquement, avec code.
Initialisation du 13/08 : 1 628 fiches marquées déjà transmises (codes présents
dans les exports Sage Maquignon/Haims ; clients Châtel/Distri facturés avant le
13/08). Les 120 `MAQ0xxxx` hérités partiront dans ce fichier.

## Suppression du code payant Odoo — FAIT le 02/09/2026

Actions serveur **1459** et **1671** supprimées (codes archivés dans
`odoo-scan-page/action_export_compta_1459.py` / `action_export_caisse_1671.py`),
boutons d'export et champs `x_studio_date_de_debut` / `x_studio_date_de_fin`
retirés de la vue journal 6403. Le bouton **Verrouiller (1680)** est conservé.
Jeton : `maquignon.compta_key`.
