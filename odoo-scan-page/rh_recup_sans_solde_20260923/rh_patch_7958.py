# -*- coding: utf-8 -*-
"""Planning RH (vue 7958) : type « sans solde », marqueurs récup / sans solde partiels.
  python rh_patch_7958.py [test|prod]"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = 'vue_7958_planning_rh.xml'
s = io.open(SRC, encoding='utf-8').read()
n0 = len(s)


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)


rep("      .d-rec{background:#7dd3fc;color:#0c4a6e;}\n", "      .d-rec{background:#7dd3fc;color:#0c4a6e;}\n      .d-ss{background:#fecaca;color:#7f1d1d;}\n")
rep("      .pr-typ .b-recup{background:#7dd3fc;color:#0c4a6e;}\n", "      .pr-typ .b-recup{background:#7dd3fc;color:#0c4a6e;}\n      .pr-typ .b-ss{background:#fecaca;color:#7f1d1d;}\n")
rep("""{'travail': 'd-t', 'cp': 'd-cp', 'maladie': 'd-mal', 'ferie': 'd-fer', 'absence': 'd-abs', 'recup': 'd-rec', 'repos': 'd-rep'}""",
    """{'travail': 'd-t', 'cp': 'd-cp', 'maladie': 'd-mal', 'ferie': 'd-fer', 'absence': 'd-abs', 'recup': 'd-rec', 'sans_solde': 'd-ss', 'repos': 'd-rep'}""")
rep("""                  <t t-elif="s and s.x_type == 'travail'"><t t-esc="('%g' % round(s.x_heures, 1))"/></t>""",
    """                  <t t-elif="s and s.x_type == 'travail'"><t t-esc="('%g' % round(s.x_heures, 1))"/><sup t-if="s.x_h_recup" style="color:#0c4a6e;" title="heures de récup prises">R</sup><sup t-if="s.x_h_sans_solde" style="color:#7f1d1d;" title="heures sans solde">S</sup></t>""")
rep("""                  <t t-elif="s and s.x_type == 'recup'">R</t>""",
    """                  <t t-elif="s and s.x_type == 'recup'">R</t>
                  <t t-elif="s and s.x_type == 'sans_solde'">SS</t>""")
rep("""<span class="d-abs">Absence</span><span class="d-rec">Récup</span><span class="d-off">jour non travaillé</span>""",
    """<span class="d-abs">Absence</span><span class="d-rec">Récup</span><span class="d-ss">Sans solde</span><span class="d-off">jour non travaillé</span>
          <span class="d-t">8,5<sup>R</sup> / <sup>S</sup> = jour travaillé avec des heures de récup prises / sans solde (survoler pour le détail)</span>""")
rep("""              <button type="button" class="b-recup" data-t="recup">Récup</button>""",
    """              <button type="button" class="b-recup" data-t="recup">Récup</button>
              <button type="button" class="b-ss" data-t="sans_solde">Sans solde</button>""")
# infobulle : note du jour (déjà) + récup / sans solde en heures
rep("""t-att-title="e.name + ' ' + dd.strftime('%d/%m') + ((' — ' + s.x_note) if s and s.x_note else '')\"""",
    """t-att-title="e.name + ' ' + dd.strftime('%d/%m') + ((' — ' + s.x_note) if s and s.x_note else '') + ((' — récup prise %g h' % s.x_h_recup) if s and s.x_h_recup else '') + ((' — sans solde %g h' % s.x_h_sans_solde) if s and s.x_h_sans_solde else '')\"""")
import xml.dom.minidom
xml.dom.minidom.parseString(s.encode('utf-8'))
io.open('vue_7958_NEW.xml', 'w', encoding='utf-8', newline='\n').write(s)
print('vue_7958_NEW.xml :', n0, '->', len(s), 'chars, XML OK')
mode = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
if mode in ('test', 'prod'):
    import ssl, xmlrpc.client
    U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
    arch = s.replace('https://ocr-pesee-webhook.onrender.com/heures/rpc', 'http://127.0.0.1:5055/heures/rpc') if mode == 'test' else s
    us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    m.execute_kw(D, uid, p, 'ir.ui.view', 'write', [[7958], {'arch_db': arch}])
    print(mode, ': vue 7958 écrite,', len(m.execute_kw(D, uid, p, 'ir.ui.view', 'read', [[7958], ['arch_db']])[0]['arch_db']), 'chars')
