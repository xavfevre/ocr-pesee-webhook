import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0,'ocr'); import web_actions as wa
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
def call(model, method, *params, **kw): return m.execute_kw(D,uid,p,model,method,list(params),kw)
r=wa._alerte_palettes(call,{'envoyer_celine':1})
print('renvoyé à', r.get('envoye_celine_a'), '|', r.get('n_commandes_produites'), 'commande(s)')
for mm in call('mail.mail','search_read',[['subject','ilike','Commandes entièrement produites']],fields=['id','email_from','email_to','state','author_id','date'],order='id desc',limit=1):
    print('  mail', mm['id'], mm['date'][:16], '| de', mm['email_from'], '| à', mm['email_to'], '| état', mm['state'], '| auteur', mm['author_id'])
