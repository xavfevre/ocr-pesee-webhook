# -*- coding: utf-8 -*-
"""Palettes par opérateur :
 1) champ stock.package.x_operateur_ids (many2many hr.employee) : opérateurs ayant posé sur la palette
 2) champ hr.employee.x_palette_scan_id (many2one stock.package) : palette active de l'opérateur au poste de scan
 3) reprise : palettes ouvertes avec contenu -> opérateurs des OF qu'elles contiennent
 4) action 1971 (tablette : mettre l'OF au colis) : marque l'opérateur (context op_id)
 5) action serveur « Poste de scan : opérateur » (select / sync) utilisée par la page /scan"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
mid=lambda model: x('ir.model','search',[['model','=',model]])[0]
# 1) + 2) champs
for model, vals in [('stock.package', {'name':'x_operateur_ids','field_description':'Opérateurs (ont posé sur la palette)','ttype':'many2many','relation':'hr.employee'}),
                    ('hr.employee', {'name':'x_palette_scan_id','field_description':'Palette active (poste de scan)','ttype':'many2one','relation':'stock.package','on_delete':'set null'})]:
    f=x('ir.model.fields','search',[['model','=',model],['name','=',vals['name']]])
    if f: print(model, vals['name'], ': existe déjà', f)
    else:
        vals.update({'model_id':mid(model),'state':'manual'})
        print(model, vals['name'], ': créé', x('ir.model.fields','create',vals))
# 3) reprise
ouv=x('stock.package','search',[['x_studio_cloturee','!=',True]])
ofs=x('mrp.production','search_read',[['x_studio_colis','in',ouv]],fields=['x_studio_colis','workorder_ids'])
reps=x('x_repartition_palette','search_read',[['x_studio_colis_id','in',ouv],['x_studio_of_id','!=',False]],fields=['x_studio_colis_id','x_studio_of_id'])
byp={}
for o in ofs: byp.setdefault(o['x_studio_colis'][0],set()).add(o['id'])
for r in reps: byp.setdefault(r['x_studio_colis_id'][0],set()).add(r['x_studio_of_id'][0])
for pid, ofids in byp.items():
    wos=x('mrp.workorder','search_read',[['production_id','in',list(ofids)]],fields=['employee_assigned_ids'])
    emps=sorted(set(e for w in wos for e in w['employee_assigned_ids']))
    if emps:
        x('stock.package','write',[pid],{'x_operateur_ids':[[6,0,emps]]})
        print('reprise palette',pid,'->',[e['name'] for e in x('hr.employee','read',emps,fields=['name'])])
# 4) action 1971
a=x('ir.actions.server','read',[1971],fields=['code'])[0]['code']
old="    record.write({'x_studio_colis': colis.id})"
new="""    record.write({'x_studio_colis': colis.id})
    op_id = int(env.context.get('op_id') or 0)
    if op_id and op_id not in colis.x_operateur_ids.ids:
        colis.sudo().write({'x_operateur_ids': [(4, op_id)]})"""
if old in a and 'op_id' not in a:
    x('ir.actions.server','write',[1971],{'code':a.replace(old,new)}); print('action 1971 : marquage opérateur ajouté')
else: print('action 1971 : inchangée (déjà patchée ?)', 'op_id' in a)
# 5) action poste de scan
code = """op_id = int(env.context.get('op_id') or 0)
mode = env.context.get('mode') or 'select'
emp = env['hr.employee'].sudo().browse(op_id) if op_id else None
for record in records:
    rec = record.sudo()
    if not emp or not emp.exists():
        rec.write({'x_studio_colis_actifs': False, 'x_studio_rsultat': "\U0001F464 Choisissez votre nom d'abord"})
        continue
    if mode == 'select':
        pal = emp.x_palette_scan_id
        if pal and pal.x_studio_cloturee:
            pal = None
        if pal:
            rec.write({'x_studio_colis_actifs': pal.id, 'x_studio_rsultat': "\U0001F464 " + emp.name + " \u2014 palette " + pal.name + " reprise"})
        else:
            rec.write({'x_studio_colis_actifs': False, 'x_studio_rsultat': "\U0001F464 " + emp.name + " \u2014 aucune palette active : scannez une palette"})
    else:
        pal = rec.x_studio_colis_actifs
        emp.write({'x_palette_scan_id': pal.id if pal else False})
        if pal and emp.id not in pal.x_operateur_ids.ids:
            pal.sudo().write({'x_operateur_ids': [(4, emp.id)]})
"""
code = code.encode('utf-8').decode('unicode_escape').encode('latin-1').decode('utf-8') if False else code.replace('\U0001F464','👤').replace('\u2014','—')
nm='Poste de scan : opérateur'
sa=x('ir.actions.server','search',[['name','=',nm]])
if sa: x('ir.actions.server','write',sa,{'code':code}); print('action',sa,'mise à jour')
else:
    sa=[x('ir.actions.server','create',{'name':nm,'model_id':mid('x_poste_de_scan'),'state':'code','code':code})]; print('action créée',sa)
print('ACTION_OP_ID', sa[0])
