# -*- coding: utf-8 -*-
"""Ménage des anciennes actions du poste de scan (remplacées par le relais Render 2102 le 16/09/2026).
Code archivé dans odoo-scan-page/actions_scan_archive_20260916/. Usage : python nettoyage_actions_scan.py dry|apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode=(sys.argv[1] if len(sys.argv)>1 else 'dry').lower()
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
autos=x('base.automation','search_read',[['id','=',29]],fields=['name','active'])
reloc=x('ir.actions.server','search',[['name','=','Relocaliser palette (emplacement)']])
ids=[1585,1587,1588,1913,1914,1915,1971,2091]+reloc
acts=x('ir.actions.server','search_read',[['id','in',ids]],fields=['name','model_id'])
print('automatisation à supprimer :',autos); print('actions à supprimer :',[(a['id'],a['name']) for a in acts])
lignes=sum(len((x('ir.actions.server','read',[a['id']],fields=['code'])[0]['code'] or '').splitlines()) for a in acts)
print('lignes de code libérées :',lignes)
if mode=='apply':
    if autos: x('base.automation','unlink',[29]); print('automatisation 29 supprimée')
    x('ir.actions.server','unlink',[a['id'] for a in acts]); print('actions supprimées')
    print('restant :',x('ir.actions.server','search_count',[['id','in',ids]]))
