# -*- coding: utf-8 -*-
"""Écritures de banque fictives « Rapprochement Sage — … » créées par l'outil sur des banques connectées
(doublon de la vraie ligne de relevé). Pour chacune : délettrage de sa ligne 511900, passage en brouillon
et suppression ; puis rapprochement du paiement avec la vraie ligne de relevé si elle est retrouvée
(même journal, même montant, ± 15 jours).   Modes : dry | apply"""
import os, ssl, sys, datetime as dt, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
CTX={'allowed_company_ids':[1,2,3,4]}
def x(mo,me,*a,**k): k.setdefault('context',CTX); return m.execute_kw(D,uid,p,mo,me,list(a),k)
mode=sys.argv[1]
print('verrous :',[(co['name'],co.get('fiscalyear_lock_date'),co.get('hard_lock_date'),co.get('sale_lock_date')) for co in x('res.company','search_read',[],fields=['name','fiscalyear_lock_date','hard_lock_date','sale_lock_date'])])
fakes=x('account.move','search_read',[['ref','ilike','Rapprochement Sage —'],['state','=','posted']],fields=['name','ref','date','journal_id','amount_total','company_id'],order='id')
jinfo={}
def infos(jid):
    if jid not in jinfo:
        j=x('account.journal','read',[jid],fields=['default_account_id','suspense_account_id'])[0]
        jinfo[jid]=(j['default_account_id'][0], j['suspense_account_id'][0] if j['suspense_account_id'] else None)
    return jinfo[jid]
plan=[]
for mv in fakes:
    bank,att=infos(mv['journal_id'][0])
    lines=x('account.move.line','search_read',[['move_id','=',mv['id']]],fields=['account_id','debit','credit','matched_debit_ids','matched_credit_ids'])
    l_att=[l for l in lines if l['account_id'][0]!=bank]
    partiels=[pid for l in l_att for pid in l['matched_debit_ids']+l['matched_credit_ids']]
    pays=set()
    for pr in x('account.partial.reconcile','read',partiels,fields=['debit_move_id','credit_move_id']):
        for k in ('debit_move_id','credit_move_id'):
            ml=x('account.move.line','read',[pr[k][0]],fields=['move_id','payment_id'])[0]
            if ml['payment_id']: pays.add(ml['payment_id'][0])
    d0=dt.date.fromisoformat(mv['date'])
    cands=[s for s in x('account.bank.statement.line','search_read',[['journal_id','=',mv['journal_id'][0]],['is_reconciled','=',False],['amount','=',mv['amount_total']]],fields=['date','amount','payment_ref','move_id']) if abs((dt.date.fromisoformat(s['date'])-d0).days)<=15]
    plan.append((mv,sorted(pays),partiels,cands,att,bank))
    print('%-16s %-12s %s %9.2f | %s | paiement(s) %s | relevé : %s' % (mv['name'],mv['journal_id'][1][:12],mv['date'],mv['amount_total'],mv['ref'][21:60],sorted(pays),[(s['date'],s['payment_ref'][:30]) for s in cands] or 'AUCUN (le paiement restera « en cours »)'))
print('écritures fictives :',len(plan),'| avec ligne de relevé retrouvée :',sum(1 for pl in plan if pl[3]))
if mode!='apply': sys.exit(0)
ok=err=0
for mv,pays,partiels,cands,att,bank in plan:
    try:
        if partiels: x('account.partial.reconcile','unlink',partiels)
        x('account.move','button_draft',[mv['id']]); x('account.move','unlink',[mv['id']])
        if cands and pays:
            s=cands[0]
            moves=[pp['move_id'][0] for pp in x('account.payment','read',pays,fields=['move_id']) if pp['move_id']]
            l_pay=x('account.move.line','search',[['move_id','in',moves],['account_id','=',att],['reconciled','=',False]])
            l_stmt=[]
            for ml in x('account.move.line','search_read',[['move_id','=',s['move_id'][0]],['reconciled','=',False]],fields=['account_id','credit']):
                if ml['account_id'][0]!=bank and ml['credit']>0:
                    if ml['account_id'][0]!=att: x('account.move.line','write',[ml['id']],{'account_id':att})
                    l_stmt.append(ml['id'])
            if l_pay and l_stmt: x('account.move.line','reconcile',l_pay+l_stmt); tag='rapproché avec le relevé du %s'%s['date']
            else: tag='paiement laissé « en cours »'
        else: tag='paiement laissé « en cours »'
        ok+=1; print('OK',mv['name'],mv['amount_total'],'->',tag)
    except Exception as e:
        err+=1; print('ERREUR',mv['name'],':',str(e).strip().split('\n')[-1][:200])
print('supprimées :',ok,'| erreurs :',err)
