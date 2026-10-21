# -*- coding: utf-8 -*-
"""Libellé Client (sale.order.line.x_studio_libell_client) reporté dans la Description article des OF (demande Xavier
21/10/2026, exemple S11958). Version 2 (« le libellé négocié remplace complètement le libellé ») : quand la ligne de vente a un
libellé client, la Description article de l'OF = ce libellé, seul ; sinon comportement d'origine (complément du nom de l'article).
1) sauvegarde du code de l'action 1477 « Transfert champs BC vers OF », 2) patch (remplace aussi la version 1 du 21/10 matin),
3) reprise des OF non terminés dont la ligne de vente a un libellé client.
Usage : python libelle_client_of.py [apply]"""
import os, sys, io, xmlrpc.client, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4]}}
ICI = os.path.dirname(os.path.abspath(__file__))

# 1. code actuel + sauvegarde
act = call('ir.actions.server', 'read', [1477], fields=['code', 'write_date'], **CTX)[0]
code = act['code']
sauv = os.path.join(ICI, 'action_1477_avant_libelle_v2_%s.py' % dt.datetime.now().strftime('%Y%m%d_%H%M'))
io.open(sauv, 'w', encoding='utf-8', newline='\n').write(code)
print('code actuel sauvegardé :', sauv, '| modifié le', act['write_date'])

V1 = """            _libcli = (matching_line.x_studio_libell_client or '').strip()
            if _libcli:
                vals['x_studio_description_article'] = _libcli if (vals.get('x_studio_description_article') or '').strip().lower() in _libcli.lower() else (_libcli + ' ' + vals['x_studio_description_article']).strip()
"""
V2 = """            _libcli = (matching_line.x_studio_libell_client or '').strip()
            if _libcli:
                vals['x_studio_description_article'] = _libcli
"""
ANCRE = """            except Exception:
                vals['x_studio_description_article'] = ''
        vals['log_note'] ="""
if V2 in code:
    nouveau = None; print('version 2 déjà en place dans l action 1477')
elif V1 in code:
    nouveau = code.replace(V1, V2); print('patch : version 1 -> version 2 (libellé seul)')
else:
    assert code.count(ANCRE) == 1, 'point d insertion introuvable'
    nouveau = code.replace(ANCRE, ANCRE.replace("        vals['log_note'] =", V2 + "        vals['log_note'] =")); print('patch : +3 lignes (version 2 directe)')
if nouveau:
    compile(nouveau, 'action_1477', 'exec')

# 3. OF à reprendre : description = libellé client seul
ofs = call('mrp.production', 'search_read', [['state', 'not in', ['done', 'cancel']], ['sale_line_id.x_studio_libell_client', '!=', False]],
           fields=['name', 'state', 'sale_line_id', 'x_studio_description_article', 'origin'], order='id', **CTX)
lignes = {l['id']: l for l in call('sale.order.line', 'read', [o['sale_line_id'][0] for o in ofs], fields=['x_studio_libell_client'], **CTX)} if ofs else {}
plan = []
for o in ofs:
    voulu = (lignes[o['sale_line_id'][0]]['x_studio_libell_client'] or '').strip()
    if voulu and voulu != (o['x_studio_description_article'] or ''):
        plan.append((o['id'], o['name'], o['origin'], o['x_studio_description_article'] or '', voulu))
print('\nOF non terminés avec libellé client :', len(ofs), '| à mettre à jour :', len(plan))
for p in plan:
    print('  %s (%s) : %r -> %r' % (p[1], p[2], p[3][:60], p[4][:60]))
if not APPLY:
    print('\nsimulation : rien écrit'); sys.exit()
if nouveau:
    call('ir.actions.server', 'write', [1477], {'code': nouveau}, **CTX)
    print('action 1477 mise à jour')
for p in plan:
    call('mrp.production', 'write', [p[0]], {'x_studio_description_article': p[4]}, **CTX)
print('OF mis à jour :', len(plan))
