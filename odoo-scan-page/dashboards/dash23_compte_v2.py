# -*- coding: utf-8 -*-
"""Tableau de bord 23 : bloc « Détail par compte comptable » placé à droite du tableau par activité (H40),
à partir de la sauvegarde d'origine (audit/dash23.BEFORE.json). Usage : python dash23_compte_v2.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
js=json.loads(io.open('audit/dash23.BEFORE.json',encoding='utf-8').read())
sh=js['sheets'][0]
assert '4' not in js['pivots'] and sh['cells'].get('A165','').startswith('CA PAR ARTICLE')
st_titre = sh['styles'].get('A40:F40') or sh['styles'].get('A40') or 3
# le tableau par activité occupe A..C ; le bloc par compte prend E..I, à la même hauteur
sh['cells']['E40']='DÉTAIL PAR COMPTE COMPTABLE — ventes + contributions TGAP/REP (= balance Sage)'
sh['cells']['E41']='=PIVOT(4, 120, TRUE, TRUE)'
if 'A40:F40' in sh['styles']:
    sh['styles']['A40:D40']=sh['styles'].pop('A40:F40')
sh['merges']=[z for z in sh['merges'] if z!='A40:F40']+['A40:D40','E40:I40']
sh['styles']['E40:I40']=st_titre
cols=sh.setdefault('cols',{})
cols['4']={'size':300}                     # E : libellé société / compte
for i in ('5','6','7','8'): cols[i]={'size':115}
js['pivots']['4']={'type':'ODOO','model':'account.move.line','name':'CA par compte comptable','formulaId':'4',
    'rows':[{'fieldName':'company_id'},{'fieldName':'account_id'}],'columns':[],
    'measures':[{'id':'credit','fieldName':'credit','aggregator':'sum','userDefinedName':'Crédit'},
                {'id':'debit','fieldName':'debit','aggregator':'sum','userDefinedName':'Débit'},
                {'id':'ca_net','fieldName':'ca_net','aggregator':'sum','userDefinedName':'CA HT net','computedBy':{'sheetId':sh['id'],'formula':'=credit-debit'}},
                {'id':'quantity','fieldName':'quantity','aggregator':'sum','userDefinedName':'Qté'}],
    'domain':['&','&','&',['parent_state','=','posted'],['move_id.move_type','in',['out_invoice','out_refund']],['account_id.account_type','in',['income','income_other']],['display_type','in',['product','tax']]],
    'context':{},'sortedColumn':None,
    'fieldMatching':{'flt_period':{'chain':'date','type':'date','offset':0},'flt_company':{'chain':'company_id','type':'many2one'},'flt_categ':{'chain':'product_id.categ_id','type':'many2one'}}}
js['pivotNextId']=5
data=json.dumps(js,ensure_ascii=False)
io.open('audit/dash23.AFTER_v2.json','w',encoding='utf-8').write(data)
print('cellules :',{k:str(v)[:60] for k,v in sh['cells'].items()}); print('fusions :',sh['merges'])
if mode=='apply':
    x('spreadsheet.dashboard','write',[23],{'spreadsheet_data':data}); print('tableau de bord 23 mis à jour (v2, bloc en H40)')
