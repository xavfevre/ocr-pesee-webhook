# -*- coding: utf-8 -*-
"""Tableau de bord 23 v6 : CA = toutes les écritures validées sur comptes de produits (factures, avoirs, clôtures de
caisse du Point de Vente, écritures diverses) — comme la balance Sage. Usage : python dash23_v6.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
js=json.loads(io.open('audit/dash23.AFTER_v5.json',encoding='utf-8').read()); sh=js['sheets'][0]
DOM=['&','&',['parent_state','=','posted'],['account_id.account_type','in',['income','income_other']],['display_type','in',['product','tax']]]
for pid in ('2','3','4'):
    assert js['pivots'][pid]['model']=='account.move.line'; js['pivots'][pid]['domain']=DOM
for fg in sh['figures']: fg['data']['searchParams']['domain']=DOM
sh['cells']['A2']='Toutes les écritures validées sur comptes de produits (factures, avoirs, caisse) — ventes + contributions TGAP/REP · filtres Période / Société / Catégorie en haut'
data=json.dumps(js,ensure_ascii=False); io.open('audit/dash23.AFTER_v6.json','w',encoding='utf-8').write(data)
print('domaines mis à jour :',[p_ for p_ in js['pivots'] if js['pivots'][p_]['domain']==DOM],'+',len(sh['figures']),'graphiques')
if mode=='apply': x('spreadsheet.dashboard','write',[23],{'spreadsheet_data':data}); print('tableau de bord 23 mis à jour (v6)')
