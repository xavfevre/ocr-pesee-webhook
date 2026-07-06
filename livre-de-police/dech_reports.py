# -*- coding: utf-8 -*-
import json, urllib.request, ssl, http.cookiejar
URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
ctx=ssl.create_default_context(); cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
def call(p,pl):
    r=urllib.request.Request(URL+p,data=json.dumps(pl).encode(),headers={"Content-Type":"application/json"})
    return json.loads(op.open(r,timeout=180).read())
def kw(m,meth,args,kwargs=None):
    r=call("/web/dataset/call_kw",{"jsonrpc":"2.0","method":"call","params":{"model":m,"method":meth,"args":args,"kwargs":kwargs or {}}})
    if r.get("error"): raise Exception(str(r["error"].get("data",{}).get("message",r["error"]))[:400])
    return r["result"]
call("/web/session/authenticate",{"jsonrpc":"2.0","params":{"db":DB,"login":U,"password":P}})

# ── 1) Action serveur : Générer les DAP manquantes ──
mid_lp = kw("ir.model","search_read",[[("model","=","x_livre_police")]],{"fields":["id"]})[0]["id"]
CODE = r'''
existing = env['x_dap'].search([])
nums = [int(d.x_name) for d in existing if (d.x_name or '').isdigit()]
nxt = (max(nums) + 1) if nums else 1
created = 0; linked = 0
for rec in records.filtered(lambda r: not r.x_studio_dap_id):
    key_cli = (rec.x_studio_client or '').strip()
    key_cha = (rec.x_studio_chantier or '').strip()
    key_cod = rec.x_studio_code or False
    dap = env['x_dap'].search([('x_studio_client','=',key_cli),('x_studio_chantier','=',key_cha),('x_studio_code','=',key_cod)], limit=1)
    if not dap:
        dap = env['x_dap'].create({
            'x_name': str(nxt), 'x_studio_client': key_cli, 'x_studio_chantier': key_cha,
            'x_studio_code': key_cod,
            'x_studio_date': rec.x_studio_date.date() if rec.x_studio_date else False,
        })
        nxt += 1; created += 1
    rec.write({'x_studio_dap_id': dap.id})
    linked += 1
log('DAP : %d creees, %d pesees liees' % (created, linked), level='info')
'''
ex = kw("ir.actions.server","search_read",[[("name","=","Générer DAP manquantes")]],{"fields":["id"]})
if ex:
    aid=ex[0]["id"]; kw("ir.actions.server","write",[[aid],{"code":CODE}])
else:
    aid = kw("ir.actions.server","create",[{"name":"Générer DAP manquantes","model_id":mid_lp,
        "state":"code","code":CODE,"binding_model_id":mid_lp,"binding_view_types":"list,form"}])
print("action DAP manquantes:", aid)

# ── 2) Rapport PDF Livre de police (paysage) ──
pf = kw("report.paperformat","search_read",[[("orientation","=","Landscape")]],{"fields":["id","name"],"limit":1})
if pf:
    pf_id = pf[0]["id"]
else:
    pf_id = kw("report.paperformat","create",[{"name":"A4 paysage livre police","format":"A4","orientation":"Landscape",
        "margin_top":12,"margin_bottom":10,"margin_left":6,"margin_right":6,"header_spacing":6,"dpi":90}])
print("paperformat paysage:", pf_id)

TPL_LP = '''<t t-name="website.report_livre_police">
  <t t-call="web.html_container">
    <t t-call="web.basic_layout">
      <div class="page" style="font-family:Helvetica, Arial, sans-serif;">
        <h3 style="color:#01666B;margin-bottom:2px;">LIVRE DE POLICE — Registre des déchets entrants (remblaiement)</h3>
        <div style="font-size:11px;color:#555;margin-bottom:8px;">
          CARRIÈRE D'HAIMS — SARL MAQUIGNON FRÈRES — Site de remblaiement (déchets inertes)
          — édité le <span t-esc="context_timestamp(datetime.datetime.now()).strftime('%d/%m/%Y')"/>
        </div>
        <table class="table table-sm" style="font-size:9.5px;width:100%;border-collapse:collapse;">
          <thead>
            <tr style="background:#01666B;color:#fff;">
              <th style="padding:3px;">N°</th><th>Date</th><th>N° pesée</th><th>Code déchet</th>
              <th>Désignation</th><th>Code interne</th><th style="text-align:right;">Tonnage (t)</th>
              <th>Producteur</th><th>Chantier</th><th>Transporteur</th><th>Immat.</th>
              <th>DAP</th><th>Facture</th><th>Contrôle</th>
            </tr>
          </thead>
          <tbody>
            <t t-set="i" t-value="0"/>
            <t t-foreach="docs.sorted(key=lambda d: (d.x_studio_date or datetime.datetime(1970,1,1), d.x_name or ''))" t-as="d">
              <t t-set="i" t-value="i + 1"/>
              <tr style="border-bottom:1px solid #ddd;">
                <td style="padding:2px 3px;"><t t-esc="i"/></td>
                <td><t t-esc="d.x_studio_date and d.x_studio_date.strftime('%d/%m/%Y %H:%M') or ''"/></td>
                <td><t t-esc="d.x_name"/></td>
                <td><t t-esc="d.x_studio_code_dechet"/></td>
                <td><t t-esc="d.x_studio_designation"/></td>
                <td><t t-esc="d.x_studio_code or ''"/></td>
                <td style="text-align:right;"><t t-esc="'%.3f' % (d.x_studio_tonnage or 0)"/></td>
                <td><t t-esc="d.x_studio_client or ''"/></td>
                <td><t t-esc="d.x_studio_chantier or ''"/></td>
                <td><t t-esc="d.x_studio_transporteur or ''"/></td>
                <td><t t-esc="d.x_studio_vehicule or ''"/></td>
                <td><t t-esc="d.x_studio_dap_id and d.x_studio_dap_id.x_name or ''"/></td>
                <td><t t-esc="d.x_studio_facture or ''"/></td>
                <td><t t-esc="dict(conforme='Conforme', non_conforme='NON CONFORME').get(d.x_studio_controle or '', '')"/></td>
              </tr>
            </t>
            <tr style="font-weight:bold;background:#EAF4F4;">
              <td colspan="6" style="text-align:right;padding:3px;">TOTAL (t)</td>
              <td style="text-align:right;"><t t-esc="'%.3f' % sum(d.x_studio_tonnage or 0 for d in docs)"/></td>
              <td colspan="7"/>
            </tr>
          </tbody>
        </table>
      </div>
    </t>
  </t>
</t>'''

TPL_DAP = '''<t t-name="website.report_dap">
  <t t-call="web.html_container">
    <t t-call="web.basic_layout">
      <t t-foreach="docs" t-as="d">
        <div class="page" style="font-family:Helvetica, Arial, sans-serif;">
          <div style="background:#01666B;color:#fff;text-align:center;padding:12px;border-radius:6px;">
            <h3 style="margin:0;color:#fff;">DEMANDE D'ACCEPTATION PRÉALABLE (DAP)</h3>
            <div style="font-size:12px;">Déchets inertes — remblaiement</div>
          </div>
          <div style="margin:10px 0 4px;font-weight:bold;">DAP n° <span t-esc="d.x_name"/> — CARRIÈRE D'HAIMS — SARL MAQUIGNON FRÈRES</div>
          <div style="font-size:11px;color:#555;margin-bottom:10px;">Site de remblaiement (décharge inertes) — Haims</div>
          <table style="width:100%;border-collapse:collapse;font-size:12px;">
            <t t-set="rows" t-value="[
              ('Producteur / détenteur', d.x_studio_client or ''),
              ('Adresse du producteur', d.x_studio_adresse or ''),
              ('Chantier d&#39;origine', d.x_studio_chantier or ''),
              ('Code déchet', (d.x_studio_code or '')[-6:] and ('%s %s %s' % ((d.x_studio_code or '')[-6:-4],(d.x_studio_code or '')[-4:-2],(d.x_studio_code or '')[-2:])) or ''),
              ('Code interne site', d.x_studio_code or ''),
              ('Date', d.x_studio_date and d.x_studio_date.strftime('%d/%m/%Y') or ''),
              ('Tonnage estimé', d.x_studio_tonnage_estime and ('%.2f t' % d.x_studio_tonnage_estime) or ''),
            ]"/>
            <t t-foreach="rows" t-as="rw">
              <tr>
                <td style="border:1px solid #bbb;background:#EAF4F4;font-weight:bold;padding:8px;width:38%;"><t t-esc="rw[0]"/></td>
                <td style="border:1px solid #bbb;padding:8px;"><t t-esc="rw[1]"/></td>
              </tr>
            </t>
          </table>
          <p style="margin-top:12px;font-size:12px;">Le producteur atteste que les déchets sont <b>inertes</b>, non contaminés
          (pas d'amiante, de goudron, de plâtre, de bois, de plastiques, de terre végétale polluée…) et proviennent
          exclusivement du chantier indiqué ci-dessus.</p>
          <table style="width:100%;border-collapse:collapse;margin-top:18px;font-size:12px;">
            <tr>
              <td style="border:1px solid #bbb;padding:8px;height:90px;width:33%;vertical-align:top;"><b>Date :</b></td>
              <td style="border:1px solid #bbb;padding:8px;vertical-align:top;"><b>Signature et cachet du producteur :</b></td>
              <td style="border:1px solid #bbb;padding:8px;vertical-align:top;"><b>Visa exploitant (Maquignon) :</b></td>
            </tr>
          </table>
        </div>
      </t>
    </t>
  </t>
</t>'''

def ensure_qweb(key, arch):
    ex = kw("ir.ui.view","search_read",[[("key","=",key),("type","=","qweb")]],{"fields":["id"]})
    if ex:
        kw("ir.ui.view","write",[[ex[0]["id"]],{"arch_db":arch}]); vid=ex[0]["id"]
    else:
        vid = kw("ir.ui.view","create",[{"name":key,"type":"qweb","key":key,"arch_db":arch}])
    # xmlid pour le moteur de rapport
    mod,name = key.split(".",1)
    xd = kw("ir.model.data","search_read",[[("module","=",mod),("name","=",name)]],{"fields":["id"]})
    if not xd:
        kw("ir.model.data","create",[{"module":mod,"name":name,"model":"ir.ui.view","res_id":vid}])
    return vid

v_lp = ensure_qweb("website.report_livre_police", TPL_LP)
v_dap = ensure_qweb("website.report_dap", TPL_DAP)
print("templates:", v_lp, v_dap)

def ensure_report(name, model, report_name, pf=None):
    ex = kw("ir.actions.report","search_read",[[("report_name","=",report_name)]],{"fields":["id"]})
    vals = {"name":name,"model":model,"report_type":"qweb-pdf","report_name":report_name,
            "binding_model_id": kw("ir.model","search_read",[[("model","=",model)]],{"fields":["id"]})[0]["id"],
            "binding_type":"report","print_report_name":"'%s'" % name}
    if pf: vals["paperformat_id"]=pf
    if ex:
        kw("ir.actions.report","write",[[ex[0]["id"]],vals]); return ex[0]["id"]
    return kw("ir.actions.report","create",[vals])
r1 = ensure_report("Livre de police","x_livre_police","website.report_livre_police",pf_id)
r2 = ensure_report("Formulaire DAP","x_dap","website.report_dap")
print("rapports:", r1, r2)
