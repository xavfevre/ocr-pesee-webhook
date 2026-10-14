# Scanner -> fiche véhicule Odoo (14/10/2026)

Demande de Xavier : « dans le module véhicule, Isabelle doit scanner directement des documents dans chaque véhicule »
(scanner Brother DS-740D en USB sur son PC, Odoo Online sans module custom).

## Fonctionnement

1. Fiche véhicule Odoo -> menu Action -> **📎 Scanner un document** : ouvre la page du relais
   `https://ocr-pesee-webhook.onrender.com/scan-vehicule/?veh=<id>&k=<clé>` sur ce véhicule (nouvel onglet).
   La page affiche le véhicule, le type de document (Carte grise, Assurance, Contrôle technique, Facture, Entretien,
   Document) et signale toutes les 20 s au relais « sur ce poste, les scans vont à ce véhicule » (paramètre
   `maquignon.scan_cible_<poste>`, valable 3 h, effacé à la fermeture de la page).
2. Isabelle scanne : iPrint&Scan enregistre le PDF dans `Documents\Scan Odoo`.
3. Le veilleur (`poste/scan_odoo_veilleur.ps1`, lancé à l'ouverture de session) envoie le fichier à
   `api/upload` et le déplace dans `Scan Odoo\Envoyés`.
4. Le relais crée la pièce jointe sur le véhicule (`<Type>_<immat>_<date>.pdf`) + une note dans le fil ;
   Documents > Fleet la reprend automatiquement (mixin documents_fleet). Sans véhicule affiché, le fichier est gardé
   « à classer » (pièce jointe fleet.vehicle, res_id 0) et la page propose « Classer dans … ».
5. Sur la page : liste des documents du véhicule (Ouvrir dans Odoo), **Retirer** pour un scan mal classé
   (supprime la pièce jointe et la note ; la copie reste dans Envoyés).

## Fichiers

- `scan_vehicule.py` + `scan_vehicule_page.html` (racine du dépôt) : blueprint Flask `/scan-vehicule`.
- `scan_vehicule_setup.py dry|apply|etat|retour` : clé `maquignon.scan_key` + action serveur (1 ligne de code).
- `poste/installer.ps1 -Cle <clé> [-Poste isabelle]` : installe le veilleur sur le PC (raccourci Démarrage, config.json).
- Procédure : `docs/build_procedure_scan_vehicule.py` -> `Desktop/Maquignon/Procedure_scanner_vehicule_2026-10-14.pdf`.
