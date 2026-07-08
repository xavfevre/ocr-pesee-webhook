# -*- coding: utf-8 -*-
"""Groupe de dashboards « États mensuels » — réplique des états Sage mensuels
(Etat_Fact_op) en dashboards Odoo natifs, données live account.invoice.report.
D1 Pierres (CA+cubage familles/clients) · D2 Transport & TP · D3 Décharge,
contrôles 0 €, palettes · D4 Comparatif annuel."""
import json, xmlrpc.client, ssl

URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
F_P="flt_period"; F_C="flt_company"

BASE = ["&","&",["move_type","in",["out_invoice","out_refund"]],["state","=","posted"],["product_id","!=",False]]
def dom(extra=None):
    d = list(BASE)
    if extra:
        d = ["&"] + extra + d[1:] if False else None
    return d
# domaines : préfixe & pour chaque condition supplémentaire
def and_dom(*conds):
    d = list(BASE)
    for c in reversed(conds):
        d = ["&", c] + d
    return d

def FM():
    return {F_P:{"chain":"invoice_date","type":"date","offset":0},
            F_C:{"chain":"company_id","type":"many2one"}}

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
}
FORMATS={"1":"#,##0\\€","2":"#,##0.000"}

def measure(fid,name,label):
    return {"id":fid,"fieldName":name,"aggregator":"sum","userDefinedName":label}

M_CA  = measure("price_subtotal","price_subtotal","CA HT Net")
M_QTE = measure("quantity","quantity","Quantité")

def pivot(pid,name,rows,cols,measures,domain,sort=None):
    return {"type":"ODOO","model":"account.invoice.report","name":name,"formulaId":pid,
            "rows":[{"fieldName":r} if isinstance(r,str) else r for r in rows],
            "columns":[{"fieldName":c} if isinstance(c,str) else c for c in cols],
            "measures":measures,"domain":domain,"context":{},
            "sortedColumn":sort,"fieldMatching":FM()}

def chart(cid,ctype,mode,groupby,title,domain,x,y,w,h,measure_f="price_subtotal"):
    return {"id":cid,"width":w,"height":h,"tag":"chart",
        "data":{"title":{"text":title},"background":"","legendPosition":"top",
        "metaData":{"groupBy":[groupby],"measure":measure_f,"order":None,
                    "resModel":"account.invoice.report","mode":mode,"cumulatedStart":False},
        "searchParams":{"comparison":None,"context":{},"domain":domain,"groupBy":[groupby],"orderBy":[]},
        "type":ctype,"dataSets":[],"humanize":True,"verticalAxisPosition":"left",
        "stacked":False,"cumulatedStart":False,"fillArea":(mode=="line"),"chartId":cid,
        "fieldMatching":FM()},
        "offset":{"x":x,"y":y},"col":0,"row":0}

def sheet(cells,sheet_styles,sheet_formats,merges,figs,cols=None,rows=None):
    return {"id":"dash","name":"Dashboard","colNumber":30,"rowNumber":1200,
     "rows":rows or {}, "cols":cols or {"0":{"size":300},"1":{"size":125},"2":{"size":125},"3":{"size":125},"4":{"size":125},"5":{"size":125}},
     "merges":merges,"cells":cells,"styles":sheet_styles,"formats":sheet_formats,
     "borders":{},"conditionalFormats":[],"dataValidationRules":[],"figures":figs,
     "tables":[],"areGridLinesVisible":False,"isVisible":True,"headerGroups":{},"comments":{}}

def doc(sheets,pivots,lists=None,list_next=1):
    return {"version":"18.5.10","sheets":sheets,"styles":STYLES,"formats":FORMATS,
     "borders":{},"revisionId":"START_REVISION","uniqueFigureIds":True,
     "settings":{"locale":{"name":"French / Français","code":"fr_FR","thousandsSeparator":" ",
       "decimalSeparator":",","dateFormat":"dd/mm/yyyy","timeFormat":"hh:mm:ss","formulaArgSeparator":";","weekStart":1}},
     "pivots":pivots,"pivotNextId":len(pivots)+1,"customTableStyles":{},
     "globalFilters":GLOBAL_FILTERS,"lists":lists or {},"listNextId":list_next,
     "chartOdooMenusReferences":{}}

# ═══ D1 — PIERRES : CA & CUBAGE ═══
D_PIERRE = and_dom(["product_categ_id","child_of",[6,42]])   # Pierres + Taille
D_PIERRE_M3 = and_dom(["product_categ_id","child_of",[6]])   # cubage : familles pierre
p1={
 "1":pivot("1","Familles",["product_categ_id"],[],[M_CA,M_QTE],D_PIERRE,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
 "2":pivot("2","Clients",["partner_id"],[],[M_CA,M_QTE],D_PIERRE,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
 "3":pivot("3","Mois x famille",["product_categ_id"],
           [{"fieldName":"invoice_date","granularity":"year"},{"fieldName":"invoice_date","granularity":"month"}],
           [M_CA],D_PIERRE),
 "4":pivot("4","Cubage",[],[],[M_QTE],D_PIERRE_M3),
}
c1=[chart("c1-fam","odoo_bar","bar","product_categ_id","CA HT par famille de pierre",D_PIERRE,0,150,555,330),
    chart("c1-mois","odoo_line","line","invoice_date:month","Évolution mensuelle CA Pierres",D_PIERRE,575,150,555,330)]
s1=sheet({
 "A1":"Pierres de taille — CA & cubage","A2":"Familles Pierres + Taille · factures validées · filtres Période / Société",
 "A4":"CA HT PIERRES","A5":"=PIVOT.VALUE(1,\"price_subtotal\")",
 "C4":"CUBAGE (m³)","C5":"=PIVOT.VALUE(4,\"quantity\")",
 "A24":"PAR FAMILLE (CA HT + quantités)","A25":"=PIVOT(1, 40, TRUE, TRUE)",
 "A70":"PAR CLIENT (triés par CA)","A71":"=PIVOT(2, 400, TRUE, TRUE)",
 "A475":"ÉVOLUTION MENSUELLE PAR FAMILLE","A476":"=PIVOT(3, 40, TRUE, TRUE)"},
 {"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"C4:D4":4,"C5:D5":5,"A24:F24":3,"A70:F70":3,"A475:N475":3},
 {"A5:B5":1,"C5:D5":2},
 ["A1:H1","A2:H2","A4:B4","A5:B5","C4:D4","C5:D5","A24:F24","A70:F70","A475:N475"],
 c1, rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"23":{"size":28},"69":{"size":28},"474":{"size":28}})
DOC1=doc([s1],p1)

# ═══ D2 — TRANSPORT & TP ═══
D_TRANS = and_dom(["product_categ_id","child_of",[33,40]])
D_TP    = and_dom(["product_categ_id","child_of",[35,41]])
p2={
 "1":pivot("1","Transport clients",["partner_id"],[],[M_CA],D_TRANS,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
 "2":pivot("2","TP clients",["partner_id"],[],[M_CA],D_TP,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
 "3":pivot("3","Transport total",[],[],[M_CA],D_TRANS),
 "4":pivot("4","TP total",[],[],[M_CA],D_TP),
}
c2=[chart("c2-t","odoo_line","line","invoice_date:month","Transport — CA mensuel",D_TRANS,0,150,555,320),
    chart("c2-tp","odoo_line","line","invoice_date:month","TP — CA mensuel",D_TP,575,150,555,320)]
s2=sheet({
 "A1":"Transport & Travaux Publics","A2":"Catégories Transport / H-Transport et TP / H-TP · factures validées",
 "A4":"CA TRANSPORT","A5":"=PIVOT.VALUE(3,\"price_subtotal\")",
 "C4":"CA TP","C5":"=PIVOT.VALUE(4,\"price_subtotal\")",
 "A23":"TRANSPORT — PAR CLIENT","A24":"=PIVOT(1, 250, TRUE, TRUE)",
 "A278":"TP — PAR CLIENT","A279":"=PIVOT(2, 250, TRUE, TRUE)"},
 {"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"C4:D4":4,"C5:D5":5,"A23:F23":3,"A278:F278":3},
 {"A5:B5":1,"C5:D5":1},
 ["A1:H1","A2:H2","A4:B4","A5:B5","C4:D4","C5:D5","A23:F23","A278:F278"],
 c2, rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"22":{"size":28},"277":{"size":28}})
DOC2=doc([s2],p2)

# ═══ D3 — DÉCHARGE, CONTRÔLES & PALETTES ═══
D_DECH = and_dom(["product_id.name","ilike","décharge"])
D_PAL  = and_dom(["product_id.name","ilike","palette"])
p3={
 "1":pivot("1","Décharge clients",["partner_id"],[],[M_CA,M_QTE],D_DECH,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
 "2":pivot("2","Décharge total",[],[],[M_CA,M_QTE],D_DECH),
 "3":pivot("3","Palettes",["partner_id"],[],[M_QTE,M_CA],D_PAL,
           {"measure":"price_subtotal","order":"desc","domain":[]}),
}
LIST_ZERO={"1":{"id":"1","name":"Lignes ≤ 0 €","model":"account.move.line",
 "columns":["date","move_name","partner_id","name","price_subtotal"],
 "domain":[["parent_state","=","posted"],
           ["move_id.move_type","in",["out_invoice","out_refund"]],
           ["display_type","=","product"],["price_subtotal","<=",0]],
 "context":{},"orderBy":[{"name":"date","asc":False}],
 "fieldMatching":{F_P:{"chain":"date","type":"date","offset":0},
                  F_C:{"chain":"company_id","type":"many2one"}}}}
cells3={
 "A1":"Décharge · Contrôles · Palettes","A2":"Factures validées · filtres Période / Société",
 "A4":"CA DÉCHARGE","A5":"=PIVOT.VALUE(2,\"price_subtotal\")",
 "C4":"TONNAGE FACTURÉ","C5":"=PIVOT.VALUE(2,\"quantity\")",
 "A8":"DÉCHARGE — PAR CLIENT (CA + tonnes)","A9":"=PIVOT(1, 80, TRUE, TRUE)",
 "A94":"⚠ CONTRÔLE — LIGNES DE FACTURE À 0 € OU NÉGATIVES (30 dernières)",
 "A126":"PALETTES — CONSIGNES PAR CLIENT (qté + CA)","A127":"=PIVOT(3, 80, TRUE, TRUE)",
}
# tableau liste contrôle : en-têtes + 30 lignes
LIST_COLS=["date","move_name","partner_id","name","price_subtotal"]
for j,f in enumerate(LIST_COLS):
    cells3[f"{chr(65+j)}95"]=f'=ODOO.LIST.HEADER(1,"{f}")'
for i in range(30):
    for j,f in enumerate(LIST_COLS):
        cells3[f"{chr(65+j)}{96+i}"]=f'=ODOO.LIST(1,{i+1},"{f}")'
s3=sheet(cells3,
 {"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"C4:D4":4,"C5:D5":5,"A8:F8":3,"A94:F94":3,"A95:E95":4,"A126:F126":3},
 {"A5:B5":1,"C5:D5":2,"E96:E125":1},
 ["A1:H1","A2:H2","A4:B4","A5:B5","C4:D4","C5:D5","A8:F8","A94:F94","A126:F126"],
 [], cols={"0":{"size":110},"1":{"size":130},"2":{"size":230},"3":{"size":330},"4":{"size":120},"5":{"size":120}},
 rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"7":{"size":28},"93":{"size":28},"125":{"size":28}})
DOC3=doc([s3],p3,lists=LIST_ZERO,list_next=2)

# ═══ D4 — COMPARATIF ANNUEL ═══
p4={
 "1":pivot("1","Mois x années",
           [{"fieldName":"invoice_date","granularity":"month_number"}],
           [{"fieldName":"invoice_date","granularity":"year"}],
           [M_CA],list(BASE)),
 "2":pivot("2","Sociétés x années",["company_id"],
           [{"fieldName":"invoice_date","granularity":"year"}],[M_CA],list(BASE)),
}
c4=[chart("c4-line","odoo_line","line","invoice_date:month","CA HT mensuel — toutes activités",list(BASE),0,150,1130,330)]
s4=sheet({
 "A1":"Comparatif annuel — CA toutes activités","A2":"Le filtre Période est volontairement large : comparez les années entre elles",
 "A4":"CA HT TOTAL","A5":"=PIVOT.VALUE(1,\"price_subtotal\")",
 "A24":"CA PAR MOIS × ANNÉE (équivalent feuille Sage « CA TOTAL »)","A25":"=PIVOT(1, 20, TRUE, TRUE)",
 "A50":"CA PAR SOCIÉTÉ × ANNÉE","A51":"=PIVOT(2, 15, TRUE, TRUE)"},
 {"A1":1,"A2":2,"A4:B4":4,"A5:B5":5,"A24:N24":3,"A50:N50":3},
 {"A5:B5":1},
 ["A1:H1","A2:H2","A4:B4","A5:B5","A24:N24","A50:N50"],
 c4, rows={"0":{"size":42},"3":{"size":22},"4":{"size":40},"23":{"size":28},"49":{"size":28}})
DOC4=doc([s4],p4)

# ═══ Création dans Odoo ═══
ctx=ssl.create_default_context()
c=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common",context=ctx); uid=c.authenticate(DB,U,P,{})
m=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object",context=ctx)
def x(mo_,me,*a,**k): return m.execute_kw(DB,uid,P,mo_,me,list(a),k)

grp=x("spreadsheet.dashboard.group","search_read",[("name","=","États mensuels")],fields=["id"])
gid=grp[0]["id"] if grp else x("spreadsheet.dashboard.group","create",{"name":"États mensuels","sequence":11})
print("groupe:",gid)

for name,D in [("Pierres — CA & cubage",DOC1),("Transport & TP",DOC2),
               ("Décharge · Contrôles · Palettes",DOC3),("Comparatif annuel",DOC4)]:
    data=json.dumps(D,ensure_ascii=False); json.loads(data)
    ex=x("spreadsheet.dashboard","search_read",[("name","=",name),("dashboard_group_id","=",gid)],fields=["id"])
    if ex:
        x("spreadsheet.dashboard","write",[ex[0]["id"]],{"spreadsheet_data":data})
        print("maj:",name,ex[0]["id"],len(data),"o")
    else:
        did=x("spreadsheet.dashboard","create",{"name":name,"dashboard_group_id":gid,
            "spreadsheet_data":data,"is_published":True})
        print("créé:",name,did,len(data),"o")
