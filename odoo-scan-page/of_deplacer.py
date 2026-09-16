# -*- coding: utf-8 -*-
"""Replace les opérations d'un OF sur un jour donné (heure 07:00, France), sans contrainte de charge.
Usage : python of_deplacer.py WH/OF/12658 2026-09-16 [nom de machine]
        python of_deplacer.py WH/OF/12658 2026-09-16 "Gracia 2" """
import os, ssl, sys, xmlrpc.client, datetime
sys.stdout.reconfigure(encoding='utf-8')
if len(sys.argv) < 3: sys.exit(__doc__)
of_name, jour = sys.argv[1], sys.argv[2]; machine = sys.argv[3] if len(sys.argv) > 3 else None
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
d = datetime.date.fromisoformat(jour)
# 07:00 heure française = 05:00 UTC (été) / 06:00 UTC (hiver)
utc_h = 5 if datetime.date(d.year, 3, 31) <= d <= datetime.date(d.year, 10, 25) else 6
start = datetime.datetime(d.year, d.month, d.day, utc_h, 0, 0)
vals = {'date_start': start.strftime('%Y-%m-%d %H:%M:%S'), 'date_finished': (start + datetime.timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')}
if machine:
    wc = x('mrp.workcenter','search',[['name','=ilike',machine]], limit=1)
    if not wc: sys.exit('machine introuvable : %s' % machine)
    vals['workcenter_id'] = wc[0]
of = x('mrp.production','search_read',[['name','=',of_name]],fields=['name','state','workorder_ids'])
if not of: sys.exit('OF introuvable : %s' % of_name)
wos = x('mrp.workorder','search_read',[['id','in',of[0]['workorder_ids']],['state','not in',['done','cancel']]],fields=['name','workcenter_id','date_start'])
for w in wos:
    x('mrp.workorder','write',[w['id']],vals)
    print('OT %s (%s) : %s -> %s %s' % (w['name'], w['workcenter_id'] and w['workcenter_id'][1], w['date_start'], jour, ('sur ' + machine) if machine else ''))
print('contrôle :', [(w['name'], w['date_start'], w['workcenter_id'][1]) for w in x('mrp.workorder','read',[w['id'] for w in wos],fields=['name','date_start','workcenter_id'])])
