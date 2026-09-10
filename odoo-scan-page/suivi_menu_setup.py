# -*- coding: utf-8 -*-
"""Menu « Suivi commandes » réservé : groupe res.groups (Céline + administrateurs, hérité par Administration/Settings),
xmlid maquignon.group_suivi_commandes, menu Fabrication > Suivi commandes (2 sous-menus URL)."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
GS=4  # base.group_system (Administration / Settings)
admins=x('res.users','search',[['group_ids','in',[GS]],['share','=',False]])
celine=x('res.users','search',[['login','=','celine@maquignon.com']])
g=x('res.groups','search',[['name','=','Suivi commandes (Maquignon)']])
if not g:
    g=[x('res.groups','create',{'name':'Suivi commandes (Maquignon)','comment':'Accès au Suivi devis/commande et au Suivi facturation (pages web). Administrateurs + Céline.'})]
    print('groupe créé',g)
x('res.groups','write',g,{'user_ids':[[6,0,sorted(set(admins+celine))]]})
print('groupe',g,'utilisateurs :',[u['name'] for u in x('res.users','read',sorted(set(admins+celine)),fields=['name'])])
# hérité par les administrateurs (Settings) -> les futurs admins l'auront
try:
    x('res.groups','write',[GS],{'implied_ids':[[4,g[0]]]}); print('hérité par Administration/Settings')
except Exception as e: print('implied_ids non modifié :',str(e).strip().split('\n')[-1][:150])
if not x('ir.model.data','search',[['module','=','maquignon'],['name','=','group_suivi_commandes']]):
    x('ir.model.data','create',{'module':'maquignon','name':'group_suivi_commandes','model':'res.groups','res_id':g[0],'noupdate':True}); print('xmlid maquignon.group_suivi_commandes créé')
# menus
def act(name,url):
    a=x('ir.actions.act_url','search',[['name','=',name]])
    return a[0] if a else x('ir.actions.act_url','create',{'name':name,'url':url,'target':'new'})
mn=x('ir.ui.menu','search',[['name','=','Suivi commandes'],['parent_id','=',729]])
if not mn:
    mn=[x('ir.ui.menu','create',{'name':'Suivi commandes','parent_id':729,'sequence':8,'group_ids':[[6,0,g]]})]; print('menu créé',mn)
else: x('ir.ui.menu','write',mn,{'group_ids':[[6,0,g]]})
for seq,name,url in [(1,'📋 Suivi devis/commande','/planning-suivi-commande'),(2,'💶 Suivi facturation','/of-non-facture')]:
    if not x('ir.ui.menu','search',[['name','=',name],['parent_id','=',mn[0]]]):
        print('sous-menu',name,x('ir.ui.menu','create',{'name':name,'parent_id':mn[0],'sequence':seq,'action':'ir.actions.act_url,%d'%act('Suivi : '+name.split(' ',1)[1],url),'group_ids':[[6,0,g]]}))
print('menus :',x('ir.ui.menu','search_read',[['id','child_of',mn]],fields=['name','parent_id','action','group_ids','sequence']))
