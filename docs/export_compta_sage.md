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


## Soldes bancaires Odoo (02/09/2026)

Les banques connectées alimentent les journaux en lignes de relevé ; le
lettrage v2 réconcilie ces lignes (aucune écriture synthétique). Les 248
écritures de reprise du rattrapage ont été extournées (« Extourne reprise —
relevés connectés ») : l'historique 512 d'Odoo = les relevés, rien d'autre.
Les soldes 512 sont alignés sur la réalité bancaire par des écritures de
« Solde initial des banques » datées à l'ouverture comptable de chaque
société (contrepartie 89000000 Bilan d'ouverture), et non par des écritures
de recalage en cours d'exercice. Vérifié au centime contre les soldes des
connecteurs le 02/09/2026. La comptabilité de référence reste Sage.

## Profil « cabinet extérieur » : Distri Béton → FITECO (21/10/2026)

SAS DISTRI BETON VIENNE (société 2) n'a pas de dossier Sage : sa comptabilité est
tenue par le cabinet **FITECO Châtellerault** (Christine Fontenault
`c.fontenault@fiteco.com`, Aurélia Colin `aurelia.colin@fiteco.com` ; boîte de
dépôt des factures `ventes+207082@fiteco.com`). Depuis mai 2025, Isabelle lui
envoie chaque mois, **avant le 15**, le fichier des **ventes** (journal VE) ;
achats et banque sont tenus par le cabinet, la banque reste rapprochée dans Odoo.

Format : le CSV générique de l'action 1459 (16 colonnes `;`, cp1252), validé par
Fiteco le 24/04/2025 avec trois demandes aujourd'hui satisfaites : ventes en
7011 (plus 7071), une seule ligne HT + taxe éco (la REP béton est en 701100,
donc fusionnée), TVA en 445711. Clients en 411100 avec leur code `DISxxxxx`
(particuliers borne = `DIS99999`).

`PROFILS` dans `app.py` (clé = id société) : pour Distri la page n'affiche que le
journal des ventes, pas de fichier « nouveaux clients », bouton direct
« ⬇ Télécharger le fichier des ventes (.csv) » (nom `ventes_DISTRIBETON_AAAA-MM.csv`
pour un mois entier), carte « 3. Envoyer au cabinet » avec lien e-mail prérempli
(destinataires, objet, corps — joindre le fichier), verrou des ventes en étape 4.
Le garde-fou « déjà transférées » et l'historique fonctionnent comme pour Sage
(`x_sage_envoye_le`, `maquignon.export_compta_dernier_2`).

## Colonne « Base TVA » (22/10/2026)

Les registres de TVA de Sage (TVA sur encaissements, « Registres taxe Règlement vente ») reconstituaient la base d'une ligne de
TVA par **TTC de la pièce − montant de la ligne** : juste pour une facture à une seule TVA, faux dès qu'une facture porte à la fois
la TVA collectée (marchandises, 44570009) et la TVA prestations (encaissements, 44570011) — bases surévaluées de 201 585 € sur
juillet-août 2026 chez Maquignon (constaté par Charlotte sur les registres imprimés le 21/09/2026).

Les fichiers Sage (formats ventes et caisse) ont donc une **17e colonne « Base TVA »** : la base hors taxe de chaque ligne de TVA
(`tax_base_amount` d'Odoo, en valeur absolue), vide sur les autres lignes. Charlotte la mappe dans l'import Sage sur la base du
registre. Le profil Fiteco (Distri Béton) reste à 16 colonnes (`colonne_base: False`).

