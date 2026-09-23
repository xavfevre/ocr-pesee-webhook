# -*- coding: utf-8 -*-
"""Colonne « Catégorie de produit » (masquée par défaut, activable via le sélecteur de colonnes) sur les lignes de facture."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),dict(k,context={'allowed_company_ids':[1,2,3,4,13]}))
NOM='account.move.form - catégorie de produit sur les lignes de facture'
base=[v for v in x('ir.ui.view','search_read',[['model','=','account.move'],['type','=','form'],['inherit_id','=',False]],fields=['xml_id']) if v['xml_id']=='account.view_move_form'][0]['id']
ex=x('ir.ui.view','search',[['name','=',NOM]])
ARCH='''<data>
  <xpath expr="//field[@name='invoice_line_ids']/list/field[@name='product_id']" position="after">
    <field name="product_category_id" string="Catégorie de produit" optional="hide"/>
  </xpath>
</data>'''
if ex:
    x('ir.ui.view','write',ex,{'arch_base':ARCH,'active':True}); vid=ex[0]; print('vue existante mise à jour :',vid)
else:
    vid=x('ir.ui.view','create',[{'name':NOM,'model':'account.move','type':'form','inherit_id':base,'mode':'extension','priority':99,'arch_base':ARCH}])
    vid=vid[0] if isinstance(vid,list) else vid; print('vue créée :',vid,'(hérite de',base,')')
# contrôle : la vue combinée contient bien la colonne
inv=x('account.move','search',[['move_type','=','out_invoice'],['state','=','posted']],limit=1,order='id desc')
v=x('account.move','get_views',[[False,'form']])
arch=v['views']['form']['arch']
i=arch.find('name="invoice_line_ids"'); seg=arch[i:arch.find('</list>',i)]
print('colonne présente dans la vue combinée :',seg.count('name="product_category_id"'),'| extrait :',seg[seg.find('product_category_id')-10:seg.find('product_category_id')+90])
