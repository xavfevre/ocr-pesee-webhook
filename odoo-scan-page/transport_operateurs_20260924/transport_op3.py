import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
U,D='https://maquignon.odoo.com','maquignon'
us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context()
uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),dict(k,context={'allowed_company_ids':[1,2,3,4,13]}))
a=x('base.automation','read',[18],fields=['name','trigger','trigger_field_ids','filter_domain','active','action_server_ids'])[0]
print('automatisation 18 :',a['name'],'|',a['trigger'],'| champs',a['trigger_field_ids'],'| domaine',a['filter_domain'],'| actif',a['active'])
print('automatisation 66 (TP) :',x('ir.actions.server','read',x('base.automation','read',[66],fields=['action_server_ids'])[0]['action_server_ids'],fields=['code'])[0]['code'])
tags={t['id']:t['name'] for t in x('project.tags','search_read',[],fields=['name'])}
print('étiquettes :',tags)
F=['name','project_id','stage_id','state','tag_ids','x_studio_chauffeur','x_studio_operateurs','x_studio_machines_tp','x_studio_transport','planned_date_begin','create_date']
tasks=x('project.task','search_read',[['project_id','=',2]],fields=F,order='id desc')
print('tâches projet Demande de transport :',len(tasks))
tp=[t for t in tasks if any('TP' in tags.get(g,'') for g in t['tag_ids'])]
print('  taguées TP :',len(tp),'| avec machines TP :',len([t for t in tasks if t['x_studio_machines_tp']]),'| TP avec chauffeur :',len([t for t in tp if t['x_studio_chauffeur']]))
tr=[t for t in tasks if t not in tp]
avec=[t for t in tr if t['x_studio_chauffeur']]
diff=[t for t in avec if sorted(t['x_studio_operateurs'])!=[t['x_studio_chauffeur'][0]]]
print('  transport (non TP) :',len(tr),'| avec chauffeur :',len(avec),'| opérateurs ≠ [chauffeur] :',len(diff),'| dont ouvertes :',len([t for t in diff if t['state'] not in ('1_done','1_canceled')]))
print('  transport sans chauffeur mais avec opérateurs :',len([t for t in tr if not t['x_studio_chauffeur'] and t['x_studio_operateurs']]))
emp={e['id']:e['name'] for e in x('hr.employee','search_read',[['active','in',[True,False]]],fields=['name'])}
for t in [t for t in diff if t['state'] not in ('1_done','1_canceled')][:12]:
    print('    ',t['id'],t['name'][:40],'|',t['state'],'| chauffeur',emp.get(t['x_studio_chauffeur'][0]),'| opérateurs',[emp.get(o,o) for o in t['x_studio_operateurs']],'| créé',t['create_date'][:10])
print('  états :',collections.Counter(t['state'] for t in tr).most_common())
