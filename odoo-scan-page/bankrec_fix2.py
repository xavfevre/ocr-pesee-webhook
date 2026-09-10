# -*- coding: utf-8 -*-
"""Rapprochement bancaire « Oups » : les écritures des lignes de relevé non lettrées ont leur contrepartie sur
l'ancien compte d'attente (471000 « Suspense accounts ») alors que le journal attend désormais son suspense_account_id.
  python bankrec_fix2.py <journal_id> info : compte les lignes à migrer (rien n'est écrit)
  python bankrec_fix2.py <journal_id> one  : migre UNE ligne (la plus récente) et vérifie
  python bankrec_fix2.py <journal_id> all  : migre toutes les lignes non lettrées du journal"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
CTX={'allowed_company_ids':[1,2,3,4,13]}
def x(mo,me,*a,**k): k.setdefault('context',CTX); return m.execute_kw(D,uid,p,mo,me,list(a),k)
JOURNAL=int(sys.argv[1]); mode=sys.argv[2]
j=x('account.journal','read',[JOURNAL],fields=['name','company_id','suspense_account_id','default_account_id'])[0]
NEW=j['suspense_account_id'][0]; BANK=j['default_account_id'][0]
print('journal',JOURNAL,j['name'],'|',j['company_id'][1],'| compte d attente attendu :',j['suspense_account_id'][1])
lines=x('account.bank.statement.line','search_read',[['journal_id','=',JOURNAL],['is_reconciled','=',False]],fields=['date','payment_ref','amount','move_id'],order='date desc, id desc')
todo=[]
for l in lines:
    mls=[ml for ml in x('account.move.line','search_read',[['move_id','=',l['move_id'][0]],['account_id','not in',[NEW,BANK]]],fields=['account_id','debit','credit','reconciled','account_type' if False else 'name'])]
    # contrepartie « d'attente » = compte de type 471xxx / Suspense accounts, non lettré
    old=[ml for ml in mls if not ml['reconciled'] and ('Suspense' in ml['account_id'][1] or ml['account_id'][1].startswith('471'))]
    if old: todo.append((l,old))
print('lignes non lettrées :',len(lines),'| à migrer :',len(todo),'| anciens comptes :',sorted(set(ml['account_id'][1] for l,o in todo for ml in o)))
if mode=='info' or not todo: sys.exit(0)
if mode=='one': todo=todo[:1]
n=0
for l,old in todo:
    x('account.move.line','write',[ml['id'] for ml in old],{'account_id':NEW}); n+=1
    if mode=='one':
        print('OK :',l['date'],(l['payment_ref'] or '')[:60],l['amount'],'-> lignes',[ml['id'] for ml in old],'sur',j['suspense_account_id'][1])
        print('relecture :',x('account.move.line','read',[ml['id'] for ml in old],fields=['account_id']))
print('lignes migrées :',n)
