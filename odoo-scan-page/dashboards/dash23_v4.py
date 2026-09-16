# -*- coding: utf-8 -*-
"""Tableau de bord 23 v4 : comptes comptables affichés — tableau société › compte › activité, camembert par compte,
évolution mensuelle par société › compte. Usage : python dash23_v4.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
js=json.loads(io.open('audit/dash23.AFTER_v3.json',encoding='utf-8').read()); sh=js['sheets'][0]
js['pivots']['2']['rows']=[{'fieldName':'company_id'},{'fieldName':'account_id'},{'fieldName':'x_activite'}]
js['pivots']['2']['name']='CA par compte et activité (écritures)'
js['pivots']['3']['rows']=[{'fieldName':'company_id'},{'fieldName':'account_id'}]
js['pivots']['3']['name']='CA par mois et compte (écritures)'
sh['cells']['A40']='DÉTAIL PAR SOCIÉTÉ, COMPTE COMPTABLE ET ACTIVITÉ (CA HT + quantités, contributions incluses)'
sh['cells']['A41']='=PIVOT(2, 120, TRUE, TRUE)'
sh['cells']['A770']='ÉVOLUTION MENSUELLE — CA HT par société et compte comptable'
for fg in sh['figures']:
    if fg['id']=='chart-ca-cat':
        fg['data']['metaData']['groupBy']=['account_id']; fg['data']['searchParams']['groupBy']=['account_id']
        fg['data']['title']={'text':'Répartition du CA par compte comptable'}
sh['cols']['0']={'size':360}
data=json.dumps(js,ensure_ascii=False); io.open('audit/dash23.AFTER_v4.json','w',encoding='utf-8').write(data)
print('pivot 2 :',js['pivots']['2']['rows'],'| pivot 3 :',js['pivots']['3']['rows'])
if mode=='apply': x('spreadsheet.dashboard','write',[23],{'spreadsheet_data':data}); print('tableau de bord 23 mis à jour (v4)')
