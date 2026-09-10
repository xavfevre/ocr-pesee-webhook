# -*- coding: utf-8 -*-
"""Chauffeurs SFM sur les demandes de transport : à l'enregistrement, Odoo revérifie le droit de lecture
des employés choisis avec la société active de la session -> « Erreur d'accès ».
Correctif : la règle multi-société des employés (ir.rule 79) rend lisibles par tous les employés
de SFM (société 13) étiquetés « Chauffeur » (catégorie 3). Rien d'autre ne change."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
r=x('ir.rule','read',[79],fields=['name','domain_force'])[0]
print('règle :',r['name']); print('AVANT :'); print(r['domain_force'])
old=r['domain_force']
if 'category_ids' in old:
    print('déjà modifiée, rien à faire')
else:
    new=old.replace("['|', '|', '|',", "['|', '|', '|', '|',\n            '&', ('company_id', '=', 13), ('category_ids', 'in', [3]),", 1)
    assert new != old, "forme de la règle inattendue"
    x('ir.rule','write',[79],{'domain_force':new})
    print('APRÈS :'); print(x('ir.rule','read',[79],fields=['domain_force'])[0]['domain_force'])
print('contrôle, société Maquignon seule -> chauffeurs SFM lisibles :',
      [e['name'] for e in x('hr.employee','search_read',[['company_id','=',13],['category_ids','in',[3]]],fields=['name'],context={'allowed_company_ids':[1]})])
