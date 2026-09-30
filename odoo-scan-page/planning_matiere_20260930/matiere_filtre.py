# -*- coding: utf-8 -*-
"""Filtre « Matière » sur les pages de planning fabrication (paramètre d'URL tp, déjà utilisé par Vue semaine / Vue mois) :
 - Board complet et sous-boards (vue 7876) et Vue opérateurs (7878) : paramètre lu, OT filtrés, barre de boutons, tp propagé
   dans tous les liens (onglets, jour préc./suiv., recherche, commandes) ;
 - Vue semaine (7875) et Vue mois (7877) : liste des matières construite d'après les OF affichés (au lieu des 6 fixes),
   couleur de la catégorie, libellé « Matière », tp propagé vers les autres onglets.
  python matiere_filtre.py dry     -> archs corrigées dans boards/<id>_new.xml, contrôle XML (lecture seule)
  python matiere_filtre.py apply   -> écrit les vues dans Odoo, copie dans le dépôt
  python matiere_filtre.py restore -> remet boards/<id>.xml (état d'avant)"""
import io, os, ssl, sys, xmlrpc.client
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
DEPOT = 'ocr/odoo-scan-page/planning_matiere_20260930'


def rep(s, old, new, n=1):
    assert s.count(old) == n, ('ancre introuvable ou multiple (%d) : %s' % (s.count(old), old[:90]))
    return s.replace(old, new)


TP = '''<t t-set="tp" t-value="(request.httprequest.args.get('tp') or '').strip().upper()"/>'''
MATFN = '''<t t-set="matfn" t-value="lambda w: ((w.production_id.x_studio_catgorie and len((w.production_id.x_studio_catgorie.display_name or '').split('/')) &gt; 1) and w.production_id.x_studio_catgorie.display_name.split('/')[1].strip().upper() or 'AUTRE')"/>'''
MATS = '''<t t-set="matcol" t-value="dict((matfn(w), ((w.production_id.x_studio_catgorie and w.production_id.x_studio_catgorie.x_studio_couleur_hex) or colors.get(matfn(w), '#9AA0A6'))) for w in ots)"/>
        <t t-set="mats" t-value="sorted(matcol, key=lambda k: (k == 'AUTRE', k))"/>'''
TPFILT = '''<t t-set="ots" t-value="ots.filtered(lambda w: matfn(w) == tp) if tp else ots"/>'''
BC_LINE = '''        <t t-set="bc" t-value="(request.httprequest.args.get('bc') or '').strip()"/>\n'''
FILT_LINE = '''        <t t-set="ots" t-value="ots.filtered(lambda w: ((w.production_id.x_studio_catgorie and len((w.production_id.x_studio_catgorie.display_name or '').split('/')) &gt; 1) and w.production_id.x_studio_catgorie.display_name.split('/')[1].strip().upper() or 'AUTRE') == tp) if tp else ots"/>\n'''


def chips(base):
    """Barre « Matière » ; base = lien de la page sans le paramètre tp."""
    return ('''<div class="d-flex gap-2 mb-2 small flex-wrap align-items-center">
          <span class="text-muted">Matière :</span>
          <a t-attf-href="%(b)s" t-attf-class="btn btn-sm py-0 {{'btn-dark' if not tp else 'btn-outline-secondary'}}">Toutes</a>
          <t t-foreach="mats" t-as="pk">
            <a t-attf-href="%(b)s&amp;tp={{pk}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if tp == pk else 'btn-outline-secondary'}}">
              <span t-attf-style="display:inline-block;width:10px;height:10px;border-radius:50%%;background:{{matcol.get(pk, '#9AA0A6')}};margin-right:4px;"/><t t-esc="pk.capitalize()"/>
            </a>
          </t>
          <a t-if="tp and tp not in mats" t-attf-href="%(b)s" class="btn btn-sm py-0 btn-dark" title="Aucune opération de cette matière ici : cliquer pour retirer le filtre"><t t-esc="tp.capitalize()"/> ✕</a>
        </div>
        ''' % {'b': base})


def fallback(base):
    return '''<a t-if="tp and tp not in mats" t-attf-href="%s" class="btn btn-sm py-0 btn-dark" title="Aucune opération de cette matière ici : cliquer pour retirer le filtre"><t t-esc="tp.capitalize()"/> ✕</a>\n''' % base


def patch_7876(s):
    s = rep(s, BC_LINE, BC_LINE + '        ' + TP + '\n        ' + MATFN + '\n')
    s = rep(s, "limit=(None if (q or bc) else 30)", "limit=(None if (q or bc or tp) else 30)")
    a = '''        <t t-set="ots" t-value="ots.filtered(lambda w: w.production_id.origin == bc) if bc else ots"/>\n'''
    s = rep(s, a, a + '        ' + MATS + '\n        ' + TPFILT + '\n')
    n = s.count('&amp;bc={{bc}}'); assert n >= 10, n
    s = s.replace('&amp;bc={{bc}}', '&amp;bc={{bc}}&amp;tp={{tp}}').replace('&amp;bc={{b}}', '&amp;bc={{b}}&amp;tp={{tp}}')
    s = rep(s, '''&amp;q={{q}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if not bc else 'btn-outline-secondary'}}">Toutes</a>''',
            '''&amp;q={{q}}&amp;tp={{tp}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if not bc else 'btn-outline-secondary'}}">Toutes</a>''')
    s = rep(s, '''<a t-attf-href="/planning-machines?board={{board}}" class="btn btn-sm btn-outline-secondary">Aujourd'hui</a>''',
            '''<a t-attf-href="/planning-machines?board={{board}}&amp;tp={{tp}}" class="btn btn-sm btn-outline-secondary">Aujourd'hui</a>''')
    s = rep(s, '''<a t-if="q" t-attf-href="/planning-machines?board={{board}}&amp;day={{day.strftime('%Y-%m-%d')}}" class="btn btn-sm btn-outline-danger"''',
            '''<a t-if="q" t-attf-href="/planning-machines?board={{board}}&amp;day={{day.strftime('%Y-%m-%d')}}&amp;tp={{tp}}" class="btn btn-sm btn-outline-danger"''')
    h = '''              <input type="hidden" name="day" t-att-value="day.strftime('%Y-%m-%d')"/>\n'''
    s = rep(s, h, h + '''              <input type="hidden" name="tp" t-att-value="tp"/>\n''')
    pa = '''        <p class="small text-muted mb-2">Une carte = une opération.'''
    s = rep(s, pa, chips("/planning-machines?board={{board}}&amp;day={{day.strftime('%Y-%m-%d')}}&amp;q={{q}}&amp;bc={{bc}}") + pa.strip())
    return s


def patch_7878(s):
    s = rep(s, BC_LINE, BC_LINE + '        ' + TP + '\n        ' + MATFN + '\n')
    a = '''<t t-set="ots" t-value="ots | done_day_ots"/>'''
    s = rep(s, a, a + '\n        ' + MATS + '\n        ' + TPFILT)
    n = s.count('&amp;bc={{bc}}'); assert n >= 8, n
    s = s.replace('&amp;bc={{bc}}', '&amp;bc={{bc}}&amp;tp={{tp}}')
    s = rep(s, '''<a href="/planning-operateurs" class="btn btn-sm btn-outline-secondary">Aujourd'hui</a>''',
            '''<a t-attf-href="/planning-operateurs?tp={{tp}}" class="btn btn-sm btn-outline-secondary">Aujourd'hui</a>''')
    s = rep(s, '''<a t-if="q" t-attf-href="/planning-operateurs?day={{day.strftime('%Y-%m-%d')}}" class="btn btn-sm btn-outline-danger"''',
            '''<a t-if="q" t-attf-href="/planning-operateurs?day={{day.strftime('%Y-%m-%d')}}&amp;tp={{tp}}" class="btn btn-sm btn-outline-danger"''')
    h = '''              <input type="hidden" name="all" t-att-value="'1' if show_all else ''"/>\n'''
    s = rep(s, h, h + '''              <input type="hidden" name="tp" t-att-value="tp"/>\n''')
    pa = '''        <p class="small text-muted mb-2">Déposer une carte sur un opérateur'''
    s = rep(s, pa, chips("/planning-operateurs?day={{day.strftime('%Y-%m-%d')}}&amp;q={{q}}&amp;bc={{bc}}&amp;all={{'1' if show_all else ''}}") + pa.strip())
    return s


def patch_semaine_mois(s, base_page):
    s = rep(s, FILT_LINE, '        ' + MATFN + '\n        ' + MATS + '\n        ' + TPFILT + '\n')
    s = rep(s, '''<span class="text-muted">Pierre :</span>''', '''<span class="text-muted">Matière :</span>''')
    s = rep(s, '''<t t-foreach="sorted(colors) + ['AUTRE']" t-as="pk">''', '''<t t-foreach="mats" t-as="pk">''')
    s = rep(s, '''background:{{colors.get(pk, '#9AA0A6')}};margin-right:4px;''', '''background:{{matcol.get(pk, '#9AA0A6')}};margin-right:4px;''')
    fin = '''<t t-esc="pk.capitalize()"/>\n            </a>\n          </t>\n'''
    s = rep(s, fin, fin + '          ' + fallback(base_page))
    for tab in ('board=complet', 'board=secondaire', 'board=primaire'):
        s = rep(s, '/planning-machines?%s&amp;q={{q}}&amp;bc={{bc}}"' % tab, '/planning-machines?%s&amp;q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}"' % tab)
    s = rep(s, '/planning-operateurs?q={{q}}&amp;bc={{bc}}"', '/planning-operateurs?q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}"')
    return s


def patch_7875(s):
    return patch_semaine_mois(s, "/planning-fabrication?week={{monday.strftime('%Y-%m-%d')}}&amp;mode={{mode}}&amp;q={{q}}&amp;bc={{bc}}")


def patch_7877(s):
    s = patch_semaine_mois(s, "/planning-mois?month={{first.strftime('%Y-%m')}}&amp;q={{q}}&amp;bc={{bc}}")
    s = rep(s, '''t-attf-href="/planning-machines?day={{d.strftime('%Y-%m-%d')}}&amp;q={{q}}&amp;bc={{bc}}" class="text-muted"''',
            '''t-attf-href="/planning-machines?day={{d.strftime('%Y-%m-%d')}}&amp;q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}" class="text-muted"''')
    return s


PATCHES = {7876: patch_7876, 7878: patch_7878, 7875: patch_7875, 7877: patch_7877}
os.makedirs('boards', exist_ok=True)
if mode == 'restore':
    for vid in PATCHES:
        avant = io.open('boards/%d.xml' % vid, encoding='utf-8').read()
        x('ir.ui.view', 'write', [vid], {'arch_base': avant})
        print(vid, 'restaurée :', x('ir.ui.view', 'read', [vid], ['arch_db'])[0]['arch_db'] == avant)
    sys.exit(0)
nouveaux = {}
for v in x('ir.ui.view', 'read', list(PATCHES), ['name', 'arch_db']):
    vid, a = v['id'], v['arch_db']
    if 'name="matfn"' in a:
        print(vid, v['name'], ': déjà corrigée'); continue
    io.open('boards/%d.xml' % vid, 'w', encoding='utf-8', newline='\n').write(a)      # état d'avant (pour restore)
    n = PATCHES[vid](a)
    ET.fromstring(n.encode('utf-8'))                                                   # XML bien formé
    io.open('boards/%d_new.xml' % vid, 'w', encoding='utf-8', newline='\n').write(n)
    nouveaux[vid] = n
    print('%s %-24s : %d -> %d car., tp dans les liens ×%d, barre Matière ×%d, XML OK' % (vid, v['name'], len(a), len(n), n.count('tp={{tp}}'), n.count('Matière :')))
if mode == 'apply' and nouveaux:
    os.makedirs(DEPOT, exist_ok=True)
    for vid, n in nouveaux.items():
        x('ir.ui.view', 'write', [vid], {'arch_base': n})
        relu = x('ir.ui.view', 'read', [vid], ['arch_db'])[0]['arch_db']
        io.open('%s/%d.xml' % (DEPOT, vid), 'w', encoding='utf-8', newline='\n').write(relu)
        print(vid, 'écrite :', relu == n)
