import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
k='maquignon.palette_max_kg'
ex=x('ir.config_parameter','search_read',[['key','=',k]],fields=['value'])
if ex: print('paramètre existant :',ex)
else: print('créé',x('ir.config_parameter','create',{'key':k,'value':'1500'}))
print('get_param ->',x('ir.config_parameter','get_param',k,'1500'))
