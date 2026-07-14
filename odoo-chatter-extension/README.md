# Odoo Chatter Manager

Extension Chrome (Manifest V3) pour **Odoo Online** :

- **Contenu en pleine largeur** : supprime la limite de largeur (`max-width`)
  des fiches (formulaires), qui laisse normalement de grandes marges vides.
- **Gestion du chatter** (fil de messages / notes / activités) :
  - **À droite** (comportement Odoo par défaut), avec **largeur réglable**
    (20 à 50 %) ;
  - **En bas**, sous la fiche, sur toute la largeur ;
  - **Masqué** complètement.
- **Bouton flottant** en bas à droite des fiches pour basculer la position du
  chatter en un clic (désactivable).
- **Raccourcis clavier** :
  - `Alt + Maj + C` : basculer le chatter (côté → en bas → masqué) ;
  - `Alt + Maj + F` : activer/désactiver la pleine largeur.

Les réglages sont synchronisés via le compte Chrome (`chrome.storage.sync`)
et s'appliquent immédiatement à tous les onglets Odoo ouverts.

## Installation (mode développeur)

1. Télécharger / cloner ce dossier `odoo-chatter-extension` sur le poste.
2. Ouvrir Chrome (ou Edge) → `chrome://extensions`.
3. Activer le **Mode développeur** (interrupteur en haut à droite).
4. Cliquer **Charger l'extension non empaquetée** et sélectionner le dossier
   `odoo-chatter-extension`.
5. Ouvrir Odoo → l'icône de l'extension permet de régler les options.

## Domaine personnalisé

L'extension est active sur `https://*.odoo.com/*` et `strate-design.fr`.
Pour ajouter un autre domaine personnalisé (ex. `erp.mondomaine.fr`),
complétez les listes `host_permissions` **et** `matches` dans
`manifest.json` avec `"https://erp.mondomaine.fr/*"`, puis rechargez
l'extension dans `chrome://extensions` (bouton ↻).

## Fonctionnement

Le script de contenu pose des attributs sur `<html>`
(`data-ocx-fullwidth`, `data-ocx-chatter`) et une variable CSS
(`--ocx-chatter-width`). Toute la mise en page est faite en CSS pur
(`content.css`), sans toucher au JavaScript d'Odoo — donc sans risque pour
les données.

Les sélecteurs couvrent les classes des versions récentes d'Odoo
(`.o-mail-Form-chatter`, Odoo 16.3+) et des anciennes
(`.o_FormRenderer_chatterContainer`). Odoo Online étant toujours sur la
dernière version, si une mise à jour d'Odoo change les noms de classes, il
suffit d'ajuster `content.css`.

## Fichiers

| Fichier         | Rôle                                                    |
| --------------- | ------------------------------------------------------- |
| `manifest.json` | Déclaration de l'extension (MV3)                        |
| `content.js`    | Applique les réglages, bouton flottant, messages        |
| `content.css`   | Toutes les règles de mise en page (pleine largeur, etc.)|
| `background.js` | Relaie les raccourcis clavier vers l'onglet actif       |
| `popup.html/js/css` | Interface de réglages                               |
