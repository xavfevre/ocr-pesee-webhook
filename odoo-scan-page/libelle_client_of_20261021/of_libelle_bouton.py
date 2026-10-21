# -*- coding: utf-8 -*-
"""Demande Xavier 21/10/2026 : (1) sur l'OF imprimé (rapport « Ordre de Fabrication », vue QWeb 6635), la colonne Produit
affiche le libellé client seul quand la ligne de vente en a un (sinon le nom de l'article comme avant) ;
(2) bouton « Imprimer l'OF » dans l'en-tête du formulaire d'OF (rapport 1483, le même que Imprimer > Ordre de Fabrication).
Sauvegarde de l'arch du rapport avant modification. Usage : python of_libelle_bouton.py [apply]"""
import os, sys, io, re, xmlrpc.client, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4]}}
ICI = os.path.dirname(os.path.abspath(__file__))

# ---------- 1. rapport : colonne Produit
VUE_RAPPORT = 6635
arch = call('ir.ui.view', 'read', [VUE_RAPPORT], fields=['arch_db'], **CTX)[0]['arch_db']
sauv = os.path.join(ICI, 'rapport_of_6635_avant_%s.xml' % dt.datetime.now().strftime('%Y%m%d_%H%M'))
io.open(sauv, 'w', encoding='utf-8').write(arch)
print('arch du rapport sauvegardée :', sauv)
OLD = """                <td>
                    <span t-field="item.product_id.name"/>
                    <t t-if="item.product_description_variants">
                        <br/><small class="text-muted"><span t-field="item.product_description_variants"/></small>
                    </t>
                    <t t-if="item.x_studio_description_article">
                        <br/><small class="text-muted"><span t-field="item.x_studio_description_article"/></small>
                    </t>
                </td>"""
NEW = """                <td>
                    <t t-set="libcli" t-value="(item.sale_line_id.x_studio_libell_client or '').strip() if item.sale_line_id else ''"/>
                    <t t-if="libcli">
                        <span t-out="libcli" style="font-weight:bold;"/>
                    </t>
                    <t t-else="">
                        <span t-field="item.product_id.name"/>
                        <t t-if="item.product_description_variants">
                            <br/><small class="text-muted"><span t-field="item.product_description_variants"/></small>
                        </t>
                        <t t-if="item.x_studio_description_article">
                            <br/><small class="text-muted"><span t-field="item.x_studio_description_article"/></small>
                        </t>
                    </t>
                </td>"""
if 't-set="libcli"' in arch:
    print('rapport : déjà modifié'); arch_new = None
else:
    assert arch.count(OLD) == 1, 'cellule Produit introuvable (%d occurrence(s))' % arch.count(OLD)
    arch_new = arch.replace(OLD, NEW)
    print('rapport : cellule Produit à remplacer (libellé client seul si présent)')

# ---------- 2. bouton dans l'en-tête du formulaire
RAPPORT = 1483
NOM_VUE = "mrp.production.form.bouton.imprimer (Maquignon)"
existante = call('ir.ui.view', 'search', [['model', '=', 'mrp.production'], ['name', '=', NOM_VUE]], **CTX)
ARCH_BOUTON = """<data>
  <xpath expr="//header" position="inside">
    <button name="%d" type="action" string="🖨️ Imprimer l'OF" class="btn-secondary" help="Imprime l'ordre de fabrication (même document que Imprimer > Ordre de Fabrication)"/>
  </xpath>
</data>""" % RAPPORT
print('bouton :', 'vue déjà présente %s' % existante if existante else 'vue héritée à créer sur le formulaire 5187 (rapport %d « %s »)' % (RAPPORT, call('ir.actions.report', 'read', [RAPPORT], fields=['name'], **CTX)[0]['name']))
if not APPLY:
    print('\nsimulation : rien écrit'); sys.exit()
if arch_new:
    call('ir.ui.view', 'write', [VUE_RAPPORT], {'arch_db': arch_new}, **CTX)
    print('rapport 6635 mis à jour')
if not existante:
    vid = call('ir.ui.view', 'create', [{'name': NOM_VUE, 'model': 'mrp.production', 'type': 'form', 'inherit_id': 5187, 'mode': 'extension', 'priority': 200, 'arch': ARCH_BOUTON}], **CTX)
    print('vue bouton créée :', vid)
r = m.execute_kw(DB, uid, P, 'mrp.production', 'get_views', [[[False, 'form']]], {'context': {'allowed_company_ids': [1, 3, 4]}})
a = r['views']['form']['arch']; i = a.find('Imprimer l\'OF')
print('bouton présent dans le formulaire combiné :', i > 0, '|', re.sub(r'\s+', ' ', a[max(0, i - 160):i + 40]))
