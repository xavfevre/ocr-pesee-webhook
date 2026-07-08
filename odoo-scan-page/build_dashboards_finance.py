# -*- coding: utf-8 -*-
"""Dashboards « Compte de résultat & Analytique » et « TGAP & REP »
(groupe États mensuels). Sources : account.move.line (P&L), account.analytic.line
(sections 001-008 = plans Sage), account.invoice.report (TGAP/REP/granulats)."""
import json, xmlrpc.client, ssl

URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
GID_NAME="États mensuels"
F_P="flt_period"; F_C="flt_company"

GLOBAL_FILTERS=[
 {"id":F_P,"type":"date","label":"Période"},
 {"id":F_C,"type":"relation","label":"Société","modelName":"res.company","defaultValueDisplayNames":[],"includeChildren":False},
]
STYLES={
 "1":{"bold":True,"fontSize":22,"textColor":"#01666B"},
 "2":{"fontSize":11,"textColor":"#6C757D","italic":True},
 "3":{"bold":True,"fontSize":13,"textColor":"#FFFFFF","fillColor":"#01666B","verticalAlign":"middle"},
 "4":{"bold":True,"fontSize":10,"textColor":"#6C757D","align":"center","verticalAlign":"middle","fillColor":"#EAF4F4"},
 "5":{"bold":True,"fontSize":18,"textColor":"#01666B","align":"center","verticalAlign":"middle","fillColor":"#EAF4F4"},
 "6":{"bold":True,"fontSize":18,"textColor":"#B45309","align":"center","verticalAlign":"middle","fillColor":"#FEF3C7"},
 "7":{"bold":True,"fontSize":13,"textColor":"#0f172a"},
}
FORMATS={"1":"#,##0\\€","2":"#,##0.00"}

def fm_aml():
    return {F_P:{"chain":"date","type":"date","offset":0},
            F_C:{"chain":"company_id","type":"many2one"}}
def fm_air():
    return {F_P:{"chain":"invoice_date","type":"date","offset":0},
            F_C:{"chain":"company_id","type":"many2one"}}

def sheet(cells,st,fo,merges,figs,cols=None,rows=None):
    return {"id":"dash","name":"Dashboard","colNumber":30,"rowNumber":900,
     "rows":rows or {},"cols":cols or {"0":{"size":300},"1":{"size":130},"2":{"size":130},"3":{"size":130},"4":{"size":130},"5":{"size":130}},
     "merges":merges,"cells":cells,"styles":st,"formats":fo,"borders":{},
     "conditionalFormats":[],"dataValidationRules":[],"figures":figs,"tables":[],
     "areGridLinesVisible":False,"isVisible":True,"headerGroups":{},"comments":{}}

def doc(sheets,pivots):
    return {"version":"18.5.10","sheets":sheets,"styles":STYLES,"formats":FORMATS,
     "borders":{},"revisionId":"START_REVISION","uniqueFigureIds":True,
     "settings":{"locale":{"name":"French / Français","code":"fr_FR","thousandsSeparator":" ",
       "decimalSeparator":",","dateFormat":"dd/mm/yyyy","timeFormat":"hh:mm:ss","formulaArgSeparator":";","weekStart":1}},
     "pivots":pivots,"pivotNextId":len(pivots)+1,"customTableStyles":{},
     "globalFilters":GLOBAL_FILTERS,"lists":{},"listNextId":1,"chartOdooMenusReferences":{}}

# ══════════ D5 — COMPTE DE RÉSULTAT & ANALYTIQUE ══════════
INCOME=["income","income_other"]
EXPENSE=["expense","expense_depreciation","expense_direct_cost"]
M_BAL=[{"id":"balance","fieldName":"balance","aggregator":"sum","userDefinedName":"Solde"}]
M_AMT=[{"id":"amount","fieldName":"amount","aggregator":"sum","userDefinedName":"Montant"}]

pv={
 "1":{"type":"ODOO","model":"account.move.line","name":"Produits","formulaId":"1",
   "rows":[{"fieldName":"account_id"}],"columns":[],"measures":M_BAL,
   "domain":["&",["parent_state","=","posted"],["account_id.account_type","in",INCOME]],
   "context":{},"sortedColumn":{"measure":"balance","order":"asc","domain":[]},"fieldMatching":fm_aml()},
 "2":{"type":"ODOO","model":"account.move.line","name":"Charges","formulaId":"2",
   "rows":[{"fieldName":"account_id"}],"columns":[],"measures":M_BAL,
   "domain":["&",["parent_state","=","posted"],["account_id.account_type","in",EXPENSE]],
   "context":{},"sortedColumn":{"measure":"balance","order":"desc","domain":[]},"fieldMatching":fm_aml()},
}
# 8 pivots analytiques (un par plan/section)
SECTIONS=[("account_id","Projets (transport, services…)"),
          ("x_plan2_id","001 · Transports"),
          ("x_plan3_id","002 · TP - Démolition - Décharge"),
          ("x_plan4_id","003 · Terre de gobetage"),
          ("x_plan5_id","004 · Blocs"),
          ("x_plan6_id","005 · Tranches"),
          ("x_plan7_id","006 · Pré-sciées"),
          ("x_plan8_id","007 · Revente de marchandises")]
for i,(fld,lbl) in enumerate(SECTIONS, start=3):
    pv[str(i)]={"type":"ODOO","model":"account.analytic.line","name":lbl,"formulaId":str(i),
      "rows":[],"columns":[],"measures":M_AMT,
      "domain":[[fld,"!=",False]],"context":{},"sortedColumn":None,"fieldMatching":fm_aml()}

cells={
 "A1":"Compte de résultat & Analytique",
 "A2":"Écritures comptables validées · filtres Période / Société · produits/charges par compte, sections analytiques Sage 001-008",
 "A4":"PRODUITS","A5":"=-PIVOT.VALUE(1,\"balance\")",
 "C4":"CHARGES","C5":"=PIVOT.VALUE(2,\"balance\")",
 "E4":"RÉSULTAT","E5":"=A5-C5",
 "A8":"RÉPARTITION ANALYTIQUE (sections Sage) — montants sur la période filtrée",
 "A9":"Section","B9":"Montant",
 "A29":"PRODUITS PAR COMPTE (solde comptable : signe négatif = produit)",
 "A30":"=PIVOT(1, 80, TRUE, TRUE)",
 "A115":"CHARGES PAR COMPTE",
 "A116":"=PIVOT(2, 200, TRUE, TRUE)",
}
for i,(fld,lbl) in enumerate(SECTIONS, start=3):
    r=10+(i-3)
    cells[f"A{r}"]=lbl
    cells[f"B{r}"]=f'=PIVOT.VALUE({i},"amount")'
cells["A18"]="TOTAL"; cells["B18"]="=SUM(B10:B17)"
st={"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"C4:D4":4,"C5:D5":6,"E4:F4":4,"E5:F5":5,
    "A8:F8":3,"A9":4,"B9":4,"A18":7,"B18":7,"A29:F29":3,"A115:F115":3}
fo={"A5:B5":1,"C5:D5":1,"E5:F5":1,"B10:B18":1}
merges=["A1:H1","A2:H2","A4:B4","A5:B5","C4:D4","C5:D5","E4:F4","E5:F5","A8:F8","A29:F29","A115:F115"]
D5=doc([sheet(cells,st,fo,merges,[],
    cols={"0":{"size":300},"1":{"size":140},"2":{"size":140},"3":{"size":140},"4":{"size":140},"5":{"size":140}},
    rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"7":{"size":28},"28":{"size":28},"114":{"size":28}})],pv)

# ══════════ D6 — TGAP & REP ══════════
BASE=["&","&",["move_type","in",["out_invoice","out_refund"]],["state","=","posted"],["product_id","!=",False]]
def and_dom(c): return ["&",c]+BASE
D_TGAP=and_dom(["product_id.default_code","=","TGAP"])
D_GRAN=and_dom(["product_categ_id","child_of",[38,39,66,25]])   # H-Concassé, H-Enrochement, H-Remblai, Sable et Granulats
D_REP =and_dom(["product_categ_id.name","ilike","eco contribution"])
M_QC=[{"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Tonnes"},
      {"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"Montant HT"}]
YM=[{"fieldName":"invoice_date","granularity":"year"},{"fieldName":"invoice_date","granularity":"month"}]
pv6={
 "1":{"type":"ODOO","model":"account.invoice.report","name":"TGAP refacturée","formulaId":"1",
   "rows":[],"columns":YM,"measures":M_QC,"domain":D_TGAP,"context":{},"sortedColumn":None,"fieldMatching":fm_air()},
 "2":{"type":"ODOO","model":"account.invoice.report","name":"Base granulats","formulaId":"2",
   "rows":[{"fieldName":"product_categ_id"}],"columns":[],"measures":M_QC,"domain":D_GRAN,
   "context":{},"sortedColumn":{"measure":"quantity","order":"desc","domain":[]},"fieldMatching":fm_air()},
 "3":{"type":"ODOO","model":"account.invoice.report","name":"Granulats mensuel","formulaId":"3",
   "rows":[{"fieldName":"product_categ_id"}],"columns":YM,
   "measures":[{"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Tonnes"}],
   "domain":D_GRAN,"context":{},"sortedColumn":None,"fieldMatching":fm_air()},
 "4":{"type":"ODOO","model":"account.invoice.report","name":"REP","formulaId":"4",
   "rows":[{"fieldName":"company_id"}],"columns":YM,"measures":M_QC,"domain":D_REP,
   "context":{},"sortedColumn":None,"fieldMatching":fm_air()},
 "5":{"type":"ODOO","model":"account.invoice.report","name":"TGAP tot","formulaId":"5",
   "rows":[],"columns":[],"measures":M_QC,"domain":D_TGAP,"context":{},"sortedColumn":None,"fieldMatching":fm_air()},
 "6":{"type":"ODOO","model":"account.invoice.report","name":"Granulats tot","formulaId":"6",
   "rows":[],"columns":[],"measures":M_QC,"domain":D_GRAN,"context":{},"sortedColumn":None,"fieldMatching":fm_air()},
 "7":{"type":"ODOO","model":"account.invoice.report","name":"REP tot","formulaId":"7",
   "rows":[],"columns":[],"measures":M_QC,"domain":D_REP,"context":{},"sortedColumn":None,"fieldMatching":fm_air()},
}
figs6=[{"id":"c6-gran","width":1130,"height":320,"tag":"chart",
 "data":{"title":{"text":"Tonnages granulats facturés par mois (base TGAP)"},"background":"","legendPosition":"top",
  "metaData":{"groupBy":["invoice_date:month"],"measure":"quantity","order":None,
              "resModel":"account.invoice.report","mode":"line","cumulatedStart":False},
  "searchParams":{"comparison":None,"context":{},"domain":D_GRAN,"groupBy":["invoice_date:month"],"orderBy":[]},
  "type":"odoo_line","dataSets":[],"humanize":True,"verticalAxisPosition":"left",
  "stacked":False,"cumulatedStart":False,"fillArea":True,"chartId":"c6-gran","fieldMatching":fm_air()},
 "offset":{"x":0,"y":170},"col":0,"row":0}]
cells6={
 "A1":"TGAP & REP (éco-contributions)",
 "A2":"TGAP granulats : base = tonnages facturés (H-Concassé, H-Enrochement, H-Remblai, Sable et Granulats) · REP = catégorie Eco Contribution",
 "A4":"TGAP REFACTURÉE","A5":"=PIVOT.VALUE(5,\"price_subtotal\")",
 "C4":"TONNES TGAP FACT.","C5":"=PIVOT.VALUE(5,\"quantity\")",
 "E4":"BASE GRANULATS (t)","E5":"=PIVOT.VALUE(6,\"quantity\")",
 "G4":"REP FACTURÉE","G5":"=PIVOT.VALUE(7,\"price_subtotal\")",
 "A7":"⚠ Rappel : l'article [TGAP] « Contribution TGAP (coût à la tonne) » (0,23 €/t) vient d'être créé — à ajouter sur les factures granulats pour refacturer la taxe.",
 "A24":"BASE TGAP — TONNAGES GRANULATS PAR CATÉGORIE","A25":"=PIVOT(2, 20, TRUE, TRUE)",
 "A50":"TONNAGES GRANULATS PAR MOIS","A51":"=PIVOT(3, 20, TRUE, TRUE)",
 "A76":"TGAP REFACTURÉE PAR MOIS","A77":"=PIVOT(1, 10, TRUE, TRUE)",
 "A92":"REP (ECO CONTRIBUTION) PAR SOCIÉTÉ ET PAR MOIS","A93":"=PIVOT(4, 15, TRUE, TRUE)",
}
st6={"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"C4:D4":4,"C5:D5":5,"E4:F4":4,"E5:F5":6,"G4:H4":4,"G5:H5":5,
     "A7:J7":2,"A24:F24":3,"A50:N50":3,"A76:N76":3,"A92:N92":3}
fo6={"A5:B5":1,"G5:H5":1,"C5:D5":2,"E5:F5":2}
merges6=["A1:H1","A2:J2","A4:B4","A5:B5","C4:D4","C5:D5","E4:F4","E5:F5","G4:H4","G5:H5",
         "A7:J7","A24:F24","A50:N50","A76:N76","A92:N92"]
D6=doc([sheet(cells6,st6,fo6,merges6,figs6,
    rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"6":{"size":24},"23":{"size":28},"49":{"size":28},"75":{"size":28},"91":{"size":28}})],pv6)

# ══════════ Création ══════════
ctx=ssl.create_default_context()
c=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common",context=ctx); uid=c.authenticate(DB,U,P,{})
m=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object",context=ctx)
def x(mo_,me,*a,**k): return m.execute_kw(DB,uid,P,mo_,me,list(a),k)
gid=x("spreadsheet.dashboard.group","search_read",[("name","=",GID_NAME)],fields=["id"])[0]["id"]
for name,D in [("Compte de résultat & Analytique",D5),("TGAP & REP",D6)]:
    data=json.dumps(D,ensure_ascii=False); json.loads(data)
    ex=x("spreadsheet.dashboard","search_read",[("name","=",name),("dashboard_group_id","=",gid)],fields=["id"])
    if ex:
        x("spreadsheet.dashboard","write",[ex[0]["id"]],{"spreadsheet_data":data}); print("maj:",name,ex[0]["id"])
    else:
        did=x("spreadsheet.dashboard","create",{"name":name,"dashboard_group_id":gid,
             "spreadsheet_data":data,"is_published":True}); print("créé:",name,did,len(data),"o")
