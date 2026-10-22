# Borne à béton Distri Béton ↔ Odoo (22/10/2026)

## Ce qu'il y avait avant

La borne Easy Béton (GR-Tech, Ludovic Chony) tourne sur le PC industriel `192.168.1.200` (XAMPP + serveur FTP FileZilla 1.12,
TLS explicite obligatoire). Deux échanges de fichiers, tous les deux à la main :

| Sens | Fichier | Avant | Maintenant |
|---|---|---|---|
| Odoo → borne | `/Imports/Contact (res.partner).csv` : tous les clients Distri Béton avec leur code DIS (format exact de l'export Odoo, virgules + guillemets, 13 colonnes). La borne le relit dès qu'il change ; un nouveau client doit y être pour que son badge fonctionne. | export Odoo manuel, dernier le 07/09/2026 | **automatique** dans la minute qui suit la création ou la modification d'un client |
| borne → Odoo | `/Exports/BLSnnnnn.csv` : un fichier par prise, écrit en lot chaque soir à **20 h** (colonnes CARDCOD…ORDCODFILTRE, séparateur `;`). | Delphine les récupérait en FTP, les importait dans les commandes avec un mappage enregistré puis les déplaçait dans `/Exports/Sauv` (1 842 commandes en 2026) | l'agent les transmet, **Delphine valide sur une page web** avant création des commandes |

Danger connu (mail de Ludovic du 15/03/2025) : un fichier clients incomplet ou avec des codes en double **efface des clients sur la borne**
(325 clients perdus ce jour-là). D'où les garde-fous ci-dessous.

## Architecture

```
PC de la borne (.200, FTP)  <── FTPS ──>  agent PowerShell (PC de caisse / Delphine, toutes les minutes)  <── HTTPS ──>  relais Render /borne  <── XML-RPC ──>  Odoo
```

* **Relais** `borne_web.py` (monté sur `/borne`, clé `maquignon.borne_key`) :
  * `api/etat` : signature de la base clients (nombre + dernière modification), prises à valider, dernier agent vu, dépôt forcé demandé ;
  * `api/clients.csv` : le fichier complet (clients Distri Béton ou code DIS, avec un code), garde-fous → `409` si codes en double,
    moins de 100 clients, ou liste qui a rétréci de plus de 10 % depuis le dernier dépôt (sauf `?forcer=1`) ;
  * `api/depot` : réception des CSV de prises → enregistrements `x_borne_bon` « à valider », client résolu par code DIS, article par
    référence interne = code recette (sinon par nom), anomalies et doublons signalés (`origin = Borne Snnnnn`, même client à la même heure) ;
  * `api/valider` : une commande Distri Béton par prise (client, article, volume, prix borne forcé seulement s'il est > 0, badge / nom badge /
    chantier / date de distribution dans les champs Studio, `client_order_ref` = chantier, `origin = Borne Snnnnn`), confirmée ;
  * `api/rejeter`, `api/corriger` (client ou article), `api/recherche`, `api/export-journal` (→ `x_borne_export`), `api/exports`, `api/forcer`.
* **Page** `borne_page.html` : prises à valider (cases à cocher, corrections, création des commandes), historique des imports, état et
  **historique de l'export automatique** des clients, bouton « forcer un dépôt ».
* **Agent** `docs/borne_agent.ps1` (installé par `docs/borne_installer.ps1` dans `%LOCALAPPDATA%\BorneDistriBeton`, mot de passe FTP chiffré
  DPAPI, certificat FTP épinglé) : à chaque passage, compare la signature clients, dépose le fichier (temporaire puis renommage) et consigne
  le résultat ; lit les `BLS*.csv`, les transmet, les range dans `Sauv`. Journal `journal.txt`, état `etat.json`.
* **Odoo** (`pa_test/borne_setup.py apply`) : modèles `x_borne_bon`, `x_borne_export`, droits utilisateurs internes, vues, menu
  Logistiques > Borne à béton (page de validation, prises, exports), clé `maquignon.borne_key`.

## Installation sur le PC

```
powershell -ExecutionPolicy Bypass -File borne_installer.ps1 -Cle <clé maquignon.borne_key> -FtpUser contact@chatelbeton.fr -FtpPass <mot de passe FTP> -Poste caisse-chatel
```

Page de validation : `https://ocr-pesee-webhook.onrender.com/borne/?k=<clé>` (aussi dans le menu Logistiques > Borne à béton).

## Relevé technique du FTP (22/10/2026)

* FileZilla Server 1.12.6 : `AUTH TLS` obligatoire, reprise de session TLS exigée sur la connexion de données (Python `ftplib` : `wrap_socket(session=…)`,
  `curl` Windows échoue en 425, .NET `FtpWebRequest` fonctionne). Empreinte SHA-256 du certificat : `ab1d8099…4393`.
* `/Exports` : 148 prises en attente du 05/10 au 21/10/2026 (toutes écrites à 20 h locales), `/Exports/Sauv` : 3 655 traitées.
* `/Imports` : `Contact (res.partner).csv` (498 clients, 27 sans code, 1 code `CELTAN`), `Recettes.csv`.
* Prises : 7 h – 17 h, environ 9 par jour, 29 clients distincts, 19 codes recette (`BF250`, `BF300`, `BF350`, `BP…`, `M…`, `…RET`, `SABLE`) ;
  `ORDHT` / `ORDTTC` à 0 pour les professionnels (prix Odoo), renseignés seulement pour `DIS99999 PARTICULIER BORNE` (payé CB à la borne).

## Import automatique (22/10/2026)

Case « Import automatique dans Odoo » sur la page, **désactivée par défaut** (paramètre système Odoo `maquignon.borne_import_auto`, `1` = actif).
Activée : à l'arrivée des fichiers, les prises dont le client (code DIS) et l'article (code recette) sont reconnus, sans doublon ni anomalie,
deviennent aussitôt des commandes Distri Béton confirmées (`x_valide_par` = « import automatique ») ; les autres restent « à valider » sur
la page. Désactivée : tout passe par la page. Le bouton « Installer l'agent sur ce PC » de la page télécharge un installateur prérempli
(clé, relais, mot de passe FTP lu dans le paramètre `maquignon.borne_ftp_mdp`, chiffré DPAPI sur le PC).

