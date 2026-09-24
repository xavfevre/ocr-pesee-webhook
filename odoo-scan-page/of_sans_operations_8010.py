# -*- coding: utf-8 -*-
"""Rapport « Ordre de Fabrication » (mrp.report_mrporder_copy_2, vue 6635) : section « Opérations » retirée
(les opérateurs travaillent sur tablette). Héritage désactivable. Contrôle : PDF d'un OF via la route /report/pdf."""
import os, ssl, sys, io, xmlrpc.client, requests
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),dict(k,context={'allowed_company_ids':[1,2,3,4,13]}))
arch=x('ir.ui.view','read',[6635],fields=['arch_db'])[0]['arch_db']
print('occurrences t-if="item.workorder_ids" :',arch.count('t-if="item.workorder_ids"'),'| commentaire Section Opérations :',arch.count('<!-- Section Opérations -->'))
NOM='report_mrporder copy(2) - sans opérations (tablettes)'
ARCH='''<data>
  <xpath expr="//t[@t-if='item.workorder_ids']" position="replace"/>
</data>'''
ex=x('ir.ui.view','search',[['name','=',NOM]])
if ex:
    x('ir.ui.view','write',ex,{'arch_base':ARCH,'active':True}); vid=ex[0]; print('héritage mis à jour',vid)
else:
    vid=x('ir.ui.view','create',[{'name':NOM,'type':'qweb','inherit_id':6635,'mode':'extension','priority':99,'arch_base':ARCH}])
    vid=vid[0] if isinstance(vid,list) else vid; print('héritage créé',vid)
# contrôle : PDF de l'OF de la capture
of=x('mrp.production','search_read',[['name','=','WH/OF/09671']],fields=['name'],limit=1)
if of:
    s=requests.Session()
    s.post(U+'/web/session/authenticate',json={'jsonrpc':'2.0','method':'call','params':{'db':D,'login':us,'password':p}},timeout=60)
    r=s.get(U+'/report/pdf/mrp.report_mrporder_copy_2/%d' % of[0]['id'],timeout=180)
    import pymupdf
    doc=pymupdf.open(stream=r.content,filetype='pdf'); txt=''.join(pg.get_text() for pg in doc)
    print('PDF',of[0]['name'],':',len(doc),'page(s) |','Opérations' in txt and 'section Opérations ENCORE présente' or 'section Opérations absente','|','Sciage secondaire' in txt and 'ligne d\'opération encore là' or 'OK','| extrait :',txt[:160].replace('\n',' '))
    open('captures_epi/of_09671.pdf','wb').write(r.content)
