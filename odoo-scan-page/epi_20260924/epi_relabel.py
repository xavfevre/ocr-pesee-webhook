# -*- coding: utf-8 -*-
"""Page EPI : le code-barres est tapé au clavier (pas de douchette) — libellés, message, aide."""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'epi_page.py'
s = io.open(p, encoding='utf-8').read()
pairs = [
    ("""                <label for="ep-scan">📷 Scan</label>
                <input type="text" id="ep-scan" class="ep-scan" data-cible="ep-prod" placeholder="scannez le code-barres de l'EPI (douchette), ou choisissez-le ci-dessous" autocomplete="off"/>""",
     """                <label for="ep-scan">Code-barres</label>
                <input type="text" id="ep-scan" class="ep-scan" data-cible="ep-prod" placeholder="tapez le code-barres de l'EPI puis Entrée (ou choisissez-le ci-dessous)" autocomplete="off" inputmode="numeric"/>"""),
    ("""                <label for="ep-rec-scan">📷 Scan</label>
                <input type="text" id="ep-rec-scan" class="ep-scan" data-cible="ep-rec-prod" placeholder="scannez le code-barres de l'EPI reçu" autocomplete="off"/>""",
     """                <label for="ep-rec-scan">Code-barres</label>
                <input type="text" id="ep-rec-scan" class="ep-scan" data-cible="ep-rec-prod" placeholder="tapez le code-barres de l'EPI reçu puis Entrée" autocomplete="off" inputmode="numeric"/>"""),
    ("""  /* douchette : le code-barres scanné (suivi d'Entrée) sélectionne l'EPI dans la liste ; inconnu = message */""",
     """  /* code-barres tapé (ou scanné) puis Entrée : sélectionne l'EPI dans la liste ; inconnu = message */"""),
    ("""Nouvel EPI à suivre ? Dans Odoo, créer l'article dans la catégorie <b>EPI</b> avec « Suivre le stock » coché (tailles en variantes) : il apparaît ici aussitôt.""",
     """Nouvel EPI à suivre ? Dans Odoo, créer l'article dans la catégorie <b>EPI</b> avec « Suivre l'inventaire » coché et son code-barres tapé dans le champ Code-barres (tailles en variantes : un code par taille). Il apparaît ici aussitôt."""),
]
for old, new in pairs:
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)
# message « code inconnu » : réécrit par expression régulière (la ligne contient des séquences \n et \')
rx = re.compile(r"alert\('Code-barres ' \+ code \+ ' inconnu\.[^;]*;")
assert len(rx.findall(s)) == 1
NEW_ALERT = "alert('Code-barres ' + code + ' inconnu.' + String.fromCharCode(10) + 'Vérifiez la saisie, ou enregistrez ce code sur la fiche de l' + String.fromCharCode(39) + 'article dans Odoo (champ Code-barres ; pour un EPI à tailles, sur chaque variante). Sinon choisissez l' + String.fromCharCode(39) + 'EPI dans la liste.');"
s = rx.sub(lambda m_: NEW_ALERT, s)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('libellés code-barres (saisie au clavier) : OK')
