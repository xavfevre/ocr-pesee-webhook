# -*- coding: utf-8 -*-
"""Actions EPI (web_actions local) contre la prod, sur un article de test archivé à la fin."""
import os, ssl, sys, importlib.util, xmlrpc.client, secrets
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
def call(mo,me,*a,**k): return m.execute_kw(D,uid,p,mo,me,list(a),k)
sys.path.insert(0,'ocr')
spec=importlib.util.spec_from_file_location('wa','ocr/web_actions.py'); wa=importlib.util.module_from_spec(spec); spec.loader.exec_module(wa)
K=call('ir.config_parameter','get_param','maquignon.epi_key'); categ=int(call('ir.config_parameter','get_param','maquignon.epi_categ'))
E=call('hr.employee','search',[['name','=','MAQUIGNON Théo']])[0]
ex=call('product.template','search',[['name','=','TEST EPI (à archiver)'],['active','=',True]])
t=ex[0] if ex else call('product.template','create',[{'name':'TEST EPI (à archiver)','categ_id':categ,'type':'consu','is_storable':True,'purchase_ok':True,'sale_ok':False,'standard_price':10.0}])
t=t[0] if isinstance(t,list) else t
pid=call('product.template','read',[t],['product_variant_ids'])[0]['product_variant_ids'][0]
print('article test',t,'variante',pid)
def essai(lab,fn):
    try: r=fn(); print('OK ',lab,'->',r)
    except wa.WebErreur as e: print('REF',lab,'->',str(e)[:140])
essai('mauvaise clé',lambda: wa.executer(call,2110,{'epi_k':'x','emp':E,'product':pid,'qty':1}))
essai('dotation sans stock',lambda: wa.executer(call,2110,{'epi_k':K,'emp':E,'product':pid,'qty':1,'date':'2026-09-23'}))
essai('réception 2 (hier)',lambda: wa.executer(call,2111,{'epi_k':K,'product':pid,'qty':2,'date':'2026-09-23','note':'test BL 123'}))
r=None
def dot():
    global r; r=wa.executer(call,2110,{'epi_k':K,'emp':E,'product':pid,'qty':1,'date':'2026-09-24','note':'test'}); return r
essai('dotation 1 à Théo',dot)
essai('dotation 3 (stock 1) refusée',lambda: wa.executer(call,2110,{'epi_k':K,'emp':E,'product':pid,'qty':3}))
essai('dotation 3 forcée',lambda: wa.executer(call,2110,{'epi_k':K,'emp':E,'product':pid,'qty':3,'force':1}))
mv=call('stock.move','search_read',[['picking_id','=',r['picking']]],fields=['id','quantity','x_employee_id','date','state'])[0]
print('mouvement de la dotation 1 :',mv)
essai('annulation dotation 1',lambda: wa.executer(call,2112,{'epi_k':K,'move':mv['id']}))
essai('annulation 2e fois',lambda: wa.executer(call,2112,{'epi_k':K,'move':mv['id']}))
print('stock final test :',wa._epi_stock(call,wa._epi_cfg(call,{'epi_k':K}),pid))
print('onglet EPI Théo :',[(x['date'][:10],x['product_id'][1][:20],x['quantity'],x['location_dest_id'][1][:22],x['reference']) for x in call('stock.move','search_read',[['x_employee_id','=',E]],fields=['date','product_id','quantity','location_dest_id','reference'],order='id')])
call('product.template','write',[t],{'active':False}); print('article test archivé')
