# -*- coding: utf-8 -*-
"""Deux champs calculés stockés sur account.move.line pour le tableau de bord CA (ventes + contributions) :
 x_ca_ht   : -solde de la ligne si compte de produits (706/707/708…), sinon 0
 x_activite: catégorie d'article (lignes d'article) ou nom de la taxe (TGAP, REP…) ou nom du compte."""
import os, ssl, sys, xmlrpc.client, time
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
mid=x('ir.model','search',[['model','=','account.move.line']])[0]
champs=[
 {'name':'x_ca_ht','field_description':'CA HT (écritures, contributions incluses)','ttype':'float','store':True,'readonly':True,
  'depends':'balance,account_id.account_type',
  'compute':"for record in self:\n    record['x_ca_ht'] = (-record.balance) if record.account_id.account_type in ('income', 'income_other') else 0.0"},
 {'name':'x_activite','field_description':'Activité (CA)','ttype':'char','store':True,'readonly':True,
  'depends':'product_id.categ_id.complete_name,tax_line_id.name,account_id.name',
  'compute':"for record in self:\n    if record.product_id:\n        record['x_activite'] = record.product_id.categ_id.complete_name or 'Sans catégorie'\n    elif record.tax_line_id:\n        record['x_activite'] = 'Contribution ' + (record.tax_line_id.name or '')\n    else:\n        record['x_activite'] = record.account_id.name or 'Autre'"},
]
for ch in champs:
    ex=x('ir.model.fields','search',[['model','=','account.move.line'],['name','=',ch['name']]])
    if ex: print(ch['name'],': existe déjà',ex); continue
    ch.update({'model_id':mid,'state':'manual'}); t=time.time()
    try: print(ch['name'],': créé',x('ir.model.fields','create',ch),'en %.0f s'%(time.time()-t))
    except Exception as e: print(ch['name'],': réponse',str(e)[:160]); time.sleep(90); print('  présent ?',x('ir.model.fields','search',[['model','=','account.move.line'],['name','=',ch['name']]]))
ctx={'allowed_company_ids':[1,2,3,4,13]}
dom=[['company_id','=',4],['parent_state','=','posted'],['move_id.move_type','in',['out_invoice','out_refund']],['date','>=','2026-08-01'],['date','<=','2026-08-31'],['account_id.account_type','in',['income','income_other']],['display_type','in',['product','tax']]]
for r in x('account.move.line','read_group',dom,['x_ca_ht:sum','quantity:sum'],['x_activite'],lazy=False,context=ctx): print('  Haims août 2026 |',r['x_activite'],'| %.2f'%r['x_ca_ht'],'| qté %.2f'%r['quantity'])
print('total Haims août : %.2f'%sum(r['x_ca_ht'] for r in x('account.move.line','read_group',dom,['x_ca_ht:sum'],['company_id'],lazy=False,context=ctx)))
