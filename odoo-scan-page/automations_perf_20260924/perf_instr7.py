# -*- coding: utf-8 -*-
"""Chronométrage interne de l'automatisation 7 « Transfert champs BC vers OF » (action 1477) : le code est instrumenté
le temps d'un test de confirmation de N lignes (cumuls par bloc, un seul log en fin de transaction), puis remis à
l'identique. La commande de test est supprimée comme d'habitude ; les lignes de journal (ir.logging) créées sont lues puis effacées.
  python perf_instr7.py [N]"""
import io, os, ssl, sys, time, xmlrpc.client
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding='utf-8')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
VARIANTE = (sys.argv[2] if len(sys.argv) > 2 else 'blocs').lower()   # blocs | write (découpe la réécriture de l'OF par champ)
REEL = len(sys.argv) > 3 and sys.argv[3].lower() == 'reel'   # lignes comme en production : quantité = volume arrondi à 3 décimales
DIMS = (0.52, 0.31, 0.2) if REEL else (0.5, 0.3, 0.2)         # volume 0,03224 (4 décimales) ou 0,03
QTE = round(DIMS[0] * DIMS[1] * DIMS[2], 3) if REEL else 1
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [1], 'default_company_id': 1}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


ACTION = 1477
orig = x('ir.actions.server', 'read', [ACTION], ['name', 'code'])[0]
code = orig['code']
io.open('action_1477_avant_instr.py', 'w', encoding='utf-8', newline='\n').write(code)
lignes = code.split('\n')
A_DUP = 'if record.sale_line_id:'
A_B1 = 'if record.origin and not record.x_studio_nom_du_client:'
A_B23 = 'if record.origin:'
A_WRITE = '        record.write(vals)'
assert lignes.count(A_DUP) == 1 and lignes.count(A_B1) == 1 and lignes.count(A_B23) == 2 and lignes.count(A_WRITE) == 1, (lignes.count(A_DUP), lignes.count(A_B1), lignes.count(A_B23), lignes.count(A_WRITE))
i_dup, i_b1, i_w = lignes.index(A_DUP), lignes.index(A_B1), lignes.index(A_WRITE)
i_b2 = lignes.index(A_B23); i_b3 = lignes.index(A_B23, i_b2 + 1)
assert i_dup < i_b1 < i_w < i_b2 < i_b3
TETE = """_T7 = env.cr.precommit.data.setdefault('t7', {'n': 0})
if 'cb' not in _T7:
    _T7['cb'] = 1
    def _t7_fin():
        _dd = env.cr.precommit.data.get('t7', {})
        log('T7 ' + ' | '.join('%s=%.3f' % (_k, _v) for _k, _v in sorted(_dd.items()) if _k != 'cb'), level='info')
    env.cr.precommit.add(_t7_fin)
_T7['n'] = _T7.get('n', 0) + 1
_t = time.time()"""


def cumul(cle, indent=0):
    sp = ' ' * indent
    return "%s_T7[%r] = _T7.get(%r, 0) + (time.time() - _t); _t = time.time()" % (sp, cle, cle)


out = []
for i, l in enumerate(lignes):
    if i == i_dup:
        out.extend(TETE.split('\n'))
    if i == i_b1:
        out.append(cumul('1_doublons'))
    if i == i_w:
        out.append(cumul('2_calcul_vals', 8))
    if i == i_b2:
        out.append(cumul('4_bloc1_fin'))
    if i == i_b3:
        out.append(cumul('5_bloc2_taille'))
    if i == i_w and VARIANTE == 'write':
        sp = ' ' * 8
        out.extend([
            sp + "_v_qty = {'product_qty': vals.pop('product_qty')} if 'product_qty' in vals else {}",
            sp + "_v_nbr = {'x_studio_nbr': vals.pop('x_studio_nbr')} if 'x_studio_nbr' in vals else {}",
            sp + "_v_sl = {'sale_line_id': vals.pop('sale_line_id')} if 'sale_line_id' in vals else {}",
            sp + "record.write(vals)",
            cumul('3a_write_champs_texte_dims', 8),
            sp + "if _v_sl:",
            sp + "    record.write(_v_sl)",
            cumul('3b_write_sale_line_id', 8),
            sp + "if _v_nbr:",
            sp + "    record.write(_v_nbr)",
            cumul('3c_write_x_studio_nbr', 8),
            sp + "if _v_qty:",
            sp + "    record.write(_v_qty)",
            cumul('3d_write_product_qty', 8),
        ])
        continue
    out.append(l)
    if i == i_w:
        out.append(cumul('3_write_of', 8))
out.append(cumul('6_bloc3_tache'))
instr = '\n'.join(out)
compile(instr, 'instr', 'exec')
print('code instrumenté : %d lignes (original %d)' % (len(out), len(lignes)))
debut = datetime.now(timezone.utc) - timedelta(seconds=5)
PARTNER = 15893
pid = x('product.product', 'search', [['default_code', '=', 'TUF0000-PS']], limit=1)[0]
so_id = None
try:
    x('ir.actions.server', 'write', [ACTION], {'code': instr})
    lignes_so = [(0, 0, {'product_id': pid, 'product_uom_qty': QTE, 'x_studio_ref_pierre': 'TEST-%02d' % (i + 1), 'x_studio_nbr': 1,
                         'x_studio_long': DIMS[0], 'x_studio_larg': DIMS[1], 'x_studio_epais': DIMS[2]}) for i in range(N)]
    print('lignes : quantité %g m³, dimensions %s (volume %g)' % (QTE, DIMS, DIMS[0] * DIMS[1] * DIMS[2]))
    so_id = x('sale.order', 'create', [{'partner_id': PARTNER, 'company_id': 1, 'origin': 'TEST PERF', 'client_order_ref': 'TEST PERF (à supprimer)', 'order_line': lignes_so}])
    so_id = so_id[0] if isinstance(so_id, list) else so_id
    nom = x('sale.order', 'read', [so_id], ['name'])[0]['name']
    print('=== commande %s (%d), %d lignes, action 1477 instrumentée' % (nom, so_id, N))
    t = time.time()
    x('sale.order', 'action_confirm', [so_id])
    dt = time.time() - t
    print('CONFIRMATION : %.1f s  (%.2f s par ligne)' % (dt, dt / N))
finally:
    x('ir.actions.server', 'write', [ACTION], {'code': code})
    relu = x('ir.actions.server', 'read', [ACTION], ['code'])[0]['code']
    print('code d origine restauré :', relu == code)
    if so_id:
        nom = x('sale.order', 'read', [so_id], ['name'])[0]['name']
        mo_ids = [o['id'] for o in x('mrp.production', 'search_read', [['origin', '=', nom]], fields=['id'])]
        if mo_ids:
            x('mrp.production', 'action_cancel', mo_ids); x('mrp.production', 'unlink', mo_ids)
        so2 = x('sale.order', 'read', [so_id], ['state', 'picking_ids'])[0]
        if so2['state'] not in ('cancel', 'draft'):
            x('sale.order', 'action_cancel', [so_id], context={'disable_cancel_warning': True})
        pk_ids = so2['picking_ids']
        if pk_ids:
            stp = x('stock.picking', 'read', pk_ids, ['state'])
            todo = [k['id'] for k in stp if k['state'] != 'cancel']
            if todo:
                x('stock.picking', 'action_cancel', todo)
            x('stock.picking', 'unlink', pk_ids)
        x('sale.order', 'unlink', [so_id])
        for model, ids in (('mrp.production', mo_ids), ('sale.order', [so_id]), ('stock.picking', pk_ids)):
            if ids:
                msg = x('mail.message', 'search', [['model', '=', model], ['res_id', 'in', ids]])
                if msg:
                    x('mail.message', 'unlink', msg)
                at = x('ir.attachment', 'search', [['res_model', '=', model], ['res_id', 'in', ids]])
                if at:
                    x('ir.attachment', 'unlink', at)
        print('--- nettoyage : OF %d, transferts %d, commande supprimés ; restes : commandes %d, OF %d' % (len(mo_ids), len(pk_ids), x('sale.order', 'search_count', [['id', '=', so_id]]), x('mrp.production', 'search_count', [['origin', '=', nom]])))
logs = x('ir.logging', 'search_read', [['message', 'like', 'T7 %'], ['create_date', '>=', debut.strftime('%Y-%m-%d %H:%M:%S')]], fields=['create_date', 'message', 'func'], order='id')
print('\n=== chronométrage interne de « Transfert champs BC vers OF » (cumuls en secondes sur toute la transaction) :')
for lg in logs:
    print('  ', lg['create_date'], lg['message'])
if logs:
    x('ir.logging', 'unlink', [lg['id'] for lg in logs])
    print('(%d lignes de journal effacées)' % len(logs))
