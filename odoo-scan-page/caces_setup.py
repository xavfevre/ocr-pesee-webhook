# -*- coding: utf-8 -*-
"""Type de compétence « CACES & habilitations » (certification, avec dates de validité) + liste des CACES / habilitations courants."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
NOM='CACES & habilitations'
t=x('hr.skill.type','search',[['name','=',NOM]],context={'active_test':False})
if not t:
    t=[x('hr.skill.type','create',{'name':NOM,'is_certification':True,'color':1})]; print('type créé',t)
else: print('type existant',t)
SKILLS=["CACES R482 cat. A — engins compacts","CACES R482 cat. B1 — pelles hydrauliques","CACES R482 cat. C1 — chargeuses / chargeuses-pelleteuses","CACES R482 cat. C2 — bouteurs / niveleuses","CACES R482 cat. E — tombereaux","CACES R482 cat. F — chariots de chantier","CACES R482 cat. G — conduite hors production",
        "CACES R489 cat. 1A/1B — transpalettes / gerbeurs","CACES R489 cat. 3 — chariots frontaux ≤ 6 t","CACES R489 cat. 4 — chariots frontaux > 6 t","CACES R489 cat. 5 — chariots à mât rétractable",
        "CACES R486 cat. A/B — nacelles (PEMP)","CACES R490 — grue auxiliaire de chargement","CACES R484 — pont roulant","CACES R487 — grue à tour",
        "Habilitation électrique (B0/H0V, BS…)","AIPR — travaux à proximité des réseaux","SST — sauveteur secouriste du travail","Permis C / CE (FIMO-FCO)","Autorisation de conduite interne","Élingage / levage"]
exist={s['name'] for s in x('hr.skill','search_read',[['skill_type_id','=',t[0]]],fields=['name'])}
n=0
for i,nm in enumerate(SKILLS):
    if nm not in exist: x('hr.skill','create',{'name':nm,'skill_type_id':t[0],'sequence':i}); n+=1
print('compétences ajoutées :',n,'| total',x('hr.skill','search_count',[['skill_type_id','=',t[0]]]))
lv=x('hr.skill.level','search_read',[['skill_type_id','=',t[0]]],fields=['name','level_progress','default_level'])
if not lv:
    x('hr.skill.level','create',{'name':'Valide','skill_type_id':t[0],'level_progress':100,'default_level':True}); print('niveau « Valide » créé')
print('type final :',x('hr.skill.type','read',t,fields=['name','is_certification','skill_ids','skill_level_ids'])[0])
