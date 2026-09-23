# -*- coding: utf-8 -*-
"""Champs RH pour la saisie directe des récups / sans solde : x_heures_jour.x_h_recup, x_h_sans_solde (float)
et valeur de sélection 'sans_solde' sur x_type.   Usage : python champs_rh.py test|prod"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'test').lower()
U,D=('https://testmaq230926v2.odoo.com','testmaq230926v2') if mode=='test' else ('https://maquignon.odoo.com','maquignon')
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),dict(k,context={'allowed_company_ids':[1,2,3,4,13]}))
mid=x('ir.model','search',[['model','=','x_heures_jour']])[0]
for name,desc,tt in (('x_h_recup','Heures prises en récup','float'),('x_h_sans_solde','Heures sans solde','float'),('x_hs_payees','Heures sup payées (pas en récup)','boolean')):
    ex=x('ir.model.fields','search',[['model_id','=',mid],['name','=',name]])
    if ex: print(name,': existe déjà',ex); continue
    fid=x('ir.model.fields','create',[{'model_id':mid,'name':name,'ttype':tt,'field_description':desc,'state':'manual','store':True,'copied':True}])
    print(name,': créé',fid)
ft=x('ir.model.fields','search',[['model_id','=',mid],['name','=','x_type']])[0]
ex=x('ir.model.fields.selection','search',[['field_id','=',ft],['value','=','sans_solde']])
if ex: print('sans_solde : existe déjà',ex)
else: print('sans_solde : créé',x('ir.model.fields.selection','create',[{'field_id':ft,'value':'sans_solde','name':'Sans solde','sequence':7}]))
print('contrôle :',{k:v['string'] for k,v in x('x_heures_jour','fields_get',attributes=['string']).items() if k in ('x_h_recup','x_h_sans_solde','x_hs_payees')},'| x_type :',[s[0] for s in x('x_heures_jour','fields_get',attributes=['selection'])['x_type']['selection']])
