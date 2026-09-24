# -*- coding: utf-8 -*-
"""Lecture seule : code complet des automatisations qui tournent à la confirmation (OF / OT / commande / lignes),
vue formulaire commande (limite et champs de la liste des lignes), origine des centaines de messages sur les commandes,
durée réelle des confirmations passées (écart entre les messages), OF / routes / nomenclatures / types d'opération."""
import os, ssl, sys, re, xmlrpc.client
from collections import Counter
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [1, 2, 3, 4, 13]}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def dt(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')


# ── 1. automatisations : code complet ──────────────────────────────────────────────────────────────────
MODELS = ['sale.order', 'sale.order.line', 'mrp.production', 'mrp.workorder', 'stock.picking', 'stock.move']
print('#' * 110); print('# AUTOMATISATIONS (code complet)'); print('#' * 110)
for a in x('base.automation', 'search_read', [['active', '=', True], ['model_name', 'in', MODELS], ['trigger', '!=', 'on_change']],
           fields=['name', 'model_name', 'trigger', 'filter_domain', 'filter_pre_domain', 'trigger_field_ids', 'action_server_ids', 'id'], order='model_name, id'):
    tf = [f['name'] for f in x('ir.model.fields', 'read', a['trigger_field_ids'], ['name'])] if a['trigger_field_ids'] else []
    print('\n=== [%s] %s — %s | déclencheur %s | champs déclencheurs %s | filtre avant %s | filtre %s' % (a['id'], a['model_name'], a['name'], a['trigger'], tf or 'TOUS', a['filter_pre_domain'] or '-', a['filter_domain'] or '-'))
    for sa in x('ir.actions.server', 'read', a['action_server_ids'], ['name', 'state', 'code', 'update_path', 'value', 'evaluation_type', 'child_ids']):
        if sa['state'] == 'code':
            print('--- action « %s » (code) :' % sa['name']); print(sa['code'])
        else:
            print('--- action « %s » : %s %s = %s' % (sa['name'], sa['state'], sa['update_path'], sa['value']))

# ── 2. vues formulaire : lignes ──────────────────────────────────────────────────────────────────────────
print('\n' + '#' * 110); print('# VUES FORMULAIRE'); print('#' * 110)
for model, champ in (('sale.order', 'order_line'), ('account.move', 'invoice_line_ids'), ('account.move', 'line_ids')):
    arch = x(model, 'get_views', [[False, 'form']])['views']['form']['arch']
    mt = re.search(r'<field name="%s"[^>]*>' % champ, arch)
    print('\n%s.%s :' % (model, champ), mt.group(0)[:300] if mt else 'ABSENT')
    if mt:
        seg = arch[mt.end():]
        fin = seg.find('</field>')
        # sous-vue liste : la première <list ...> après le champ
        lst = re.search(r'<list[^>]*>(.*?)</list>', seg, re.S)
        if lst:
            noms = re.findall(r'<field name="([^"]+)"', lst.group(1))
            vis = re.findall(r'<field name="([^"]+)"(?![^>]*(?:column_invisible="1"|invisible="1"))[^>]*/?>', lst.group(1))
            print('   liste : %d champs (%d hors column_invisible/invisible=1) : %s' % (len(noms), len(vis), ', '.join(noms)))
            print('   attributs de la liste :', re.search(r'<list[^>]*>', seg).group(0)[:200])
            for suspect in ('x_studio_palettes', 'x_of_ids', 'x_studio_plan', 'x_studio_plan_ligne', 'x_studio_epaisseur', 'analytic_distribution', 'product_template_attribute_value_ids'):
                if suspect in noms:
                    print('   présent :', suspect)

# ── 3. messages sur les grosses commandes ────────────────────────────────────────────────────────────────
print('\n' + '#' * 110); print('# MESSAGES SUR LES COMMANDES ET DURÉE DES CONFIRMATIONS PASSÉES'); print('#' * 110)
for so_id, nom in ((37675, 'S06604'), (38529, 'S07457'), (42139, 'S11054')):
    msgs = x('mail.message', 'search_read', [['model', '=', 'sale.order'], ['res_id', '=', so_id]], fields=['date', 'message_type', 'subtype_id', 'body', 'author_id', 'tracking_value_ids'], order='date')
    cnt = Counter((mm['message_type'], (mm['subtype_id'] or ['', ''])[1], re.sub('<[^>]+>', ' ', mm['body'] or '').strip()[:50]) for mm in msgs)
    print('\n%s : %d messages' % (nom, len(msgs)))
    for k, v in cnt.most_common(6):
        print('   %4d ×  %s' % (v, k))
    confs = [mm for mm in msgs if mm['tracking_value_ids']]
    tv = x('mail.tracking.value', 'search_read', [['mail_message_id', 'in', [mm['id'] for mm in confs]]], fields=['field_id', 'old_value_char', 'new_value_char', 'mail_message_id'])
    conf = [t for t in tv if t['field_id'][1].startswith('Statut') or t['field_id'][1].startswith('État') or t['field_id'][1].startswith('State')]
    for t in conf:
        mm = [q for q in confs if q['id'] == t['mail_message_id'][0]][0]
        print('   suivi %s : %s -> %s à %s' % (t['field_id'][1], t['old_value_char'], t['new_value_char'], mm['date']))
    mos = x('mrp.production', 'search_read', [['origin', '=', nom]], fields=['name', 'state', 'workorder_ids', 'move_raw_ids', 'create_date', 'write_date'], order='id')
    if mos:
        mm_of = x('mail.message', 'search_read', [['model', '=', 'mrp.production'], ['res_id', 'in', [o['id'] for o in mos]]], fields=['date', 'message_type', 'subtype_id', 'body'], order='date')
        print('   OF : %d (create_date %s … %s) | messages sur les OF : %d, de %s à %s' % (len(mos), min(o['create_date'] for o in mos), max(o['create_date'] for o in mos), len(mm_of), mm_of and mm_of[0]['date'], mm_of and mm_of[-1]['date']))
        jour = mos[0]['create_date'][:10]
        dates = [dt(q['date']) for q in mm_of if q['date'][:10] == jour] + [dt(q['date']) for q in msgs if q['date'][:10] == jour]
        if dates:
            print('   messages du jour de création (%s) : %d, étalés de %s à %s  => durée mini de la transaction ≈ %.0f s' % (jour, len(dates), min(dates).strftime('%H:%M:%S'), max(dates).strftime('%H:%M:%S'), (max(dates) - min(dates)).total_seconds()))
        cnt2 = Counter((q['message_type'], (q['subtype_id'] or ['', ''])[1], re.sub('<[^>]+>', ' ', q['body'] or '').strip()[:45]) for q in mm_of)
        for k, v in cnt2.most_common(5):
            print('      %4d ×  %s' % (v, k))
        print('   OT par OF %s | composants par OF %s | états %s' % (Counter(len(o['workorder_ids']) for o in mos), Counter(len(o['move_raw_ids']) for o in mos), Counter(o['state'] for o in mos)))

# ── 4. produits / routes / nomenclatures / types d'opération ────────────────────────────────────────────
print('\n' + '#' * 110); print('# PRODUITS, ROUTES, NOMENCLATURES, TYPES D OPÉRATION'); print('#' * 110)
so = x('sale.order', 'read', [38529], ['name', 'order_line', 'warehouse_id', 'picking_ids'])[0]
lignes = x('sale.order.line', 'read', so['order_line'], ['product_id', 'product_uom_qty', 'display_type'])
prods = Counter(l['product_id'][1][:50] for l in lignes if l['product_id'])
print('Produits sur %s (%d lignes, %d produits distincts) :' % (so['name'], len(lignes), len(prods)))
for k, v in prods.most_common(6):
    print('   %4d ×  %s' % (v, k))
pids = sorted({l['product_id'][0] for l in lignes if l['product_id']})
pp = x('product.product', 'read', pids, ['product_tmpl_id', 'route_ids', 'bom_count', 'type', 'is_storable', 'categ_id'])
tmpls = sorted({q['product_tmpl_id'][0] for q in pp})
routes = {r['id']: r['name'] for r in x('stock.route', 'search_read', [], fields=['name'], context={'active_test': False})}
print('Routes / types sur ces produits :', [(k, v) for k, v in Counter((q['type'], q['is_storable'], q['bom_count'], tuple(routes.get(r, r) for r in sorted(q['route_ids']))) for q in pp).most_common(6)])
cats = x('product.category', 'read', sorted({q['categ_id'][0] for q in pp}), ['name', 'total_route_ids'])
print('Routes des catégories :', [(ct['name'], [routes.get(r, r) for r in ct['total_route_ids']]) for ct in cats])
boms = x('mrp.bom', 'search_read', [['product_tmpl_id', 'in', tmpls]], fields=['product_tmpl_id', 'type', 'operation_ids', 'bom_line_ids', 'product_qty'])
print('Nomenclatures : %d | types %s | opérations par nomenclature %s | composants par nomenclature %s' % (len(boms), Counter(b['type'] for b in boms), Counter(len(b['operation_ids']) for b in boms), Counter(len(b['bom_line_ids']) for b in boms)))
comp_ids = sorted({l['product_id'][0] for l in x('mrp.bom.line', 'search_read', [['bom_id', 'in', [b['id'] for b in boms]]], fields=['product_id'])})
if comp_ids:
    comps = x('product.product', 'read', comp_ids[:40], ['display_name', 'route_ids', 'bom_count', 'seller_ids', 'is_storable', 'qty_available'])
    print('Composants (%d) :' % len(comp_ids), [(q['display_name'][:35], [routes.get(r, r) for r in q['route_ids']], 'nomencl.' if q['bom_count'] else '', 'fourn.' if q['seller_ids'] else '', q['qty_available']) for q in comps[:6]])
print("Types d'opération :")
for t in x('stock.picking.type', 'search_read', [['code', 'in', ['mrp_operation', 'outgoing']], ['company_id', '=', 1]], fields=['name', 'code', 'reservation_method', 'reservation_days_before', 'create_backorder'], order='code'):
    print('   %-38s %-14s réservation %-14s backorder %s' % (t['name'][:38], t['code'], t['reservation_method'], t['create_backorder']))
print('Entrepôts :', [(w['name'], w['manufacture_steps'], w['delivery_steps']) for w in x('stock.warehouse', 'search_read', [['company_id', '=', 1]], fields=['name', 'manufacture_steps', 'delivery_steps'])])
print('Règles fabrication / MTO :', [(r['name'][:40], r['action'], r['procure_method']) for r in x('stock.rule', 'search_read', ['|', ['action', '=', 'manufacture'], ['procure_method', '=', 'mto'], ['company_id', '=', 1]], fields=['name', 'action', 'procure_method'])])
pk = x('stock.picking', 'read', so['picking_ids'], ['name', 'state', 'move_ids', 'picking_type_id'])
print('Livraisons de %s :' % so['name'], [(k_['name'], k_['state'], len(k_['move_ids']), k_['picking_type_id'][1]) for k_ in pk])
print('Champs personnalisés mrp.production / mrp.workorder calculés :')
for f in x('ir.model.fields', 'search_read', [['model', 'in', ['mrp.production', 'mrp.workorder']], ['state', '=', 'manual'], '|', ['compute', '!=', False], ['related', '!=', False]], fields=['model', 'name', 'ttype', 'store', 'related', 'compute', 'depends'], order='model, name'):
    print('   %-16s %-40s %-9s %-6s %s%s%s' % (f['model'], f['name'], f['ttype'], 'stocké' if f['store'] else 'calc.', ('related=' + f['related'] + ' ') if f['related'] else '', ('depends=' + str(f['depends']) + ' ') if f['depends'] else '', ('compute: ' + (f['compute'] or '').replace('\n', ' | ')[:150]) if f['compute'] else ''))
print('   (personnalisés au total : mrp.production %d, mrp.workorder %d)' % (x('ir.model.fields', 'search_count', [['model', '=', 'mrp.production'], ['state', '=', 'manual']]), x('ir.model.fields', 'search_count', [['model', '=', 'mrp.workorder'], ['state', '=', 'manual']])))
