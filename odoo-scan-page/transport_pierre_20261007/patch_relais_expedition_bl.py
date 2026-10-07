# -*- coding: utf-8 -*-
"""Phase 3 : au départ des palettes, le bon de livraison de la commande est validé pour les pièces chargées (reliquat
automatique pour le reste), avec transporteur et référence de suivi ; les quantités livrées suivent la réalité et la
facture partielle de Céline se base dessus. Paramètre système maquignon.expedition_bl = 0 pour désactiver.
Mode lecture seule « bl_plan » pour contrôler le calcul sans rien écrire.   python patch_relais_expedition_bl.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
p = os.path.join(R, 'web_actions.py'); s = io.open(p, encoding='utf-8', newline='').read()
if '_exp_bl(' in s:
    print('déjà patché'); sys.exit(0)

BLOC = r'''
EXP_BL_PARAM = 'maquignon.expedition_bl'      # '1' (défaut) : valider le BL au départ ; '0' : seulement transporteur et suivi


def _exp_lignes_livrees(call, grp):
    """Quantités à livrer par ligne de commande d'après le contenu des palettes : un OF entier = toute la quantité de sa
    ligne (une pierre = une ligne, en m³ ou en tonne) ; une répartition = au prorata des pièces (q / total de l'OF).
    Plafonné à ce qui reste à livrer sur la ligne. Renvoie {ligne_id: quantité}."""
    of_ids = sorted({it['of_id'] for p in grp for it in p.get('items', []) if it.get('of_id')})
    if not of_ids:
        return {}
    ofs = {o['id']: o for o in call('mrp.production', 'search_read', [['id', 'in', of_ids]], fields=['sale_line_id', 'x_studio_nbr'])}
    frac = {}
    for p in grp:
        for it in p.get('items', []):
            o = ofs.get(it.get('of_id'))
            if not o or not o['sale_line_id']:
                continue
            lid = o['sale_line_id'][0]
            tot = int(o['x_studio_nbr'] or 1) or 1
            part = 1.0 if it.get('kind') == 'whole' else min(1.0, float(it.get('qte') or 0) / tot)
            frac[lid] = min(1.0, frac.get(lid, 0.0) + part)
    if not frac:
        return {}
    out = {}
    for l in call('sale.order.line', 'read', list(frac), fields=['product_uom_qty', 'qty_delivered']):
        q = round(min(frac[l['id']] * (l['product_uom_qty'] or 0.0), (l['product_uom_qty'] or 0.0) - (l['qty_delivered'] or 0.0)), 3)
        if q > 0.0005:
            out[l['id']] = q
    return out


def _exp_bl(call, so_id, lignes, mode, qui, camion, lot, lettre, noms, simulation=False):
    """Valide le(s) transfert(s) en attente de la commande pour les quantités `lignes` ({ligne_id: qté}) : chaîne
    PICK -> PACK -> OUT si l'ancienne route en 3 étapes est encore en cours, sinon le bon de livraison seul.
    Les mouvements non chargés restent en reliquat (Odoo crée le reliquat tout seul). Renvoie un texte de synthèse."""
    if not lignes:
        return 'BL : aucune ligne de commande identifiée sur ces palettes'
    infos = []
    for _ in range(3):
        pend = call('stock.picking', 'search_read', [['sale_id', '=', so_id], ['state', 'in', ['assigned', 'confirmed', 'waiting', 'partially_available']]],
                    fields=['name', 'picking_type_code', 'move_ids', 'carrier_id', 'carrier_tracking_ref'])
        pend.sort(key=lambda k: (0 if k['picking_type_code'] == 'internal' else 1, k['name']))
        choix = None
        for pk in pend:
            mvs = call('stock.move', 'search_read', [['picking_id', '=', pk['id']], ['sale_line_id', 'in', list(lignes)], ['state', 'not in', ['done', 'cancel']]],
                       fields=['id', 'sale_line_id', 'product_uom_qty', 'quantity', 'picked'])
            if mvs:
                choix = (pk, mvs); break
        if not choix:
            if not infos:
                infos.append('BL : aucun transfert en attente pour ces lignes')
            break
        pk, mvs = choix
        restant = dict(lignes); a_faire = []
        for mv in mvs:
            lid = mv['sale_line_id'][0]
            q = round(min(mv['product_uom_qty'] or 0.0, restant.get(lid, 0.0)), 3)
            if q <= 0.0005:
                continue
            a_faire.append((mv['id'], q)); restant[lid] = round(restant[lid] - q, 6)
        if not a_faire:
            infos.append('%s : rien à valider' % pk['name']); break
        if simulation:
            infos.append('%s : %d mouvement(s) à valider sur %d (%s)' % (pk['name'], len(a_faire), len(pk['move_ids']), ', '.join('%.3f' % q for _, q in a_faire[:8])))
            break
        for mid, q in a_faire:
            call('stock.move', 'write', [mid], {'quantity': q, 'picked': True})
        autres = call('stock.move', 'search', [['picking_id', '=', pk['id']], ['id', 'not in', [mid for mid, _ in a_faire]], ['state', 'not in', ['done', 'cancel']]])
        if autres:
            call('stock.move', 'write', autres, {'picked': False})
        vals = {'carrier_tracking_ref': ' | '.join(t for t in [pk.get('carrier_tracking_ref') or '', '%s — %s — %s%s' % (lot, qui, noms, (' — ' + lettre) if lettre else '')] if t)[:500]}
        if mode == 'camions' and camion:
            cid = call('delivery.carrier', 'search', [['name', '=', camion]], limit=1)
            if cid:
                vals['carrier_id'] = cid[0]
        call('stock.picking', 'write', [pk['id']], vals)
        _sur(lambda: call('stock.picking', 'button_validate', [pk['id']], context={'skip_backorder': True, 'skip_sms': True, 'skip_immediate': True}))
        etat = call('stock.picking', 'read', [pk['id']], fields=['state', 'backorder_ids'])[0]
        rel = ', '.join(b['name'] for b in call('stock.picking', 'read', etat['backorder_ids'], fields=['name'])) if etat['backorder_ids'] else ''
        if etat['state'] != 'done':
            infos.append('%s : validation incomplète (état %s)' % (pk['name'], etat['state'])); break
        infos.append('%s validé pour %d ligne(s)%s' % (pk['name'], len(a_faire), (' — reliquat ' + rel) if rel else ' — sans reliquat'))
        if pk['picking_type_code'] == 'outgoing':
            break
    return ' ; '.join(infos)

'''
anchor = "\n\ndef _exp_annuler(call, ctx):"
assert s.count(anchor) == 1
s = s.replace(anchor, BLOC + anchor, 1)

# items bruts sur la fiche palette (of_id / kind / qte) pour le calcul des quantités livrées
old = """    return {'id': colis['id'], 'name': colis['name'], 'zone': colis['x_studio_zone'] or '',"""
new = """    return {'id': colis['id'], 'name': colis['name'], 'zone': colis['x_studio_zone'] or '',
            'items': [{'of_id': i.get('of_id'), 'kind': i.get('kind'), 'qte': i.get('qte')} for i in items],"""
assert s.count(old) == 1; s = s.replace(old, new, 1)

# dans _exp_valider : BL par commande, après la note et la tâche
old = """        details.append((so['name'], grp[0]['client'], noms, ton, etat))
    # mail au bureau"""
new = """        bl = ''
        if str(_param(call, EXP_BL_PARAM, '1')).strip().lower() not in ('0', 'non', 'false'):
            try:
                bl = _exp_bl(call, so_id, _exp_lignes_livrees(call, grp), mexp, qui, camion, lot, lettre, noms)
            except Exception as exc:  # noqa: BLE001 — le départ reste enregistré, le BL se fera au bureau
                bl = 'BL non validé automatiquement : %s' % str(exc).strip().split('\\n')[-1][:200]
            _note(call, 'sale.order', so_id, '📦 %s — %s' % (lot, bl))
            etat = etat + ' — ' + bl
        details.append((so['name'], grp[0]['client'], noms, ton, etat))
    # mail au bureau"""
assert s.count(old) == 1; s = s.replace(old, new, 1)

# mode lecture seule bl_plan
old = """    if mode == 'lots':
        return _exp_lots(call, ctx.get('jours') or 3)
    raise WebErreur('Mode inconnu : %s' % mode)"""
new = """    if mode == 'lots':
        return _exp_lots(call, ctx.get('jours') or 3)
    if mode == 'bl_plan':
        # contrôle sans écriture : quantités par ligne et transfert qui serait validé, par commande
        pals = [_exp_palette(call, _exp_lire(call, colis_id=int(i))) for i in (ctx.get('palettes') or [])]
        plan = []
        for so_id in sorted({p['commande_id'] for p in pals}):
            grp = [p for p in pals if p['commande_id'] == so_id]
            lignes = _exp_lignes_livrees(call, grp) if so_id else {}
            plan.append({'commande': grp[0]['commande'], 'lignes': {str(k): v for k, v in lignes.items()},
                         'bl': _exp_bl(call, so_id, lignes, 'client', 'simulation', '', 'CHG-SIMULATION', '', ', '.join(p['name'] for p in grp), simulation=True) if so_id else 'sans commande'})
        return {'plan': plan}
    raise WebErreur('Mode inconnu : %s' % mode)"""
assert s.count(old) == 1; s = s.replace(old, new, 1)
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('web_actions.py : phase 3 (BL au départ, mode bl_plan) ajoutée, syntaxe ok')
