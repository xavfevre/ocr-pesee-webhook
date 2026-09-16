# -*- coding: utf-8 -*-
"""Tableau de bord 23 v5 : retour à la vue par activité à gauche (v3), comptes comptables seulement dans le tableau
de droite ; titres raccourcis pour ne pas se chevaucher. Usage : python dash23_v5.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
js=json.loads(io.open('audit/dash23.AFTER_v3.json',encoding='utf-8').read()); sh=js['sheets'][0]
assert js['pivots']['2']['rows']==[{'fieldName':'company_id'},{'fieldName':'x_activite'}]
sh['cells']['A40']='DÉTAIL PAR SOCIÉTÉ ET ACTIVITÉ (CA HT + quantités)'
sh['cells']['E40']='DÉTAIL PAR COMPTE COMPTABLE (= balance Sage)'
data=json.dumps(js,ensure_ascii=False); io.open('audit/dash23.AFTER_v5.json','w',encoding='utf-8').write(data)
print('pivot 2 :',js['pivots']['2']['rows'],'| pie :',[fg['data']['metaData']['groupBy'] for fg in sh['figures'] if fg['id']=='chart-ca-cat'])
if mode=='apply': x('spreadsheet.dashboard','write',[23],{'spreadsheet_data':data}); print('tableau de bord 23 mis à jour (v5)')
