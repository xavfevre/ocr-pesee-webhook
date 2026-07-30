# Abonnement — « Modules supplémentaires : Maintenance (par 100 lignes) »

**Mise à jour 30/07/2026** : bannière à **32 unités** pour 18 incluses.
Le comptage a cette fois été reproduit avec **l'outil officiel d'Odoo**
(`odoo/tools/cloc.py`, celui qu'utilise leur facturation) : notre
reproduction donne **31,5 unités**, ce qui colle à la bannière.

## Ce qu'Odoo compte réellement (et ce qu'il ne compte pas)

Le diagnostic du 29/07 était faux : les lignes des **vues** (Studio ou
créées par RPC, y compris toutes nos pages tablette/web) **ne comptent pas**.
L'outil cloc facture, par tranche de 100 lignes de code effectives
(commentaires et lignes vides exclus) :

1. **Toute action serveur en Python sans identifiant de module** — c'est-à-dire
   toutes celles créées à la main ou par RPC. Retirer l'étiquette
   `studio_customization` (le « ménage » du 29/07) ne les sort pas du
   comptage : elles passent simplement du compartiment `studio_customization`
   au compartiment `odoo/studio`, facturé pareil. D'où le « toujours pas ».
2. **Les champs calculés manuels** (code Python du calcul).
3. Les vues qweb et fichiers js/css **uniquement s'ils appartiennent à un
   module importé** — pas notre cas.

## État au 30/07/2026 (après ménage)

| Poste | Quantité | Lignes |
|---|---|---|
| Actions serveur (automatisations, boutons, pages tablette/RH) | 101 | 2 797 |
| Champs calculés manuels (`x_studio_*`) | 31 | 280 |
| **Total** | | **3 077 ≈ 30,8 unités** |

Ménage effectué ce jour : suppression de 5 actions mortes (74 lignes) —
« Relocaliser palette » (remplacée), 2 actions de test horaires oubliées,
2 patchs temporaires de cron. Code sauvegardé dans
`actions_supprimees_20260730.py.txt` avant suppression.
Toutes les autres actions sont référencées (automatisation active, cron,
bouton/menu contextuel, ou appel depuis les pages tablette/RH) — vérifié
action par action.

## Pourquoi le compteur monte

Chaque nouvelle fonctionnalité tablette/RH ajoute des actions serveur
(la suite heures/congés/horaires de juillet ≈ 260 lignes ≈ 2,6 unités).
C'est le prix normal du modèle : la logique métier vit dans Odoo.

## Options pour la suite

- **Réduction réaliste** : déplacer les 2 gros exports comptables
  (« Export journal pour Sage » 135 l. + « Export journal compta extérieure »
  130 l.) vers l'application Flask (comme l'export paie) — l'action Odoo
  devient un simple lien. Gain ≈ 2,5 unités. Au-delà, il faudrait
  réécrire/compacter des automatisations en production, risqué pour un gain
  faible.
- **Ajustement de l'abonnement** : il restera ~28 unités ≈ 10 tranches
  au-dessus des 18 incluses — c'est l'objet de la proposition de Pauline
  (Odoo). Le volume de personnalisation actuel ne descendra pas sous 18
  sans dé-fonctionnaliser la base.

## Vérification

Script de reproduction du comptage : scratchpad `_cloc_repro.py`
(recalcule le total exact façon cloc via RPC — à relancer après tout
ajout/suppression d'action pour suivre le compteur sans attendre le ping
de la bannière, qui se rafraîchit sous 24–48 h).
