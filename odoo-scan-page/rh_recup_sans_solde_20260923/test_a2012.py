# -*- coding: utf-8 -*-
"""Test de la nouvelle logique 2012/2014 (heures_actions.py local) contre la production, sur MAQUIGNON Théo,
sur des jours de juin 2026 sans saisie ; tout est supprimé à la fin."""
import os, ssl, sys, xmlrpc.client, datetime, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
def call(mo,me,*a,**k): return m.execute_kw(D,uid,p,mo,me,list(a),k)
spec=importlib.util.spec_from_file_location('ha','ocr/heures_actions.py'); ha=importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
emp=call('hr.employee','search_read',[['name','=','MAQUIGNON Théo']],fields=['name','x_heures_token','resource_calendar_id'])[0]
E=emp['id']; TOK=emp['x_heures_token']; ADM=call('ir.config_parameter','get_param','maquignon.rh_admin_key')
cal,atts=ha._cal_info(call,emp['resource_calendar_id'][0])
libres=[]
d=datetime.date(2026,6,1)
while len(libres)<6 and d<datetime.date(2026,7,1):
    theo=sum(r[1]-r[0] for r in ha._rngs_jour(cal,atts,d))
    if theo>0 and not call('x_heures_jour','search_count',[['x_employee_id','=',E],['x_date','=',d.isoformat()]]): libres.append((d,theo))
    d+=datetime.timedelta(days=1)
print('Théo',E,'| jours libres :',[(d.isoformat(),t) for d,t in libres])
crees=set()
def essai(lab,ctx):
    ctx=dict(ctx,active_model='x_heures_jour',hj_emp=E)
    try:
        r=ha._a2012(call,ctx); crees.add(ctx['hj_date'])
        row=call('x_heures_jour','search_read',[['x_employee_id','=',E],['x_date','=',ctx['hj_date']]],fields=['x_type','x_heures','x_theo','x_hs','x_h_recup','x_h_sans_solde','x_hs_payees','x_note','x_m_deb','x_am_fin'])[0]
        print('OK  %-42s -> %s | base: type %s H %.2f T %.2f hs %+.2f R %.2f S %.2f payées %s note %r' % (lab,{k:r[k] for k in ('type','heures','theo','hs','h_recup','h_ss')},row['x_type'],row['x_heures'],row['x_theo'],row['x_hs'],row['x_h_recup'],row['x_h_sans_solde'],row['x_hs_payees'],row['x_note']))
        return r
    except ha.HeuresErreur as e:
        print('REF %-42s -> %s' % (lab,str(e)[:150])); crees.add(ctx['hj_date'])
(d0,t0),(d1,t1),(d2,t2),(d3,t3),(d4,t4),(d5,t5)=libres
rngs=ha._rngs_jour(cal,atts,d0); print('plages jour 0 :',rngs)
m_=rngs[0]; a_=rngs[1] if len(rngs)>1 else [0,0]
sal=dict(hj_token=TOK)
essai('salarié : journée normale',dict(sal,hj_date=d0.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=a_[0],hj_am_fin=a_[1]))
essai('salarié : +1,5 h (heures sup -> récup auto)',dict(sal,hj_date=d0.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=a_[0],hj_am_fin=a_[1]+1.5))
essai('salarié : 4 h + 4,5 h récup (trop si T<8,5)',dict(sal,hj_date=d1.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[0]+4,hj_am_deb=0,hj_am_fin=0,hj_h_recup=4.5,hj_h_ss=0))
essai('salarié : matin travaillé, reste en récup',dict(sal,hj_date=d1.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=0,hj_am_fin=0,hj_h_recup=round(t1-(m_[1]-m_[0]),2),hj_h_ss=0))
essai('salarié : récup + sans solde > manque',dict(sal,hj_date=d1.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=0,hj_am_fin=0,hj_h_recup=3,hj_h_ss=3))
essai('salarié : journée entière en récup',dict(sal,hj_date=d2.isoformat(),hj_type='recup'))
essai('salarié : journée entière sans solde',dict(sal,hj_date=d3.isoformat(),hj_type='sans_solde'))
essai('salarié : CP (interdit)',dict(sal,hj_date=d4.isoformat(),hj_type='cp'))
essai('salarié : 0 h + sans solde = T (normalisé)',dict(sal,hj_date=d4.isoformat(),hj_type='travail',hj_m_deb=0,hj_m_fin=0,hj_am_deb=0,hj_am_fin=0,hj_h_recup=0,hj_h_ss=t4))
essai('salarié : retouche d\'un jour récup -> travail',dict(sal,hj_date=d2.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=a_[0],hj_am_fin=a_[1]))
adm=dict(hj_k=ADM)
essai('bureau : sans solde partiel matin',dict(adm,hj_date=d5.isoformat(),hj_type='sans_solde',hj_periode='matin'))
essai('bureau : récup partiel après-midi',dict(adm,hj_date=d5.isoformat(),hj_type='recup',hj_periode='apresmidi'))
essai('bureau : HS payées (+2 h non mises en récup)',dict(adm,hj_date=d5.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=a_[0],hj_am_fin=a_[1]+2,hj_hs_payees=1))
essai('salarié : resauve le même jour (payées conservé)',dict(sal,hj_date=d5.isoformat(),hj_type='travail',hj_m_deb=m_[0],hj_m_fin=m_[1],hj_am_deb=a_[0],hj_am_fin=a_[1]+2))
essai('bureau : CP partiel matin (inchangé)',dict(adm,hj_date=d4.isoformat(),hj_type='cp',hj_periode='matin'))
# nettoyage
ids=call('x_heures_jour','search',[['x_employee_id','=',E],['x_date','in',sorted(crees)]])
att=call('hr.attendance','search',[['employee_id','=',E],['check_in','>=','2026-06-01 00:00:00'],['check_in','<','2026-07-01 00:00:00']])
print('nettoyage : jours',ids,'| pointages',att)
if ids: call('x_heures_jour','unlink',ids)
if att: call('hr.attendance','unlink',att)
print('reste :',call('x_heures_jour','search_count',[['x_employee_id','=',E],['x_date','>=','2026-06-01'],['x_date','<','2026-07-01']]),'| congés natifs juin Théo :',call('hr.leave','search_read',[['employee_id','=',E],['request_date_from','>=','2026-06-01'],['request_date_from','<','2026-07-01']],fields=['name','state']))
