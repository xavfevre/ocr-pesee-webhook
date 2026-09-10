# -*- coding: utf-8 -*-
"""Odoo 19 : le bouton « Fabrication » de la commande passe par stock.reference (sale.stock_reference_ids -> production_ids).
Ajoute la référence de S11054 aux OF créés à la main."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
SO=42139
so=x('sale.order','read',[SO],fields=['stock_reference_ids','mrp_production_count'])[0]; print('références commande :',so)
refs=x('stock.reference','read',so['stock_reference_ids']); print('  ',[{k:v for k,v in r.items() if k in ('id','name','production_ids','sale_ids','picking_ids') or 'ids' in k} for r in refs])
print('OF 12030 reference_ids :',x('mrp.production','read',[12030],fields=['reference_ids'])[0]['reference_ids'],'| OF 12058 :',x('mrp.production','read',[12058],fields=['reference_ids'])[0]['reference_ids'])
ref=so['stock_reference_ids'][0]
ofs=x('mrp.production','search_read',[['sale_line_id.order_id','=',SO],['state','!=','cancel'],['reference_ids','not in',[ref]]],fields=['name'],limit=5000)
print('OF sans la référence :',len(ofs))
if len(sys.argv)>1 and sys.argv[1]=='apply' and ofs:
    x('mrp.production','write',[o['id'] for o in ofs],{'reference_ids':[[4,ref]]})
    print('après : bouton Fabrication =',x('sale.order','read',[SO],fields=['mrp_production_count'])[0]['mrp_production_count'])
