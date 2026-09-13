# -*- coding: utf-8 -*-
"""Vérification de l'instance Odoo après (ou avant) montée de version.
Contrôle les personnalisations PROTEC : vues, champs, automatisations,
rapports PDF, dashboards, champs utilisés par l'app Flask.
Usage : python3 check_post_upgrade.py"""
import xmlrpc.client, json, urllib.request, http.cookiejar, urllib.parse, sys

url, db = "https://protec-s3t.odoo.com", "protec-s3t"
u, pw = "s3t@orange.fr", "Violette2025"
uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").authenticate(db, u, pw, {})
m = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
def EK(md, me, a, k={}, **kw): return m.execute_kw(db, uid, pw, md, me, a, {**k, **kw})

OK, KO = [], []
def check(label, cond, detail=""):
    (OK if cond else KO).append(f"{label}{(' — ' + detail) if detail and not cond else ''}")
    print(("  ✓ " if cond else "  ✗ ") + label + ("" if cond else f"  [{detail}]"))

print("Version:", xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common").version()["server_serie"])

# ── 1. Vues custom actives et contenu clé ──
print("\n— Vues —")
probes = {
    2589: ("sale.order form Studio (chantier + miroir BI)", "x_bi_technicien_id"),
    2929: ("BI : CGV agrandies", "protec_cgv"),
    2931: ("BI chiffré : annexe Nota/Photos", "x_studio_nota"),
    2638: ("BI non chiffré : annexe Nota/Photos (VUE DE BASE — risque reset)", "x_studio_nota"),
    4260: ("Devis : CGV agrandies", "font-size:1.08em"),
    4261: ("Facture : CGV page dédiée", "page-break-before"),
    4262: ("Popup bascule société", "x_company_id"),
    4162: ("Page planning semaine (+ Dupliquer)", "dmodal"),
}
for vid, (label, probe) in probes.items():
    try:
        v = EK('ir.ui.view', 'read', [[vid]], fields=['active', 'arch_db'])[0]
        check(f"vue {vid} {label}", v['active'] and probe in v['arch_db'],
              "inactive" if not v['active'] else f"marqueur '{probe}' absent")
    except Exception as e:
        check(f"vue {vid} {label}", False, str(e)[:80])

# ── 2. Automatisations actives ──
print("\n— Automatisations —")
autos = EK('base.automation', 'search_read', [[]], fields=['name', 'active'])
for a in autos:
    check(f"automatisation « {a['name'][:40]} »", a['active'], "désactivée")

# ── 3. Actions serveur custom : le code compile toujours (syntaxe) ──
print("\n— Actions serveur clés —")
for aid in (1189, 1190, 1191, 1192, 1194, 1195, 1016, 1204, 1113, 1114,
            1163, 1199, 1200, 1201, 1202, 1205, 1206, 1207):
    try:
        code = EK('ir.actions.server', 'read', [[aid]], fields=['code'])[0]['code']
        compile(code, f'<a{aid}>', 'exec')
        check(f"action {aid}", True)
    except Exception as e:
        check(f"action {aid}", False, str(e)[:80])

# ── 4. Champs manuels et Studio utilisés partout ──
print("\n— Champs critiques —")
FIELDS = {
    'planning.slot': ['name', 'start_datetime', 'end_datetime', 'partner_id', 'employee_ids',
                      'resource_ids', 'x_fdt_fait', 'x_fdt_date', 'x_fdt_vehicule',
                      'x_fdt_heure_arrivee', 'x_fdt_heure_depart', 'x_fdt_temps_trajet',
                      'x_fdt_operateurs', 'x_fdt_commentaires', 'x_fdt_data', 'x_fdt_signataire'],
    'sale.order': ['x_studio_nota', 'x_studio_lieu_dintervention_1', 'x_studio_lieu_dintervention_2',
                   'x_studio_interlocuteur_1', 'x_studio_date_previsionnelle_dintervention',
                   'x_bi_technicien_id', 'x_bi_camion_id', 'x_bi_conformite', 'x_fin_intervention'],
    'stock.picking': ['x_technicien_id', 'x_camion_id', 'x_conformite', 'x_bi_seq_code'],
    'product.pricelist.item': ['applied_on', 'product_tmpl_id', 'compute_price', 'fixed_price',
                               'date_start', 'date_end'],
    'account.move.line': ['balance', 'move_name', 'parent_state'],
    'hr.leave': ['work_entry_type_id', 'request_date_from', 'request_date_to'],
    'fleet.vehicle': ['x_surnom'],
    'fleet.vehicle.odometer': ['value', 'x_litres'],
    'x_bascule_societe': ['x_move_id', 'x_company_id'],
}
for model, flds in FIELDS.items():
    try:
        have = EK(model, 'fields_get', [flds], {'attributes': ['type']})
        missing = [f for f in flds if f not in have]
        check(f"{model}", not missing, "manquants: " + ",".join(missing))
    except Exception as e:
        check(f"{model}", False, str(e)[:80])

# ── 5. Rendus PDF (devis, facture, BI × 2) ──
print("\n— Rapports PDF —")
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
payload = json.dumps({"jsonrpc": "2.0", "params": {"db": db, "login": u, "password": pw}}).encode()
op.open(urllib.request.Request(f"{url}/web/session/authenticate", data=payload,
        headers={"Content-Type": "application/json"}), timeout=60)
ctx = urllib.parse.quote(json.dumps({"allowed_company_ids": [2]}))
C = {'allowed_company_ids': [2]}
so = EK('sale.order', 'search', [[('state', '=', 'sale')]], {'limit': 1, 'order': 'id desc', 'context': C})
inv = EK('account.move', 'search', [[('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]],
         {'limit': 1, 'order': 'id desc', 'context': C})
pick = EK('stock.picking', 'search', [[('picking_type_id.sequence_code', '=', 'ASS/BI/')]],
          {'limit': 1, 'order': 'id desc', 'context': C})
for rep, rid, label, probe in (
        ("sale.report_saleorder", so and so[0], "devis (CGV)", "CONDITIONS GENERALES"),
        ("account.report_invoice", inv and inv[0], "facture (CGV + QR)", "CONDITIONS GENERALES"),
        ("protec_custom.report_deliveryslip_priced", pick and pick[0], "BI chiffré", "Bon d'intervention"),
        ("stock.report_deliveryslip", pick and pick[0], "BI non chiffré", "")):
    if not rid:
        check(f"rendu {label}", False, "aucun enregistrement de test"); continue
    try:
        html = op.open(f"{url}/report/html/{rep}/{rid}?context={ctx}", timeout=120).read().decode()
        check(f"rendu {label}", (probe in html) if probe else len(html) > 5000, f"'{probe}' absent du rendu")
    except Exception as e:
        check(f"rendu {label}", False, str(e)[:80])

# ── 6. Pages planning website ──
print("\n— Pages planning —")
for pg in ("/planning-semaine", "/planning-mois", "/planning-jour", "/planning-mobile", "/planning"):
    try:
        html = op.open(f"{url}{pg}", timeout=90).read().decode()
        check(f"page {pg}", len(html) > 3000 and 'Traceback' not in html[:3000])
    except Exception as e:
        check(f"page {pg}", False, str(e)[:80])

# ── 7. Dashboards : les listes pointent vers des champs existants ──
print("\n— Dashboards persos —")
for did in (14, 15, 16, 17, 18, 20, 35, 36):
    try:
        d = json.loads(EK('spreadsheet.dashboard', 'read', [[did]], fields=['spreadsheet_data'])[0]['spreadsheet_data'])
        bad = []
        for lid, l in d.get('lists', {}).items():
            cols = [c for c in l['columns'] if c != 'id']
            have = EK(l['model'], 'fields_get', [cols], {'attributes': ['type']})
            bad += [f"{l['model']}.{c}" for c in cols if c not in have]
        check(f"dashboard {did}", not bad, "champs disparus: " + ",".join(bad[:4]))
    except Exception as e:
        check(f"dashboard {did}", False, str(e)[:80])

print(f"\n════ RÉSULTAT : {len(OK)} OK / {len(KO)} PROBLÈME(S) ════")
for k in KO:
    print("  ✗", k)
sys.exit(1 if KO else 0)
