# Fiche Chrome Web Store — textes à coller

## Onglet « Fiche du store »

**Nom** : Odoo Chatter Manager — pleine largeur

**Résumé** (132 caractères max) :

> Odoo en pleine largeur et chatter maîtrisé : à droite, en bas ou masqué. Fini les marges vides sur vos fiches Odoo.

**Description détaillée** :

> Odoo Chatter Manager améliore l'affichage des fiches Odoo (devis, factures, commandes, projets…) :
>
> ✅ GRATUIT — Gestion du chatter (fil de messages) :
> • À droite (défaut Odoo) avec largeur réglable de 20 à 50 %
> • En bas, sous la fiche, sur toute la largeur
> • Masqué complètement
> • Bouton flottant pour basculer en un clic
> • Raccourcis clavier : Alt+Maj+C (chatter), Alt+Maj+F (pleine largeur)
>
> 💎 PREMIUM (achat unique, essai gratuit 7 jours) — Pleine largeur :
> • Supprime les grandes marges vides des formulaires Odoo
> • Votre contenu occupe enfin tout l'écran
>
> Fonctionne sur toutes les bases Odoo : Odoo Online (*.odoo.com), Odoo.sh et domaines personnalisés. L'extension détecte automatiquement les sites Odoo et reste inactive partout ailleurs.
>
> 100 % CSS : l'extension ne modifie que la mise en page, jamais vos données Odoo. Aucune donnée collectée.
>
> ---
>
> Make Odoo full-width and take control of the chatter: side (adjustable width), below the sheet, or hidden. Works on Odoo Online, Odoo.sh and custom domains. Free chatter management; full-width is a one-time Premium purchase with a 7-day free trial. Pure CSS, no data collected.

**Catégorie** : Outils de développement → non ; choisir **Productivité / Workflow & Planning** (ou « Outils »)

**Langue** : Français

## Onglet « Confidentialité »

**Objectif unique (single purpose)** :

> Améliorer l'affichage des vues formulaire d'Odoo : contenu en pleine largeur et contrôle de la position du chatter (fil de messages).

**Justification de la permission `storage`** :

> Enregistre les préférences d'affichage de l'utilisateur (pleine largeur activée ou non, position et largeur du chatter, bouton flottant) via chrome.storage.sync afin de les retrouver sur tous ses postes.

**Justification des host permissions (`https://*/*`)** :

> L'extension s'adresse aux utilisateurs du logiciel de gestion Odoo. Chaque entreprise héberge Odoo sur son propre nom de domaine (sous-domaines *.odoo.com, *.odoo.sh, ou domaine personnalisé comme erp.entreprise.fr), qu'il est impossible d'énumérer à l'avance. Le script de contenu vérifie au chargement que la page est un site Odoo (présence du web client Odoo) et se désactive immédiatement sur tout autre site. L'extension n'applique que des styles CSS ; elle ne lit ni ne transmet aucun contenu de page.

**Justification du code distant** :

> Aucun code distant : toutes les bibliothèques (ExtPay.js) sont embarquées dans le paquet.

**Utilisation des données** : cocher « Ne collecte aucune donnée utilisateur ».

**URL de la politique de confidentialité** : héberger `privacy.html` (voir README) et coller l'URL ici. Elle se règle dans l'onglet « Confidentialité » de la fiche ET dans Compte → « Politique de confidentialité ».

## Captures d'écran (1280×800, 1 à 5)

À faire sur ta base Odoo (flouter les données clients réelles !) :
1. Fiche AVANT/APRÈS pleine largeur (côte à côte ou annotée)
2. Le popup de réglages ouvert sur une fiche
3. Chatter en bas sur toute la largeur
4. Chatter masqué, fiche plein écran

## Processus

1. « Nouvel élément » → téléverser `odoo-chatter-manager-store.zip`
2. Remplir les onglets avec les textes ci-dessus + captures
3. « Envoyer pour examen ». Avec l'accès large aux sites, l'examen peut
   prendre de quelques jours à 2-3 semaines (examen approfondi). C'est
   normal, ne pas re-soumettre entre-temps.
4. Une fois publiée : installer l'extension DEPUIS le store → ExtensionPay
   passe automatiquement en paiements réels (vérifier que Stripe est en
   mode live).
