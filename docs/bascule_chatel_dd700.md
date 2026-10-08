# Pont-bascule Chatel'Granulats : indicateur Bilanciai DD700 (relevé du 08/10/2026)

Matériel : indicateur **Bilanciai DD700** (plaque Minebea Intec type CP0522, n° 230110-MI37-01), pont 48 000 kg,
mini 500 kg, échelon 20 kg, classe III. Arrière : COM1 RS232 DB9, COM2 RS232/422/485 (DB9 + bornier 8 points),
USB device + USB host. Câble USB-série **Prolific** fourni par le prestataire de pesage (carte sur l'appareil),
branché sur le DB9 ; il était relié auparavant à un PC avec le logiciel dédié du prestataire.

## Liaison vérifiée depuis le portable de Xavier (COM3, 9600 bauds, 8 bits, sans parité, 1 stop)

Protocole « commandes à distance » Bilanciai : commande ASCII terminée par **CR** (0x0D), réponse terminée par CR LF.
Commande inconnue → `??`. Commande sans donnée acceptée → `OK`.

| Commande | Réponse observée | Sens |
|---|---|---|
| `XB` | `       20 kg B` | poids brut (9 caractères cadrés à droite, unité, `B`) |
| `XN` | `       20 kg NT` | poids net (`NT`) |
| `XT` | `        0 kg TR` | tare (`TR` = tare mesurée, `TE` = tare saisie) |
| `XM` | `Max=    48000 kg` | portée |
| `XZ` | `3201` | état (4 chiffres hexa, même champ que la chaîne étendue) |
| `XS` | `30` | état, à documenter |
| `XC` | ` 10837,2` | compteur, à documenter |
| `EX` | `OK` | arrête l'émission cyclique |
| `SX` | `OK` puis flux | démarre l'émission cyclique de la chaîne étendue (3 fois/s) |

Chaîne étendue (mode cyclique) : `$       20         0 kg 3201` = `$`, net sur 9, espace, tare sur 9, espace, unité,
espace, état 4 hexa, CR LF (disposition identique au manuel D70). Au repos l'indicateur est en mode **sur demande**
(aucune émission) ; mon test a laissé l'indicateur dans cet état (EX envoyé après SX).

Sources : manuel DINET DD700 (EX/SX, archives par `&L`), manuels D70 / DD1010 (XB, XN, XT, chaîne étendue, 10 ms
minimum entre réponse et commande suivante, en cyclique les commandes sont ignorées tant que EX n'est pas envoyé).

## Piste d'intégration Odoo (à valider avec Xavier)

Odoo Online ne lit pas un port série : programme local (Python, service Windows) sur le PC de caisse, câble Prolific,
qui interroge l'indicateur (`XN`/`XB`) et pousse chaque pesée vers le relais Render (`/odoo/...`), qui crée dans Odoo
une commande prête (client ou immatriculation, article, net en tonnes) réglée ensuite dans la caisse (bouton Commandes).
Questions ouvertes : qui gère la logique pesée 1 / pesée 2 par véhicule (l'indicateur avec son clavier, ou le programme),
déclencheur (bouton côté PC ou validation sur l'indicateur), article et client à rattacher, et la box IoT Odoo écartée
(balance de comptoir en kg, pas de vente à la tonne).

## Page web /bascule (relais Render, 08/10/2026 soir)

- URL : `https://ocr-pesee-webhook.onrender.com/bascule/?site=chatel&k=<clé>` ; la clé est `maquignon.bascule_key`
  (paramètre système Odoo, créée par `odoo-scan-page/bascule_20261008/bascule_setup.py apply`) et se mémorise dans le
  navigateur après la première ouverture. Chrome ou Edge obligatoires (Web Serial). « Connecter la bascule » = choisir le
  câble Prolific dans la liste de Chrome, une fois ; ensuite la page se reconnecte seule.
- Services (`bascule_web.py`, blueprint `/bascule`) : `api/config` (société, imprimante, en-tête, articles à la tonne
  vendables en caisse), `api/clients?q=` (recherche de contacts), `api/pesees` (en attente + du jour), `api/pesee`
  (POST : p1, p2, simple, annuler, imprime, note). Multi-sites : bloc `SITES` dans `bascule_web.py` + séquence
  `x_pesee.<site>` dans Odoo + en-tête de ticket.
- Odoo : modèle manuel `x_pesee` (2716) « Pesée pont-bascule », vues liste/formulaire, menu Logistiques > Pesées
  pont-bascule (1069), numéros `CHA-AAAA-00001`. Zéro ligne de code.
- Page (`bascule_page.html`) : poids en direct (XB toutes les 600 ms, stable = 3 lectures identiques), sens
  vente / réception / pesée simple, immatriculation, client (autocomplétion Odoo), produit (liste ou texte libre),
  note ; « Pesée 1 » ouvre une pesée, le camion apparaît dans « en attente », « Pesée 2 » termine, net = |P2 - P1|,
  ticket ePOS sur l'Epson du site (`https://IP/cgi-bin/epos/service.cgi`, certificat à accepter une fois par navigateur),
  réimpression depuis la liste du jour. Réglages par poste dans le navigateur : nom du poste, IP imprimante, clé.
