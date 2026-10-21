# Pont-bascule SARL Maquignon (Usseau) : indicateur Bilanciai D400 (relevé du 21/10/2026)

Matériel : indicateur **Bilanciai D400** (n° 71897, maintenance PNA 05 46 41 31 37), pont 48 000 kg, mini 500 kg,
échelon 20 kg. COM1 RS232 DB9 à l'arrière, câble USB-série Prolific (COM3 sur le portable de Xavier).

## Protocole (sonde `Desktop/Maquignon/bascule_maquignon_sonde.ps1`, 9600 bauds, 8 bits, sans parité, 1 stop)

Mêmes « commandes à distance » Bilanciai que le DD700 de Chatel (commande + CR, réponse + CR LF, `??` si inconnue) :

| Commande | Réponse observée | Sens |
|---|---|---|
| `XB` | `      -20 kg B` | poids brut (9 caractères cadrés à droite, signe possible) |
| `XN` | `      -20 kg NT` | poids net |
| `XT` | `        0 kg TR` | tare |
| `XZ` | `B201` | état (4 hexa) |
| `XM` | `Max=    48000 kg` | portée |
| `XS` | `70` | état, non documenté |
| `EX` | `OK` | arrêt du flux cyclique |

Aucune émission spontanée au repos (mode sur demande). Commandes Mettler (`S`, `SI`), `READ`, `P`, ENQ : `??`.

## Page relais

`https://ocr-pesee-webhook.onrender.com/bascule/?site=maquignon&k=<maquignon.bascule_key>` — menu Odoo Ventes > Pont-bascule
Maquignon (act_url 2152, menu 1075). Configuration `SITES['maquignon']` dans `bascule_web.py` : société 1, séquence
`x_pesee.maquignon` (MAQ-AAAA-00001, ir.sequence 329), en-tête ticket Usseau, protocole `bilanciai_dd700`, pas de point de vente
(destination « ticket de caisse » masquée), pas d'imprimante ePOS (ticket non imprimé, adresse réglable par poste), articles
= vendables à la tonne de la société ou communs, hors contributions.
