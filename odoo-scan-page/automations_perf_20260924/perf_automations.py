# -*- coding: utf-8 -*-
"""Confirmation des commandes Pierres : les automatisations qui rebalayent toute la commande à chaque écriture
de chaque OF / OT deviennent différées (une passe par transaction) et les déclencheurs « tous les champs »
sont restreints aux champs utiles.
  python perf_automations.py show      état actuel (lecture seule)
  python perf_automations.py archive   sauvegarde JSON des définitions actuelles (lecture seule)
  python perf_automations.py apply     applique les modifications (après archive)
  python perf_automations.py restore   remet les définitions du JSON
"""
import io, json, os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'show').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
ARCH = 'ocr/odoo-scan-page/automations_perf_20260924/avant.json'

# automatisations concernées (ids base.automation) et modifications
DIFFERES = {76: 'fab_of', 77: 'fab_ot', 61: 'etape_of'}
TRIGGERS = {
    7: ('mrp.production', ['origin', 'sale_line_id', 'product_id']),           # Transfert champs BC vers OF : à la création / re-liaison seulement
    12: ('mrp.production', ['name', 'x_studio_nbr', 'x_studio_nbr_original_1']),  # Update Nbr Split
    14: ('sale.order', ['x_studio_plan_gnral', 'order_line']),                   # Classement automatique plans de fabrication
    53: ('sale.order.line', ['product_id', 'tax_ids']),                          # FSM - Corriger TVA articles
    68: ('sale.order.line', ['product_id', 'product_uom_id']),                   # UdF selon le libellé de variante
    55: ('sale.order.line', ['qty_delivered', 'qty_invoiced']),                  # PdV - Corriger qty_delivered
}
IDS = sorted(set(DIFFERES) | set(TRIGGERS))


def lire():
    out = []
    for a in x('base.automation', 'read', IDS, ['name', 'model_name', 'trigger', 'trigger_field_ids', 'filter_domain', 'filter_pre_domain', 'action_server_ids', 'active']):
        a['trigger_fields'] = [f['name'] for f in x('ir.model.fields', 'read', a['trigger_field_ids'], ['name'])] if a['trigger_field_ids'] else []
        a['actions'] = x('ir.actions.server', 'read', a['action_server_ids'], ['name', 'state', 'code'])
        out.append(a)
    return out


def indent(body, n):
    return '\n'.join((' ' * n + l) if l.strip() else '' for l in body.split('\n'))


def code_differe(orig, cle):
    """Transforme le code d'origine en version différée (une passe en fin de transaction)."""
    lignes = orig.strip('\n').split('\n')
    if cle in ('fab_of', 'fab_ot'):
        i = [k for k, l in enumerate(lignes) if l.startswith('TRC = ')]
        assert len(i) == 1, 'ligne TRC introuvable'
        body = '\n'.join(lignes[i[0]:])
        assert body.rstrip().endswith('})'), body[-60:]
        tete = ("names = set(r.origin for r in records if r.origin)" if cle == 'fab_of'
                else "names = set(p.origin for p in records.mapped('production_id') if p.origin)")
        return """# Recalcul « Fab en cours » DIFFÉRÉ en fin de transaction : une seule passe par commande, quel que soit
# le nombre d'OF / OT écrits dans la transaction (avant : recalcul complet à chaque écriture de chaque OF,
# soit un coût quadratique à la confirmation d'une commande de plusieurs centaines de lignes).
%s
if names:
    _d = env.cr.precommit.data
    if 'maq_fab_recalc' not in _d:
        _d['maq_fab_recalc'] = set()
        def _maq_fab_recalc():
            noms = env.cr.precommit.data.pop('maq_fab_recalc', set())
            orders = env['sale.order'].search([('name', 'in', sorted(noms))]) if noms else env['sale.order']
%s
            env.flush_all()
        env.cr.precommit.add(_maq_fab_recalc)
    _d['maq_fab_recalc'].update(names)
""" % (tete, indent(body, 12))
    if cle == 'etape_of':
        i = [k for k, l in enumerate(lignes) if l.startswith('STAGES = ')]
        assert len(i) == 1, 'ligne STAGES introuvable'
        assert lignes[0].startswith("TASKS = records.mapped('x_studio_tche_commande_pierre')"), lignes[0]
        body = '\n'.join(lignes[i[0]:])
        return """# Étape de la tâche Commande Pierres selon les OF : recalcul DIFFÉRÉ en fin de transaction (une passe par tâche,
# au lieu d'un balayage de tous les OF de la tâche à chaque changement d'état de chaque OF).
_tids = set(records.mapped('x_studio_tche_commande_pierre').ids)
if _tids:
    _d = env.cr.precommit.data
    if 'maq_etape_of' not in _d:
        _d['maq_etape_of'] = set()
        def _maq_etape_of():
            _ids = env.cr.precommit.data.pop('maq_etape_of', set())
            TASKS = env['project.task'].browse(sorted(_ids)).exists()
%s
            env.flush_all()
        env.cr.precommit.add(_maq_etape_of)
    _d['maq_etape_of'].update(_tids)
""" % indent(body, 12)
    raise ValueError(cle)


def fids(model, noms):
    fs = x('ir.model.fields', 'search_read', [['model', '=', model], ['name', 'in', noms]], fields=['name'])
    assert sorted(f['name'] for f in fs) == sorted(noms), (model, noms, [f['name'] for f in fs])
    return [f['id'] for f in fs]


etat = lire()
if mode == 'show':
    for a in etat:
        print('[%s] %-16s %-55s %-18s déclencheurs %s | actions %s' % (a['id'], a['model_name'], a['name'][:55], a['trigger'], a['trigger_fields'] or 'TOUS', [(s['id'], len(s['code'] or '')) for s in a['actions']]))
        for s in a['actions']:
            if a['id'] in DIFFERES:
                print('      code (%d lignes) : %s …' % (len((s['code'] or '').split('\n')), (s['code'] or '').split('\n')[0][:100]))
elif mode == 'archive':
    os.makedirs(os.path.dirname(ARCH), exist_ok=True)
    io.open(ARCH, 'w', encoding='utf-8', newline='\n').write(json.dumps(etat, ensure_ascii=False, indent=1))
    print('archivé :', ARCH, '(%d automatisations)' % len(etat))
elif mode == 'apply':
    assert os.path.exists(ARCH), 'lancer archive avant'
    for a in etat:
        if a['id'] in DIFFERES:
            assert len(a['actions']) == 1, a['id']
            s = a['actions'][0]
            if 'maq_fab_recalc' in (s['code'] or '') or 'maq_etape_of' in (s['code'] or ''):
                print('[%s] déjà différé' % a['id']); continue
            new = code_differe(s['code'], DIFFERES[a['id']])
            compile(new, '<automation %s>' % a['id'], 'exec')   # vérification syntaxique locale
            x('ir.actions.server', 'write', [s['id']], {'code': new})
            print('[%s] %s : code différé écrit (%d lignes)' % (a['id'], a['name'], len(new.split('\n'))))
        if a['id'] in TRIGGERS:
            model, noms = TRIGGERS[a['id']]
            assert a['model_name'] == model, (a['id'], a['model_name'])
            x('base.automation', 'write', [a['id']], {'trigger_field_ids': [(6, 0, fids(model, noms))]})
            print('[%s] %s : déclencheurs %s -> %s' % (a['id'], a['name'], a['trigger_fields'] or 'TOUS', noms))
    print('\nÉtat après :')
    for a in lire():
        print('[%s] %-55s déclencheurs %s%s' % (a['id'], a['name'][:55], a['trigger_fields'] or 'TOUS', ' | code différé' if any('maq_' in (s['code'] or '') for s in a['actions']) else ''))
elif mode == 'restore':
    avant = json.loads(io.open(ARCH, encoding='utf-8').read())
    for a in avant:
        for s in a['actions']:
            x('ir.actions.server', 'write', [s['id']], {'code': s['code']})
        x('base.automation', 'write', [a['id']], {'trigger_field_ids': [(6, 0, fids(a['model_name'], a['trigger_fields']) if a['trigger_fields'] else [])]})
        print('[%s] %s restaurée (déclencheurs %s)' % (a['id'], a['name'], a['trigger_fields'] or 'TOUS'))
else:
    print('mode inconnu', mode)
