# -*- coding: utf-8 -*-
"""Libellé Client (sale.order.line.x_studio_libell_client) reporté dans la Description article des OF (demande Xavier 21/10/2026,
exemple S11958). 1) sauvegarde du code de l'action 1477 « Transfert champs BC vers OF », 2) patch : le libellé client est mis
en tête de x_studio_description_article, 3) reprise des OF non terminés dont la ligne de vente a un libellé client.
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

def description(libcli, desc):
    """Description article de l'OF = libellé client puis le complément de description de la ligne (ex. « - Brut de sciage »)."""
    libcli = (libcli or '').strip(); desc = (desc or '').strip()
    if libcli and desc and desc.lower() not in libcli.lower():
        return libcli + ' ' + desc
    return libcli or desc

# 1. code actuel + sauvegarde
act = call('ir.actions.server', 'read', [1477], fields=['code', 'write_date'], **CTX)[0]
code = act['code']
sauv = os.path.join(ICI, 'action_1477_avant_libelle_%s.py' % dt.date.today().strftime('%Y%m%d'))
io.open(sauv, 'w', encoding='utf-8', newline='\n').write(code)
print('code actuel sauvegardé :', sauv, '| modifié le', act['write_date'])

old = """            except Exception:
                vals['x_studio_description_article'] = ''
        vals['log_note'] ="""
new = """            except Exception:
                vals['x_studio_description_article'] = ''
            _libcli = (matching_line.x_studio_libell_client or '').strip()
            if _libcli:
                vals['x_studio_description_article'] = _libcli if (vals.get('x_studio_description_article') or '').strip().lower() in _libcli.lower() else (_libcli + ' ' + vals['x_studio_description_article']).strip()
        vals['log_note'] ="""
deja = "_libcli = (matching_line.x_studio_libell_client" in code
if deja:
    print('patch déjà présent dans l action 1477')
else:
    assert code.count(old) == 1, 'point d insertion introuvable'
    nouveau = code.replace(old, new)
    compile(nouveau, 'action_1477', 'exec')
    print('patch : +%d lignes, syntaxe vérifiée' % (nouveau.count('\n') - code.count('\n')))

# 3. OF à reprendre
ofs = call('mrp.production', 'search_read', [['state', 'not in', ['done', 'cancel']], ['sale_line_id.x_studio_libell_client', '!=', False]],
           fields=['name', 'state', 'sale_line_id', 'x_studio_description_article', 'origin'], order='id', **CTX)
lignes = {l['id']: l for l in call('sale.order.line', 'read', [o['sale_line_id'][0] for o in ofs], fields=['x_studio_libell_client', 'name'], **CTX)} if ofs else {}
plan = []
for o in ofs:
    l = lignes[o['sale_line_id'][0]]
    voulu = description(l['x_studio_libell_client'], o['x_studio_description_article'])
    if voulu != (o['x_studio_description_article'] or ''):
        plan.append((o['id'], o['name'], o['origin'], o['x_studio_description_article'] or '', voulu))
print('\nOF non terminés avec libellé client :', len(ofs), '| à mettre à jour :', len(plan))
for p in plan:
    print('  %s (%s) : %r -> %r' % (p[1], p[2], p[3][:40], p[4][:80]))
if not APPLY:
    print('\nsimulation : rien écrit'); sys.exit()
if not deja:
    call('ir.actions.server', 'write', [1477], {'code': nouveau}, **CTX)
    print('action 1477 mise à jour')
for p in plan:
    call('mrp.production', 'write', [p[0]], {'x_studio_description_article': p[4]}, **CTX)
print('OF mis à jour :', len(plan))
