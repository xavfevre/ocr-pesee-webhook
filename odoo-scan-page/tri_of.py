# -*- coding: utf-8 -*-
"""Listes OF et OT triées par défaut sur le numéro d'OF.
 - mrp.workorder : champ x_of_num (related production_id.name, stocké) pour pouvoir trier par numéro d'OF
 - vues héritées (priorité 10001) posant default_order sur la racine <list> des listes OF (5186) et OT (5153)"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
here=os.path.dirname(os.path.abspath(__file__))
f=x('ir.model.fields','search',[['model','=','mrp.workorder'],['name','=','x_of_num']])
if f: print('champ x_of_num : existe', f)
else:
    mid=x('ir.model','search',[['model','=','mrp.workorder']])[0]
    print('champ x_of_num créé :', x('ir.model.fields','create',{'model_id':mid,'name':'x_of_num','field_description':"N° d'OF",'ttype':'char','related':'production_id.name','store':True,'state':'manual'}), flush=True)
print('exemple :', x('mrp.workorder','search_read',[],fields=['name','x_of_num'],limit=2,order='x_of_num desc'))
for key,name,inh,order in [('mrp.of_list_tri_of','OF : tri par défaut sur le numéro',5186,'name asc'),
                           ('mrp.ot_list_tri_of',"OT : tri par défaut sur le numéro d'OF",5153,'x_of_num asc, sequence asc, id asc')]:
    arch='<data>\n  <xpath expr="//list" position="attributes"><attribute name="default_order">%s</attribute></xpath>\n</data>'%order
    v=x('ir.ui.view','search',[['key','=',key]])
    if v: x('ir.ui.view','write',v,{'arch_db':arch}); print('vue mise à jour',v,key)
    else: v=[x('ir.ui.view','create',{'name':name,'key':key,'type':'list','model':'mrp.production' if inh==5186 else 'mrp.workorder','mode':'extension','inherit_id':inh,'priority':10001,'arch_db':arch})]; print('vue créée',v,key)
    io.open(os.path.join(here,'ocr','odoo-scan-page',key.replace('.','_')+'.xml'),'w',encoding='utf-8',newline='\n').write(arch)
for model,vid in [('mrp.production',5186),('mrp.workorder',5153)]:
    ga=x(model,'get_views',[[vid,'list']])['views']['list']['arch']
    import re; print(model,'racine :',re.search(r'<list[^>]*>',ga).group(0)[:200])
