import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),dict(k,context={'allowed_company_ids':[1,2,3,4,13]}))
# modèle : menus personnalisés existants (Poste de scan, Atelier simplifié…)
for mn in x('ir.ui.menu','search_read',[['name','in',['Poste de scan','Atelier simplifié','Plannings atelier','Suivi commandes']]],fields=['name','parent_id','action','sequence','group_ids']):
    print('menu modèle :',mn)
    if mn['action'] and mn['action'].startswith('ir.actions.act_url'):
        aid=int(mn['action'].split(',')[1]); print('   action :',x('ir.actions.act_url','read',[aid],fields=['name','url','target'])[0])
root=x('ir.ui.menu','search_read',[['parent_id','=',False],['name','in',['Inventory','Inventaire']]],fields=['name','complete_name'])
print('racine Inventaire :',root)
kids=x('ir.ui.menu','search_read',[['parent_id','=',root[0]['id']]],fields=['name','sequence'],order='sequence')
print('menus :',[(k['name'],k['sequence']) for k in kids])
K=x('ir.config_parameter','get_param','maquignon.epi_key')
ex=x('ir.ui.menu','search',[['name','=','EPI'],['parent_id','=',root[0]['id']]])
if ex:
    print('menu EPI existe déjà :',ex)
else:
    act=x('ir.actions.act_url','create',[{'name':'EPI — remise et stock','url':'/epi?k='+K,'target':'new'}])
    act=act[0] if isinstance(act,list) else act
    mid=x('ir.ui.menu','create',[{'name':'EPI','parent_id':root[0]['id'],'action':'ir.actions.act_url,%d' % act,'sequence':95}])
    mid=mid[0] if isinstance(mid,list) else mid
    print('menu EPI créé :',mid,'| action',act)
print('menus Inventaire après :',[(k['name'],k['sequence']) for k in x('ir.ui.menu','search_read',[['parent_id','=',root[0]['id']]],fields=['name','sequence'],order='sequence')])
