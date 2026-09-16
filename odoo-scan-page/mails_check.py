import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
for mm in x('mail.mail','search_read',[['subject','ilike','Commandes entièrement produites']],fields=['id','subject','email_from','email_to','state','failure_reason','failure_type','date','message_id','mail_server_id','author_id'],order='id desc',limit=5):
    print('mail',mm['id'],mm['date'][:16],'| de',mm['email_from'],'| à',mm['email_to'],'| état',mm['state'],'| échec',mm['failure_type'],(mm['failure_reason'] or '')[:150],'| serveur',mm['mail_server_id'])
print('--- mails « Palette clôturée » (qui arrivent) :')
for mm in x('mail.mail','search_read',[['subject','ilike','Palette clôturée']],fields=['email_from','email_to','state','mail_server_id','author_id'],order='id desc',limit=2):
    print('  de',mm['email_from'],'| à',mm['email_to'],'| état',mm['state'],'| serveur',mm['mail_server_id'],'| auteur',mm['author_id'])
t=x('mail.template','read',[116],fields=['email_from','mail_server_id'])[0]; print('template 116 : de',t['email_from'],'| serveur',t['mail_server_id'])
print('serveurs sortants :',x('ir.mail_server','search_read',[],fields=['name','smtp_host','from_filter','active']))
print('mail.default.from :',x('ir.config_parameter','get_param','mail.default.from',''),'| catchall.domain :',x('ir.config_parameter','get_param','mail.catchall.domain',''))
print('société :',x('res.company','read',[1],fields=['email','name'])[0])
