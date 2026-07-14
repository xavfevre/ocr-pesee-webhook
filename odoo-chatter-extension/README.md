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

## Domaines couverts

L'extension fonctionne sur **tous les sites Odoo**, quel que soit le
domaine : `*.odoo.com`, `*.odoo.sh`, domaines personnalisés
(`erp.mondomaine.fr`, etc.). Elle est déclarée sur tous les sites mais
**détecte automatiquement** si la page est un Odoo (présence du web
client ou des assets `/web/assets/`) avant de s'activer ; sur les autres
sites elle ne fait rien et s'endort au bout de quelques secondes.

C'est pourquoi Chrome affiche à l'installation l'avertissement « peut
lire et modifier les données sur tous les sites » : c'est le prix de la
compatibilité avec les domaines personnalisés, l'extension ne lit ni
n'envoie rien nulle part (tout le code est dans ce dossier, lisible).

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

## Monétisation (Premium)

La **pleine largeur** est une fonction **Premium** (achat unique ou essai
gratuit de 7 jours). La gestion du chatter reste gratuite. Les paiements
passent par [ExtensionPay](https://extensionpay.com) (Stripe).

### Mise en route (une seule fois)

1. Créer un compte sur <https://extensionpay.com> (gratuit).
2. **Register a new extension** avec l'identifiant exact :
   `odoo-chatter-manager` (sinon, modifier `OCX_EXTPAY_ID` dans
   `config.js` pour qu'il corresponde).
3. Connecter son compte **Stripe** (création possible dans la foulée) et
   fixer le prix (paiement unique ou abonnement, au choix — le prix se
   règle côté ExtensionPay, rien à changer dans le code).
4. Recharger l'extension. Tant que l'extension n'est pas enregistrée sur
   ExtensionPay, le statut Premium est simplement « non payé » (aucune
   erreur bloquante).

### Comment ça marche

- `background.js` interroge ExtensionPay (`extpay.getUser()`) et met le
  statut en cache local (utilisable hors ligne).
- Le script de contenu n'applique la pleine largeur que si le statut est
  Premium (payé, ou essai de 7 jours en cours — durée définie dans
  `config.js`, côté extension).
- Le popup affiche un encart d'achat / d'essai / de reconnexion quand la
  fonction est verrouillée, et les jours d'essai restants pendant l'essai.
- Après paiement, ExtensionPay notifie l'extension (`extpay.onPaid`) et la
  pleine largeur se débloque immédiatement dans tous les onglets.

ExtensionPay prélève ~5 % + les frais Stripe. L'utilisateur peut
retrouver son achat sur un autre poste via « Déjà acheté ? Se
reconnecter » (lien magique par e-mail).

## Fichiers

| Fichier         | Rôle                                                    |
| --------------- | ------------------------------------------------------- |
| `manifest.json` | Déclaration de l'extension (MV3)                        |
| `content.js`    | Applique les réglages, bouton flottant, messages        |
| `content.css`   | Toutes les règles de mise en page (pleine largeur, etc.)|
| `background.js` | Raccourcis clavier + statut Premium (ExtensionPay)      |
| `popup.html/js/css` | Interface de réglages + encart Premium              |
| `config.js`     | Identifiant ExtensionPay + durée de l'essai gratuit     |
| `ExtPay.js`     | Librairie officielle ExtensionPay (non modifiée)        |
