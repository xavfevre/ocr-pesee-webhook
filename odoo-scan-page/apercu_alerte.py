import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0,'ocr'); import web_actions as wa
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
def call(model, method, *params, **kw): return m.execute_kw(D,uid,p,model,method,list(params),kw)
r=wa._alerte_palettes(call,{})
html='<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Palettes : point hebdo (aperçu)</title><style>body{font-family:Arial,sans-serif;max-width:860px;margin:24px auto;color:#0f172a;line-height:1.45}h3{color:#01666B;margin-top:22px}</style></head><body><p style="background:#fef3c7;padding:8px 12px;border-radius:8px">Aperçu du mail automatique du lundi (objet : « Palettes : point hebdo du JJ/MM/AAAA », destinataire : isabelle@maquignon.com).</p>'+r['html']+'</body></html>'
io.open('C:/Users/xavfe/Desktop/Maquignon/Apercu_mail_palettes_hebdo.html','w',encoding='utf-8').write(html)
print('aperçu écrit :',r['n_ops'],'opérateurs,',r['n_of'],'OF,',r['n_dormantes'],'palettes dormantes')
