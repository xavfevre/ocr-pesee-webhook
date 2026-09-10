# -*- coding: utf-8 -*-
"""Site Chatel Granulats (website 4) : pas de prix dans la liste déroulante de recherche
(vue héritée de website.website_search_box_input, propre au site, data-display-detail = false)."""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
base={'id':654,'name':'website.website_search_box_input (vue primaire, celle qui pose data-display-detail)'}; print('vue de base :',base)
arch="""<data>
  <!-- Chatel Granulats : la recherche ne doit pas afficher les prix (le « détail » = prix) -->
  <xpath expr="//input[@type='search']" position="attributes">
    <attribute name="t-att-data-display-detail">'false'</attribute>
  </xpath>
</data>"""
key='website.chatel_search_sans_prix'
v=x('ir.ui.view','search',[['key','=',key]])
if v: x('ir.ui.view','write',v,{'arch_db':arch}); print('vue mise à jour',v)
else:
    v=[x('ir.ui.view','create',{'name':'Chatel Granulats : recherche sans prix','key':key,'type':'qweb','mode':'extension','inherit_id':base['id'],'website_id':4,'priority':99,'arch_db':arch,'active':True})]; print('vue créée',v)
io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'ocr','odoo-scan-page','chatel_search_sans_prix.xml'),'w',encoding='utf-8',newline='\n').write(arch)
