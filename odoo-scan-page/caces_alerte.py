# -*- coding: utf-8 -*-
"""1) action serveur + cron hebdo : e-mail au bureau des CACES / habilitations expirées ou expirant sous 3 mois
   (destinataire : paramètre maquignon.caces_alerte_email, initialisé avec celui du parc auto)
   2) exemples de CACES sur Jérémy POUGER (498), à corriger / supprimer."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
parc=x('ir.config_parameter','get_param','maquignon.parc_alerte_email') or ''
cur=x('ir.config_parameter','get_param','maquignon.caces_alerte_email') or ''
if not cur and parc: x('ir.config_parameter','set_param','maquignon.caces_alerte_email',parc); cur=parc
print('destinataire alerte CACES :',cur or '(aucun !)')
CODE = r'''# Alerte e-mail hebdomadaire : certifications (CACES, habilitations...) expirées ou expirant sous 90 jours
today = datetime.date.today()
lignes = env['hr.employee.skill'].sudo().search([('is_certification', '=', True), ('employee_id.active', '=', True)])
expirees, proches, sans_date = [], [], []
for l in lignes:
    if not l.valid_to:
        sans_date.append(l)
    elif l.valid_to < today:
        expirees.append(l)
    elif (l.valid_to - today).days <= 90:
        proches.append(l)
if env.context.get('test'):
    action = {'test': True, 'expirees': [(l.employee_id.name, l.skill_id.name, str(l.valid_to)) for l in expirees],
              'proches': [(l.employee_id.name, l.skill_id.name, str(l.valid_to)) for l in proches], 'sans_date': len(sans_date)}
elif not expirees and not proches:
    action = {'envoye': False, 'raison': 'rien a signaler'}
else:
    dest = env['ir.config_parameter'].sudo().get_param('maquignon.caces_alerte_email') or ''
    if not dest:
        action = {'envoye': False, 'raison': 'aucun destinataire configure (maquignon.caces_alerte_email)'}
    else:
        def ligne(l, couleur):
            return ('<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;color:%s;font-weight:700;">%s</td></tr>'
                    % (l.employee_id.name, l.skill_id.name, couleur, l.valid_to.strftime('%d/%m/%Y')))
        entete = ('<tr><th style="text-align:left;padding:6px 10px;">Salarié</th><th style="text-align:left;padding:6px 10px;">Certification</th>'
                  '<th style="text-align:left;padding:6px 10px;">Fin de validité</th></tr>')
        corps = '<div style="font-family:Arial,sans-serif;font-size:13px;color:#0f172a;"><h3>🎓 CACES &amp; habilitations à surveiller</h3>'
        if expirees:
            corps += '<p><b style="color:#991b1b;">%d certification(s) expirée(s) :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(expirees) + entete
            for l in sorted(expirees, key=lambda r: r.valid_to):
                corps += ligne(l, '#991b1b')
            corps += '</table>'
        if proches:
            corps += '<p><b style="color:#92400e;">%d certification(s) expirant sous 3 mois :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(proches) + entete
            for l in sorted(proches, key=lambda r: r.valid_to):
                corps += ligne(l, '#92400e')
            corps += '</table>'
        if sans_date:
            corps += '<p style="color:#64748b;">%d certification(s) sans date de fin de validité renseignée.</p>' % len(sans_date)
        corps += ('<p style="margin-top:16px;"><a href="https://maquignon.odoo.com/odoo/action-hr_skills.hr_employee_skill_report_action" '
                  'style="background:#0f172a;color:#fff;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:700;">Ouvrir l\'analyse des compétences</a></p></div>')
        env['mail.mail'].sudo().create({
            'subject': '🎓 CACES / habilitations : %d expirée(s), %d sous 3 mois' % (len(expirees), len(proches)),
            'email_to': dest, 'body_html': corps}).send()
        action = {'envoye': True, 'expirees': len(expirees), 'proches': len(proches), 'dest': dest}
'''
NOM='RH : alerte email hebdomadaire CACES / habilitations'
mid=x('ir.model','search',[['model','=','hr.employee.skill']])[0]
a=x('ir.actions.server','search',[['name','=',NOM]])
if a: x('ir.actions.server','write',a,{'code':CODE}); print('action mise à jour',a)
else: a=[x('ir.actions.server','create',{'name':NOM,'model_id':mid,'state':'code','code':CODE})]; print('action créée',a)
cr=x('ir.cron','search',[['name','=',NOM]])
if not cr:
    cr=[x('ir.cron','create',{'name':NOM,'ir_actions_server_id':a[0],'interval_number':1,'interval_type':'weeks','nextcall':'2026-09-14 05:00:00','user_id':2,'active':True})]; print('cron créé',cr,'(lundi 07:00 Paris)')
else: print('cron existant',cr)
# 2) exemples sur Jérémy POUGER
emp=498; t=x('hr.skill.type','search',[['name','=','CACES & habilitations']])[0]
lvl=x('hr.skill.level','search',[['skill_type_id','=',t]])[0]
def sk(nm): return x('hr.skill','search',[['skill_type_id','=',t],['name','ilike',nm]])[0]
EX=[('R482 cat. B1','2019-03-12','2029-03-11'),('R489 cat. 3','2021-10-05','2026-10-04'),('Habilitation électrique','2023-01-10','2026-01-09')]
for nm,d1,d2 in EX:
    s=sk(nm)
    if not x('hr.employee.skill','search',[['employee_id','=',emp],['skill_id','=',s]]):
        x('hr.employee.skill','create',{'employee_id':emp,'skill_type_id':t,'skill_id':s,'skill_level_id':lvl,'valid_from':d1,'valid_to':d2})
print('certifications de Jérémy :',[(r['skill_id'][1],r['valid_from'],r['valid_to']) for r in x('hr.employee.skill','search_read',[['employee_id','=',emp]],fields=['skill_id','valid_from','valid_to'])])
# 3) test à blanc (aucun e-mail envoyé)
print('test à blanc :',x('ir.actions.server','run',a,context={'test':1,'active_model':'hr.employee.skill'}))
