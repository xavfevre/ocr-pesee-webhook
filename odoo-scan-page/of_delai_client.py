# -*- coding: utf-8 -*-
"""Délai client (Ventes > article > « Délai de livraison ») : c'est lui qui date les OF à +20 jours.
Usage : python of_delai_client.py dry   -> liste les articles concernés
        python of_delai_client.py apply -> met le délai à 0 (les nouveaux OF partent à la date de commande)"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
rows=x('product.template','search_read',[['sale_ok','=',True],['company_id','in',[1,False]],['sale_delay','>',0]],fields=['name','default_code','sale_delay','company_id'],order='default_code')
for r in rows: print('  %-14s %-52s %4.0f j  %s' % (r['default_code'] or '', r['name'][:52], r['sale_delay'], r['company_id'] and r['company_id'][1] or 'toutes sociétés'))
print(len(rows), 'article(s) avec un délai client > 0')
if mode == 'apply' and rows:
    x('product.template','write',[r['id'] for r in rows],{'sale_delay':0})
    print('délai client mis à 0 sur', len(rows), 'article(s) — les prochains OF seront datés du jour de la commande')
