import os, ssl, sys, xmlrpc.client, random
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
for k,v in (('maquignon.palette_code_chef', str(random.randint(1000,9999))), ('maquignon.palettes_alerte_email','isabelle@maquignon.com')):
    ex=x('ir.config_parameter','search_read',[['key','=',k]],fields=['value'])
    if ex: print(k,'existe :',ex[0]['value'])
    else: x('ir.config_parameter','create',{'key':k,'value':v}); print(k,'créé =',v)
