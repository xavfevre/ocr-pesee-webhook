# -*- coding: utf-8 -*-
"""Chauffeurs SFM sélectionnables sur les demandes de transport Maquignon :
 1) tous les utilisateurs internes reçoivent SFM (13) dans leurs sociétés autorisées (sans changer leur société courante)
 2) vue formulaire 4380 : champs Chauffeur / Opérateurs cherchent dans les sociétés Maquignon + SFM (context allowed_company_ids)"""
import os, ssl, sys, io, xmlrpc.client
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
here=os.path.dirname(os.path.abspath(__file__))
users=x('res.users','search_read',[['share','=',False],['company_ids','not in',[13]]],fields=['login','company_id'])
for u in users:
    x('res.users','write',[u['id']],{'company_ids':[[4,13]]})
print('SFM ajoutée aux sociétés autorisées de :',[u['login'] for u in users])
v=x('ir.ui.view','read',[4380],fields=['arch_db'])[0]['arch_db']
io.open(os.path.join(here,'live_4380.BEFORE.xml'),'w',encoding='utf-8',newline='\n').write(v)
CTX=' context="{\'allowed_company_ids\': [1, 13]}"'
n=0
for f in ['x_studio_chauffeur','x_studio_operateurs']:
    old='<field name="%s"'%f
    if 'allowed_company_ids' not in v.split(old,1)[1].split('/>',1)[0]:
        v=v.replace(old, old+CTX,1); n+=1
ET.fromstring(v.encode('utf-8'))
x('ir.ui.view','write',[4380],{'arch_db':v}); print('vue 4380 : contexte sociétés ajouté sur',n,'champ(s)')
io.open(os.path.join(here,'ocr','odoo-scan-page','task_form_4380.xml'),'w',encoding='utf-8',newline='\n').write(v)
for l in v.split('\n'):
    if 'x_studio_chauffeur"' in l or 'x_studio_operateurs' in l: print('   ',l.strip()[:260])
print('chauffeurs proposés :',[nm for i,nm in x('hr.employee','name_search','',[['category_ids','=',[3]]],'ilike',30,context={'allowed_company_ids':[1,13]})])
