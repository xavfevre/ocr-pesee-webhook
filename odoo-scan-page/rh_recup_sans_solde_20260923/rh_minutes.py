# -*- coding: utf-8 -*-
"""Récup / sans solde à la minute (plus d'arrondi au quart d'heure) : « Tout en récup » couvre exactement le manque."""
import io, sys, py_compile
sys.stdout.reconfigure(encoding='utf-8')
def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new, n in pairs:
        assert s.count(old) == n, (path, s.count(old), n, old[:80]); s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s); print(path, ': OK')
patch('ocr/heures_actions.py', [
    ('''def _quart(v):
    """Arrondi au quart d'heure."""
    return round(float(v or 0.0) * 4) / 4.0''',
     '''def _quart(v):
    """Arrondi à la minute (les horaires sont saisis à la minute : 13:20…), pour que
    « tout le manque en récup » tombe juste."""
    return round(float(v or 0.0) * 60) / 60.0''', 1),
])
py_compile.compile('ocr/heures_actions.py', doraise=True)
patch('rh_patch_7956.py', [
    ("  function q4(v){ return Math.round(v*4)/4; }", "  function q4(v){ return Math.round(v*60)/60; }   /* à la minute, comme les horaires */", 1),
    ('<input type="number" data-f="h_recup" step="0.25" min="0" max="12"', '<input type="number" data-f="h_recup" step="any" min="0" max="12"', 1),
    ('<input type="number" data-f="h_ss" step="0.25" min="0" max="12"', '<input type="number" data-f="h_ss" step="any" min="0" max="12"', 1),
])
patch('rh_page_fiche.py', [
    ('<input type="number" data-f="h_recup" step="0.25" min="0" max="12"', '<input type="number" data-f="h_recup" step="any" min="0" max="12"', 1),
    ('<input type="number" data-f="h_ss" step="0.25" min="0" max="12"', '<input type="number" data-f="h_ss" step="any" min="0" max="12"', 1),
])
patch('rh_patch_7957.py', [
    ('<input type="number" id="ha-hr" step="0.25" min="0" max="12"', '<input type="number" id="ha-hr" step="any" min="0" max="12"', 1),
    ('<input type="number" id="ha-hs" step="0.25" min="0" max="12"', '<input type="number" id="ha-hs" step="any" min="0" max="12"', 1),
])
