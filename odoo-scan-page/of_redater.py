# -*- coding: utf-8 -*-
"""OF datés à +20 jours (ancien délai client sur les articles) : remis à leur date de commande.
- OF brouillons : date de début de l'OF = date de création (les opérations suivront à la confirmation) ;
- OF confirmés / en cours : opérations replacées le jour de la commande à 07:00 (France), même machine.
Usage : python of_redater.py        (liste + applique)"""
import os, ssl, sys, xmlrpc.client, datetime
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ofs = x('mrp.production', 'search_read',
        [['company_id', '=', 1], ['state', 'in', ['draft', 'confirmed', 'progress']],
         ['date_start', '>=', '2026-09-30'], ['create_date', '>=', '2026-09-01']],
        fields=['name', 'state', 'date_start', 'create_date', 'workorder_ids'], order='name')
n_d = n_c = 0
for o in ofs:
    cd = datetime.datetime.strptime(o['create_date'][:19], '%Y-%m-%d %H:%M:%S')
    if o['state'] == 'draft':
        x('mrp.production', 'write', [o['id']], {'date_start': o['create_date'][:19]})
        n_d += 1
    else:
        jour = cd.date()
        start = datetime.datetime(jour.year, jour.month, jour.day, 5, 0, 0)   # 07:00 France (heure d'été)
        wos = x('mrp.workorder', 'search', [['id', 'in', o['workorder_ids']], ['state', 'not in', ['done', 'cancel']]])
        if wos:
            x('mrp.workorder', 'write', wos, {'date_start': start.strftime('%Y-%m-%d %H:%M:%S'),
                                              'date_finished': (start + datetime.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')})
        n_c += 1
    print('  ', o['name'], o['state'], o['date_start'][:10], '->', o['create_date'][:10])
print('brouillons redatés :', n_d, '| confirmés replacés :', n_c)
print('OT de WH/OF/12658 :', x('mrp.workorder', 'search_read', [['production_id.name', '=', 'WH/OF/12658']],
                               fields=['date_start', 'workcenter_id', 'state']))
