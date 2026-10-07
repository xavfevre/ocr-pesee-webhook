# -*- coding: utf-8 -*-
"""Test de bout en bout des webhooks transport sur une BASE DE TEST Odoo (jamais la production) :
  python test_webhooks_base_test.py <hote testmaq….odoo.com> <S… devis modèle à copier>
Copie le devis (brouillon), enlève sa ligne transport, puis :
  1. mode « Nos camions »            -> ligne « Transport de pierres » à 0 en fin de devis (automatisation 103 -> webhook) ;
  2. mode « Transporteur extérieur » + GENDRON, bouton « Demander un tarif transport » (action 2118 lancée par RPC)
                                      -> demande de prix + mail en attente (copie Céline) ;
  3. prix saisi et demande confirmée  -> transporteur retenu, prix d'achat, ligne valorisée + marge (automatisation 102).
Les webhooks passent par le relais Render (URL avec &host=<hôte>) ; chaque étape attend le résultat jusqu'à 60 s."""
import os, re, sys, time, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
hote, modele = sys.argv[1], sys.argv[2]
assert 'maquignon.odoo.com' not in hote and re.fullmatch(r'(testmaq|maquignon-)[a-z0-9-]*\.odoo\.com', hote), 'base de test seulement'
U = 'https://' + hote; D = hote.split('.')[0]
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')


def x(mo, me, *a, **k):
    ctx = {'allowed_company_ids': [1]}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


VARIANTES = [5897, 5898, 5899, 5900]
GENDRON = 18880


def lignes(so_id):
    return x('sale.order.line', 'search_read', [['order_id', '=', so_id]], fields=['name', 'sequence', 'price_unit', 'product_id', 'display_type'], order='sequence, id')


def transport(so_id):
    return [l for l in lignes(so_id) if l['product_id'] and l['product_id'][0] in VARIANTES]


def notes(model, rid, n=4):
    return [re.sub(r'<[^>]+>', '', q['body'])[:150] for q in x('mail.message', 'search_read', [['model', '=', model], ['res_id', '=', rid], ['message_type', '=', 'comment']], fields=['body'], order='id desc', limit=n)]


def attendre(libelle, cond, secondes=60):
    t0 = time.time()
    while time.time() - t0 < secondes:
        v = cond()
        if v:
            print('   %s : ok en %.0f s' % (libelle, time.time() - t0))
            return v
        time.sleep(3)
    raise SystemExit('   %s : rien après %d s (relais déployé ? URL des webhooks ? journal Render)' % (libelle, secondes))


print('=== base %s (db %s), uid %s ===' % (hote, D, uid))
src = x('sale.order', 'search_read', [['name', '=', modele]], fields=['id', 'state', 'company_id'], limit=1)
assert src and src[0]['company_id'][0] == 1, 'devis modèle introuvable ou pas SARL MAQUIGNON'
so_id = x('sale.order', 'copy', [src[0]['id']])
so_id = so_id[0] if isinstance(so_id, list) else so_id
so = x('sale.order', 'read', [so_id], ['name', 'state', 'x_mode_transport'])[0]
print('copie du devis %s -> %s (%s, mode %s)' % (modele, so['name'], so['state'], so['x_mode_transport']))
time.sleep(4)
x('sale.order', 'write', [so_id], {'x_mode_transport': False, 'x_transporteurs_ids': [[6, 0, []]], 'x_transporteur_id': False, 'x_transport_achat': 0.0, 'x_ordre_transport_id': False})
tr = transport(so_id)
if tr:
    x('sale.order.line', 'unlink', [l['id'] for l in tr]); print('ligne(s) transport copiée(s) retirée(s) :', [l['name'][:40] for l in tr])
avant = {l['id'] for l in lignes(so_id)}
print('lignes de départ :', [(l['sequence'], (l['name'] or '')[:30]) for l in lignes(so_id)])

print('1. mode « Nos camions »')
x('sale.order', 'write', [so_id], {'x_mode_transport': 'camions'})
nouv = attendre('ligne transport', lambda: transport(so_id))
print('   ligne :', [(l['sequence'], l['name'], l['price_unit']) for l in nouv])
print('   lignes :', [(l['sequence'], (l['name'] or '')[:30]) for l in lignes(so_id)])
print('   notes :', notes('sale.order', so_id, 3))

print('2. mode « Transporteur extérieur » + GENDRON, bouton « Demander un tarif transport »')
x('sale.order', 'write', [so_id], {'x_mode_transport': 'exterieur', 'x_transporteurs_ids': [[6, 0, [GENDRON]]]})
time.sleep(5)
x('ir.actions.server', 'run', [2118], context={'active_model': 'sale.order', 'active_id': so_id, 'active_ids': [so_id]})
pos = attendre('demande de prix', lambda: x('purchase.order', 'search_read', [['origin', '=', so['name']]], fields=['name', 'state', 'partner_id', 'order_line']))
print('   demandes :', [(q['name'], q['partner_id'][1], q['state']) for q in pos])
po = pos[0]
mails = x('mail.mail', 'search_read', [['mail_message_id.model', '=', 'purchase.order'], ['mail_message_id.res_id', '=', po['id']]], fields=['subject', 'state', 'email_to', 'email_cc'])
print('   mail(s) :', mails)
print('   notes devis :', notes('sale.order', so_id, 3))
assert len(transport(so_id)) == 1, 'la ligne transport ne doit pas être doublée'

print('3. prix 410 saisi et demande confirmée')
x('purchase.order.line', 'write', po['order_line'], {'price_unit': 410.0})
x('purchase.order', 'button_confirm', [po['id']])
fin = attendre('report sur le devis', lambda: (lambda s: s if s['x_transporteur_id'] and s['x_transport_achat'] else None)(x('sale.order', 'read', [so_id], ['x_transporteur_id', 'x_transport_achat', 'x_ordre_transport_id'])[0]))
print('   devis :', fin)
l = attendre('ligne valorisée', lambda: [l for l in transport(so_id) if l['price_unit'] > 0])
print('   ligne :', [(q['sequence'], q['name'], q['price_unit']) for q in l])
print('   notes devis :', notes('sale.order', so_id, 3))
print('   notes demande :', notes('purchase.order', po['id'], 2))
assert len(transport(so_id)) == 1 and abs(l[0]['price_unit'] - 574.0) < 0.01, 'prix attendu 410 + 40 % = 574'
print()
print('TEST BASE DE TEST TERMINÉ : devis %s (id %s) laissé en place' % (so['name'], so_id))
