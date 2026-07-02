# -*- coding: utf-8 -*-
"""Dashboard 'CA Carrière d'Haims' — réplique Odoo du rapport Sage 'Chiffre d'affaires Haims'.
3 onglets : Synthèse (KPIs par activité), CA par article (sections Sage), Par mois.
Source : account.invoice.report (factures clients validées, société 4), maj instantanée."""
import os, json, xmlrpc.client, ssl
URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
GROUP_ID = 10  # groupe "Par activité"
F_PERIOD="flt_period"; F_CATEG="flt_categ"

DOM = ["&","&","&",
       ["company_id","=",4],
       ["move_type","in",["out_invoice","out_refund"]],
       ["state","=","posted"],
       ["product_id","!=",False]]

def fm():
    return {F_PERIOD:{"chain":"invoice_date","type":"date","offset":0},
            F_CATEG:{"chain":"product_categ_id","type":"many2one"}}

pivots={
 # 1 : par catégorie > article (le rapport Sage)
 "1":{"type":"ODOO","model":"account.invoice.report","name":"CA par article","formulaId":"1",
   "rows":[{"fieldName":"product_categ_id"},{"fieldName":"product_id"}],
   "columns":[],
   "measures":[{"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Qté vendues"},
               {"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"}],
   "domain":DOM,"context":{},"sortedColumn":None,"fieldMatching":fm()},
 # 2 : par catégorie seule (KPIs synthèse)
 "2":{"type":"ODOO","model":"account.invoice.report","name":"CA par activité","formulaId":"2",
   "rows":[{"fieldName":"product_categ_id"}],
   "columns":[],
   "measures":[{"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"},
               {"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Qté"}],
   "domain":DOM,"context":{},"sortedColumn":{"measure":"price_subtotal","order":"desc","domain":[]},
   "fieldMatching":fm()},
 # 3 : catégorie x mois (évolution)
 "3":{"type":"ODOO","model":"account.invoice.report","name":"CA par mois","formulaId":"3",
   "rows":[{"fieldName":"product_categ_id"}],
   "columns":[{"fieldName":"invoice_date","granularity":"year"},{"fieldName":"invoice_date","granularity":"month"}],
   "measures":[{"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"}],
   "domain":DOM,"context":{},"sortedColumn":None,"fieldMatching":fm()},
}
global_filters=[
 {"id":F_PERIOD,"type":"date","label":"Période"},
 {"id":F_CATEG,"type":"relation","label":"Catégorie","modelName":"product.category","defaultValueDisplayNames":[],"includeChildren":True},
]
styles={
 "1":{"bold":True,"fontSize":22,"textColor":"#01666B"},
 "2":{"fontSize":11,"textColor":"#6C757D","italic":True},
 "3":{"bold":True,"fontSize":13,"textColor":"#FFFFFF","fillColor":"#01666B","verticalAlign":"middle"},
 "4":{"bold":True,"fontSize":10,"textColor":"#6C757D","align":"center","verticalAlign":"middle","fillColor":"#EAF4F4"},
 "5":{"bold":True,"fontSize":18,"textColor":"#01666B","align":"center","verticalAlign":"middle","fillColor":"#EAF4F4"},
}
formats={"1":"#,##0\\€","2":"#,##0.00"}

def base_sheet(sid,name,cells,sstyles,sformats,merges,cols,rows,grid=True):
    return {"id":sid,"name":name,"colNumber":30,"rowNumber":150,"rows":rows,"cols":cols,
     "merges":merges,"cells":cells,"styles":sstyles,"formats":sformats,"borders":{},
     "conditionalFormats":[],"dataValidationRules":[],"figures":[],"tables":[],
     "areGridLinesVisible":grid,"isVisible":True,"headerGroups":{},"comments":{}}

synth=base_sheet("s_synth","Synthèse",
  {"A1":"Chiffre d'affaires — Carrière d'Haims",
   "A2":"Factures clients validées · filtres Période / Catégorie en haut · mise à jour instantanée",
   "A4":"CA HT TOTAL","A5":"=PIVOT.VALUE(2,\"price_subtotal\")",
   "A7":"DÉTAIL PAR ACTIVITÉ (CA HT + quantités)",
   "A8":"=PIVOT(2, 40, TRUE, TRUE)"},
  {"A1":1,"A2":2,"A4:C4":4,"A5:C5":5,"A7:F7":3},
  {"A5:C5":1},
  ["A1:H1","A2:H2","A4:C4","A5:C5","A7:F7"],
  {"0":{"size":260},"1":{"size":130},"2":{"size":130},"3":{"size":130},"4":{"size":130},"5":{"size":130}},
  {"0":{"size":44},"1":{"size":22},"3":{"size":24},"4":{"size":42},"6":{"size":30}}, grid=False)

articles=base_sheet("s_art","CA par article",
  {"A1":"CA PAR ARTICLE — sections par activité (équivalent rapport Sage)",
   "A2":"=PIVOT(1, 300, TRUE, TRUE)"},
  {"A1:F1":3},{},["A1:F1"],
  {"0":{"size":320},"1":{"size":130},"2":{"size":130}},
  {"0":{"size":30}}, grid=True)

mois=base_sheet("s_mois","Par mois",
  {"A1":"ÉVOLUTION MENSUELLE — CA HT par activité",
   "A2":"=PIVOT(3, 200, TRUE, TRUE)"},
  {"A1:N1":3},{},["A1:N1"],
  {"0":{"size":260}},
  {"0":{"size":30}}, grid=True)

doc={"version":"18.5.10","sheets":[synth,articles,mois],
 "styles":styles,"formats":formats,"borders":{},"revisionId":"START_REVISION","uniqueFigureIds":True,
 "settings":{"locale":{"name":"French / Français","code":"fr_FR","thousandsSeparator":" ",
   "decimalSeparator":",","dateFormat":"dd/mm/yyyy","timeFormat":"hh:mm:ss","formulaArgSeparator":";","weekStart":1}},
 "pivots":pivots,"pivotNextId":4,"customTableStyles":{},
 "globalFilters":global_filters,"lists":{},"listNextId":1,"chartOdooMenusReferences":{}}
data=json.dumps(doc,ensure_ascii=False); json.loads(data)
print("JSON OK, taille:",len(data))

ctx=ssl.create_default_context()
c=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common",context=ctx); uid=c.authenticate(DB,U,P,{})
m=xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object",context=ctx)
def x(mo_,me,*a,**k): return m.execute_kw(DB,uid,P,mo_,me,list(a),k)
ex=x("spreadsheet.dashboard","search_read",[("name","=","CA Carrière d'Haims")],fields=["id"])
if ex:
    x("spreadsheet.dashboard","write",[ex[0]["id"]],{"spreadsheet_data":data})
    print("dashboard mis à jour:",ex[0]["id"])
else:
    did=x("spreadsheet.dashboard","create",{"name":"CA Carrière d'Haims","dashboard_group_id":GROUP_ID,
        "spreadsheet_data":data,"is_published":True})
    print("dashboard créé:",did)
