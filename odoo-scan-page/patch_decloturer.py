# -*- coding: utf-8 -*-
"""Bouton « Déclôturer » sur le poste de scan : patch de web_actions.py (mode decloturer), de la vue 7890
(scan_view_7890.AFTER.xml, JS inline échappé) et de la copie lisible scan_view_7890.js."""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr')
# ---------- Render
p = os.path.join(R, 'web_actions.py'); s = io.open(p, encoding='utf-8').read()
DEJA = 'def _scan_decloturer' in s
FN = '''

def _scan_decloturer(call, colis_id):
    """Rouvre une palette clôturée depuis le poste de scan : contenu modifiable, à clôturer de nouveau ensuite
    (nouveau bon de colisage) ; l'opérateur la retrouve en palette active, le bureau est prévenu."""
    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, '⚠️ Aucune palette active à déclôturer', False)
    if not colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], 'ℹ️ %s n’est pas clôturée' % colis['name'], False)
    call('stock.package', 'write', [colis['id']], {'x_studio_cloturee': False})
    if colis['x_operateur_id']:
        _sur(lambda: call('hr.employee', 'write', [colis['x_operateur_id'][0]], {'x_palette_scan_id': colis['id']}))
    _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                      body='🔓 Palette déclôturée depuis le poste de scan (elle était clôturée → %s)' % (colis['x_studio_zone'] or '?')))
    dest = _param(call, 'maquignon.palettes_alerte_email', '')
    if dest:
        try:
            _mail_bureau(call, 'Palette %s déclôturée' % colis['name'], dest,
                         '<p>La palette <b>%s</b>%s a été <b>déclôturée</b> depuis le poste de scan%s.</p>'
                         '<p>Son bon de colisage n’est plus valable : un nouveau sera émis à la prochaine clôture.</p>'
                         % (colis['name'], (' de ' + colis['x_operateur_id'][1]) if colis['x_operateur_id'] else '',
                            (' (elle était → ' + colis['x_studio_zone'] + ')') if colis['x_studio_zone'] else ''))
        except Exception:  # noqa: BLE001
            pass
    return _scan_etat(call, colis['id'], '🔓 %s déclôturée — modifiez son contenu, puis clôturez-la à nouveau (nouveau bon de colisage)' % colis['name'], True)
'''
anchor = "\n\n# ─── 2103 · Alerte hebdo palettes (bureau) ─"
assert anchor in s
s = s.replace(anchor, FN + anchor, 1)
old = "    if mode == 'cloturer':\n        return _scan_cloturer(call, colis_id, (ctx.get('zone') or '').strip())\n"
assert old in s
s = s.replace(old, old + "    if mode == 'decloturer':\n        return _scan_decloturer(call, colis_id)\n", 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('web_actions.py : mode decloturer ajouté')
# ---------- vue 7890 (XML avec JS échappé) et JS lisible
BTN = '<button id="btn-colis-open" style="display:none;margin-top:10px;margin-left:8px;border:none;border-radius:10px;padding:10px 18px;font-size:15px;font-weight:800;cursor:pointer;background:#b45309;color:#fff;">🔓 Déclôturer</button>'
JS_SHOW = "    var bo = document.getElementById('btn-colis-open'); if(bo){ bo.style.display = ferme ? '' : 'none'; }\n"
JS_CLICK = ("  document.getElementById('btn-colis-open').addEventListener('click', function(){\n"
            "    if(!colisActif){ setRes('⚠️ Aucune palette active'); beep(false); return; }\n"
            "    if(!confirm('Déclôturer la palette ' + colisNom + ' ?\\nElle redevient modifiable : il faudra la clôturer à nouveau (nouveau bon de colisage, le bureau est prévenu).')){ return; }\n"
            "    act('decloturer').then(function(){ input.focus(); });\n"
            "  });\n")
for fn, escaped in (('odoo-scan-page/scan_view_7890.AFTER.xml', True), ('odoo-scan-page/scan_view_7890.js', False)):
    p = os.path.join(R, fn); s = io.open(p, encoding='utf-8').read()
    assert 'btn-colis-open' not in s
    esc = (lambda t: t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')) if escaped else (lambda t: t)
    if escaped:
        a = '🖨 Bon de colisage</button>'
        assert s.count(a) == 1
        s = s.replace(a, a + BTN, 1)
    show_anchor = esc("    var bp = document.getElementById('btn-colis-print'); if(bp){ bp.textContent = ferme ? '🖨 Réimprimer le bon de colisage' : '🖨 Bon de colisage'; }\n")
    assert s.count(show_anchor) == 1, fn
    s = s.replace(show_anchor, show_anchor + esc(JS_SHOW), 1)
    click_anchor = esc("  document.getElementById('btn-colis-nav').addEventListener('click', openNav);\n")
    assert s.count(click_anchor) == 1, fn
    s = s.replace(click_anchor, esc(JS_CLICK) + click_anchor, 1)
    info = esc("if(txt.indexOf('ℹ') === 0 || txt.indexOf('↩') === 0")
    assert s.count(info) == 1, fn
    s = s.replace(info, esc("if(txt.indexOf('ℹ') === 0 || txt.indexOf('🔓') === 0 || txt.indexOf('↩') === 0"), 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    print(fn, ': bouton + JS ajoutés (%d car.)' % len(s))
