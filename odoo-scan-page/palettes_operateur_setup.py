# -*- coding: utf-8 -*-
"""Palettes par opérateur v2 (16/09/2026) — « une palette = un opérateur » :
 1) champ stock.package.x_operateur_id (many2one hr.employee) : opérateur responsable (a ouvert la palette)
 2) reprise : palettes ayant déjà des opérateurs (x_operateur_ids) -> premier = responsable
 3) formulaire colis 7896 : champs Opérateur / Opérateurs ayant posé / clôturée / zone visibles au bureau
 4) liste colis : colonne Opérateur (vue héritée créée si absente)
 5) bon de colisage 7898 : ligne « Opérateur »"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
mid=lambda model: x('ir.model','search',[['model','=',model]])[0]
# 1) champ
f=x('ir.model.fields','search',[['model','=','stock.package'],['name','=','x_operateur_id']])
if f:
    print('x_operateur_id : existe déjà', f)
else:
    vals={'name':'x_operateur_id','field_description':'Opérateur (responsable de la palette)','ttype':'many2one',
          'relation':'hr.employee','on_delete':'set null','model_id':mid('stock.package'),'state':'manual','index':True}
    try:
        print('x_operateur_id : créé', x('ir.model.fields','create',vals))
    except Exception as e:
        print('création : réponse', str(e)[:200])
        import time; time.sleep(120)
        f=x('ir.model.fields','search',[['model','=','stock.package'],['name','=','x_operateur_id']])
        print('après attente :', f)
# 2) reprise
pk=x('stock.package','search_read',[['x_operateur_ids','!=',False],['x_operateur_id','=',False]],fields=['name','x_operateur_ids'],order='id')
for r in pk:
    first=sorted(r['x_operateur_ids'])[0]
    x('stock.package','write',[r['id']],{'x_operateur_id':first})
    print('reprise',r['name'],'->',first)
# 3) formulaire 7896
v=x('ir.ui.view','read',[7896],fields=['arch_db'])[0]['arch_db']
if 'x_operateur_id' not in v:
    new=v.replace('<field name="x_studio_cubage" widget="float" digits="[16,3]"/>',
                  '<field name="x_operateur_id"/>\n    <field name="x_operateur_ids" widget="many2many_tags" readonly="1"/>\n    <field name="x_studio_cloturee"/>\n    <field name="x_studio_zone"/>\n    <field name="x_studio_cubage" widget="float" digits="[16,3]"/>')
    assert new!=v
    x('ir.ui.view','write',[7896],{'arch_db':new}); print('formulaire 7896 : champs ajoutés')
else: print('formulaire 7896 : déjà à jour')
# 4) liste
la=x('ir.ui.view','read',[1904],fields=['arch_db'])[0]['arch_db']
print('liste 1904 :',la[:600].replace('\n',' '))
ex=x('ir.ui.view','search',[['key','=','maquignon.package_list_operateur']])
if ex: print('liste opérateur : existe',ex)
else:
    anchor='name' if 'name="name"' in la else None
    if anchor:
        arch='<data>\n  <xpath expr="//field[@name=\'name\']" position="after">\n    <field name="x_operateur_id" optional="show"/>\n    <field name="x_studio_cloturee" optional="show"/>\n    <field name="x_studio_zone" optional="show"/>\n  </xpath>\n</data>'
        vid=x('ir.ui.view','create',{'name':'Palette - opérateur (liste)','key':'maquignon.package_list_operateur','model':'stock.package','type':'list','inherit_id':1904,'mode':'extension','arch_db':arch,'priority':99})
        print('liste opérateur : vue créée',vid)
    else: print('liste : ancre name introuvable, pas de colonne ajoutée')
# 5) rapport 7898
r=x('ir.ui.view','read',[7898],fields=['arch_db'])[0]['arch_db']
old='<div class="col-4" t-if="o.x_studio_zone"><strong>Emplacement :</strong> <span t-out="o.x_studio_zone"/></div>'
if 'x_operateur_id' in r: print('rapport 7898 : déjà à jour')
else:
    assert r.count(old)==1
    x('ir.ui.view','write',[7898],{'arch_db':r.replace(old, old+'\n            <div class="col-2" t-if="o.x_operateur_id"><strong>Opérateur :</strong> <span t-out="o.x_operateur_id.name"/></div>')})
    print('rapport 7898 : ligne Opérateur ajoutée')
print('contrôle :',x('stock.package','search_read',[['x_operateur_id','!=',False]],fields=['name','x_operateur_id','x_studio_cloturee'],order='id'))
