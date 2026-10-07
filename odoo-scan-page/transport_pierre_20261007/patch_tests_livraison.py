# -*- coding: utf-8 -*-
"""Étend le test hors ligne (livrer / a_livrer / annulation de livraison) et le test de production (cycle avec livraison)."""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
ecrire = lambda p, s: io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep(s, old, new, nom=''):
    assert s.count(old) == 1, 'ancre %s : %d' % (nom, s.count(old))
    return s.replace(old, new)


p = os.path.join(HERE, 'test_expedition_mock.py'); s = lire(p)
if "'mode': 'livrer'" not in s:
    s = rep(s, """print('\\nTOUS LES TESTS PASSENT')""", """print('=== livraison : palettes à livrer pour le camion, livrer, annuler la livraison ===')
o3 = Faux()
W.executer(o3, 2104, {'mode': 'valider', 'palettes': [445], 'exp_mode': 'camions', 'camion': 'SEMI GE-106-QS', 'chauffeur': 'Mickaël', 'charge_par': 478, 'sans_mail': 1})
al = W.executer(o3, 2104, {'mode': 'a_livrer', 'camions': ['SEMI GE-106-QS'], 'jours': 7})
check(len(al['palettes']) == 1 and al['palettes'][0]['name'] == 'PACK0000475' and al['palettes'][0]['partner_commercial_id'] == 15897, 'palette chargée sur le camion trouvée pour la tournée : %s' % al['palettes'][0]['name'])
check(W.executer(o3, 2104, {'mode': 'a_livrer', 'camions': ['DAF Camion 8 x 4 EY-665-NV'], 'jours': 7})['palettes'] == [], 'rien pour un autre camion')
lv = W.executer(o3, 2104, {'mode': 'livrer', 'palettes': [445], 'qui': 'DURAND Mickaël', 'source': 'tournee'})
pk3 = o3.data['stock.package'][445]
check(lv['ok'] == 1 and pk3['x_exp_statut'] == 'livree' and pk3['x_livraison_date'], 'palette livrée avec date : %s' % lv['msg'])
check(any(m == 'sale.order' and me == 'message_post' and 'Livraison' in str(k.get('body')) and 'entièrement livrée' in str(k.get('body')) for m, me, a, k in o3.journal), 'note de livraison sur la commande (entièrement livrée)')
lots = W.executer(o3, 2104, {'mode': 'lots', 'jours': 10})
check(lots['lots'][0].get('livrees') == 1 and lots['lots'][0]['palettes'][0]['statut'] == 'livree', 'départs récents : statut livré')
an = W.executer(o3, 2104, {'mode': 'annuler', 'palette_id': 445})
check(pk3['x_exp_statut'] == 'chargee' and not pk3['x_livraison_date'], 'annulation de la livraison : palette de nouveau chargée (%s)' % an['msg'])
try:
    W.executer(o3, 2104, {'mode': 'livrer', 'palettes': [446]}); check(False, 'refus attendu')
except W.WebErreur as e:
    check('en cours de livraison' in str(e), 'refus d une palette non partie : %s' % e)

print('\\nTOUS LES TESTS PASSENT')""", nom='mock livraison')
    ecrire(p, s); print('test_expedition_mock.py : livraison ajoutée')
else:
    print('test_expedition_mock.py : déjà patché')

p = os.path.join(HERE, 'test_expedition_prod.py'); s = lire(p)
if "'mode': 'livrer'" not in s:
    s = rep(s, """a = rpc({'mode': 'annuler', 'palette_id': pk_id})
print('annulation :', a['msg'])""", """lv = rpc({'mode': 'livrer', 'palettes': [pk_id], 'qui': 'TEST', 'source': 'bureau'})
pkl = x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_livraison_date'])[0]
print('livraison :', lv['msg'], '|', pkl)
lots = rpc({'mode': 'lots', 'jours': 10})
print('départs récents (livrées) :', [(l['lot'], l.get('livrees'), l['n']) for l in lots['lots'] if l['lot'] == r['lot']])
a0 = rpc({'mode': 'annuler', 'palette_id': pk_id})
print('annulation livraison :', a0['msg'], '|', x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_livraison_date'])[0])
a = rpc({'mode': 'annuler', 'palette_id': pk_id})
print('annulation :', a['msg'])""", nom='prod livraison')
    s = rep(s, """    msgs += x('mail.message', 'search', [['model', '=', 'sale.order'], ['res_id', '=', p1['commande_id']], ['body', 'ilike', r['lot']]])""",
            """    msgs += x('mail.message', 'search', [['model', '=', 'sale.order'], ['res_id', '=', p1['commande_id']], '|', '|', ['body', 'ilike', r['lot']], ['body', 'ilike', 'Livraison le'], ['body', 'ilike', 'Livraison annulée']])""", nom='prod nettoyage')
    s = rep(s, """    msgs += x('mail.message', 'search', [['model', '=', 'project.task'], ['res_id', '=', tache], ['body', 'ilike', r['lot']]])""",
            """    msgs += x('mail.message', 'search', [['model', '=', 'project.task'], ['res_id', '=', tache], '|', ['body', 'ilike', r['lot']], ['body', 'ilike', 'Livré :']])""", nom='prod nettoyage tâche')
    ecrire(p, s); print('test_expedition_prod.py : cycle avec livraison')
else:
    print('test_expedition_prod.py : déjà patché')
