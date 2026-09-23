# -*- coding: utf-8 -*-
"""Supprime les jours de test de MAQUIGNON Théo (juin 2026) : x_heures_jour, pointages, congés natifs miroirs."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
E=x('hr.employee','search',[['name','=','MAQUIGNON Théo']])[0]
ids=x('x_heures_jour','search',[['x_employee_id','=',E],['x_date','>=','2026-06-01'],['x_date','<=','2026-06-30']])
att=x('hr.attendance','search',[['employee_id','=',E],['check_in','>=','2026-06-01 00:00:00'],['check_in','<','2026-07-01 00:00:00']])
lv=x('hr.leave','search',[['employee_id','=',E],['request_date_from','>=','2026-06-01'],['request_date_from','<=','2026-06-30']])
print('à supprimer : jours',ids,'| pointages',att,'| congés natifs',lv)
if ids: x('x_heures_jour','unlink',ids)
if att: x('hr.attendance','unlink',att)
for l in lv:
    try: x('hr.leave','action_refuse',[l])
    except Exception: pass
    try: x('hr.leave','unlink',[l])
    except Exception as e: print('  congé',l,'non supprimé :',str(e)[-120:])
print('reste : jours',x('x_heures_jour','search_count',[['x_employee_id','=',E],['x_date','>=','2026-06-01'],['x_date','<=','2026-06-30']]),'| congés',x('hr.leave','search_count',[['employee_id','=',E],['request_date_from','>=','2026-06-01'],['request_date_from','<=','2026-06-30']]))
