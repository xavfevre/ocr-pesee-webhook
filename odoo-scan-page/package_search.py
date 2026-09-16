import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
vs=x('ir.ui.view','search_read',[['model','=','stock.package'],['type','=','search']],fields=['id','name','key','inherit_id','arch_db'],order='id')
for v in vs: print(v['id'],v['name'],v['key'],'hérite',v['inherit_id'] and v['inherit_id'][0]); 
base=[v for v in vs if not v['inherit_id']][0]
print('--- base',base['id']); print(base['arch_db'][:1500])
ex=x('ir.ui.view','search',[['key','=','maquignon.package_search_operateur']])
if ex: print('déjà :',ex)
else:
    anchor = "//field[@name='name']" if 'name="name"' in base['arch_db'] else "//search/field[1]"
    arch=('<data>\n  <xpath expr="%s" position="after">\n    <field name="x_operateur_id"/>\n    <field name="x_studio_zone"/>\n  </xpath>\n'
          '  <xpath expr="//search" position="inside">\n    <filter name="ouvertes" string="Palettes ouvertes" domain="[(\'x_studio_cloturee\',\'!=\',True)]"/>\n'
          '    <filter name="cloturees" string="Palettes clôturées" domain="[(\'x_studio_cloturee\',\'=\',True)]"/>\n'
          '    <filter name="grp_operateur" string="Opérateur" context="{\'group_by\': \'x_operateur_id\'}"/>\n  </xpath>\n</data>') % anchor
    vid=x('ir.ui.view','create',{'name':'Palette - recherche opérateur','key':'maquignon.package_search_operateur','model':'stock.package','type':'search','inherit_id':base['id'],'mode':'extension','arch_db':arch,'priority':99})
    print('vue recherche créée',vid)
