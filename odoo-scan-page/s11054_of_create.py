# -*- coding: utf-8 -*-
"""S11054 : un OF par ligne produit (comme la confirmation standard), modèle = OF 12030.
 un   : remet 12030 à la quantité de sa ligne + crée l'OF de la 1re ligne sans OF (test)
 tout : crée les OF de toutes les lignes sans OF (reprise possible)"""
import os, ssl, sys, time, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
c=ssl.create_default_context(); uid=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/common',context=c).authenticate(D,us,p,{})
m=xmlrpc.client.ServerProxy(U+'/xmlrpc/2/object',context=c)
x=lambda mo,me,*a,**k: m.execute_kw(D,uid,p,mo,me,list(a),k)
SO=42139; mode=sys.argv[1]
ref=x('mrp.production','read',[12030],fields=['product_id','product_uom_id','bom_id','picking_type_id','location_src_id','location_dest_id','company_id','date_start','date_deadline','sale_line_id','product_qty','origin'])[0]
if mode=='un':
    q=x('sale.order.line','read',[ref['sale_line_id'][0]],fields=['product_uom_qty'])[0]['product_uom_qty']
    if abs(ref['product_qty']-q)>1e-6:
        x('mrp.production','write',[12030],{'product_qty':q}); print('OF 12030 remis à',q,'m³ (était %.3f)'%ref['product_qty'])
deja=set(o['sale_line_id'][0] for o in x('mrp.production','search_read',[['sale_line_id.order_id','=',SO],['state','!=','cancel']],fields=['sale_line_id'],limit=5000) if o['sale_line_id'])
ls=[l for l in x('sale.order.line','search_read',[['order_id','=',SO],['display_type','=',False],['product_id','=',744],['product_uom_qty','>',0]],fields=['id','product_uom_qty','name','sequence'],order='sequence,id',limit=5000) if l['id'] not in deja]
print('lignes Tuffeau sans OF :',len(ls))
if mode=='un': ls=ls[:1]
t0=time.time(); n=0; err=0
for i,l in enumerate(ls):
    vals={'product_id':ref['product_id'][0],'product_uom_id':ref['product_uom_id'][0],'product_qty':l['product_uom_qty'],'bom_id':ref['bom_id'][0],
          'origin':'S11054','sale_line_id':l['id'],'picking_type_id':ref['picking_type_id'][0],'location_src_id':ref['location_src_id'][0],
          'location_dest_id':ref['location_dest_id'][0],'company_id':ref['company_id'][0],'date_start':ref['date_start']}
    if ref.get('date_deadline'): vals['date_deadline']=ref['date_deadline']
    try:
        oid=x('mrp.production','create',vals); n+=1
        if mode=='un':
            o=x('mrp.production','read',[oid],fields=['name','state','product_qty','workorder_ids','x_studio_nbr','x_studio_long_m_1','x_studio_larg_m_1','x_studio_haut_m_1','x_studio_ref_pierre','x_studio_palette','x_studio_nom_du_client','x_studio_tche_commande_pierre','x_studio_poste_de_travail','log_note'])[0]
            print('OF créé :',o); print('  OT :',x('mrp.workorder','read',o['workorder_ids'],fields=['name','workcenter_id','state']))
    except Exception as e:
        err+=1; print('ERREUR ligne',l['id'],':',str(e).strip().split('\n')[-1][:300])
        if err>=5: print('trop d erreurs, arrêt'); break
    if (i+1)%25==0: print('  %d/%d OF créés (%.0f s)'%(i+1,len(ls),time.time()-t0),flush=True)
print('créés :',n,'| erreurs :',err,'| durée %.0f s'%(time.time()-t0))
ofs=x('mrp.production','search_read',[['sale_line_id.order_id','=',SO],['state','!=','cancel']],fields=['product_qty','x_studio_nbr','workorder_ids'],limit=5000)
print('contrôle : OF S11054 :',len(ofs),'| volume total %.3f m³'%sum(o['product_qty'] for o in ofs),'| pièces',sum(o['x_studio_nbr'] or 0 for o in ofs),'| sans OT',sum(1 for o in ofs if not o['workorder_ids']))
