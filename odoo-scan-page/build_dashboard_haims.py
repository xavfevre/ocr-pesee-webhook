# -*- coding: utf-8 -*-
"""Dashboard 'Chiffre d'affaires par société' — réplique Odoo du rapport Sage CA.
3 onglets : Synthèse (Société›Activité), CA par article (Société›Activité›Article),
Par mois. Source : account.invoice.report (factures validées, toutes sociétés)."""
import json, xmlrpc.client, ssl
URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
GROUP_ID = 10; DASH_ID = 23
F_PERIOD="flt_period"; F_COMPANY="flt_company"; F_CATEG="flt_categ"

DOM = ["&","&",
       ["move_type","in",["out_invoice","out_refund"]],
       ["state","=","posted"],
       ["product_id","!=",False]]

def fm():
    return {F_PERIOD:{"chain":"invoice_date","type":"date","offset":0},
            F_COMPANY:{"chain":"company_id","type":"many2one"},
            F_CATEG:{"chain":"product_categ_id","type":"many2one"}}

MEAS_QC = [{"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Qté vendues"},
           {"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"}]
MEAS_CQ = [{"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"},
           {"id":"quantity","fieldName":"quantity","aggregator":"sum","userDefinedName":"Qté"}]

pivots={
 "1":{"type":"ODOO","model":"account.invoice.report","name":"CA par article","formulaId":"1",
   "rows":[{"fieldName":"company_id"},{"fieldName":"product_categ_id"},{"fieldName":"product_id"}],
   "columns":[], "measures":MEAS_QC,
   "domain":DOM,"context":{},"sortedColumn":None,"fieldMatching":fm()},
 "2":{"type":"ODOO","model":"account.invoice.report","name":"CA par activité","formulaId":"2",
   "rows":[{"fieldName":"company_id"},{"fieldName":"product_categ_id"}],
   "columns":[], "measures":MEAS_CQ,
   "domain":DOM,"context":{},"sortedColumn":None,"fieldMatching":fm()},
 "3":{"type":"ODOO","model":"account.invoice.report","name":"CA par mois","formulaId":"3",
   "rows":[{"fieldName":"company_id"},{"fieldName":"product_categ_id"}],
   "columns":[{"fieldName":"invoice_date","granularity":"year"},{"fieldName":"invoice_date","granularity":"month"}],
   "measures":[{"id":"price_subtotal","fieldName":"price_subtotal","aggregator":"sum","userDefinedName":"CA HT Net"}],
   "domain":DOM,"context":{},"sortedColumn":None,"fieldMatching":fm()},
}
global_filters=[
 {"id":F_PERIOD,"type":"date","label":"Période"},
 {"id":F_COMPANY,"type":"relation","label":"Société","modelName":"res.company","defaultValueDisplayNames":[],"includeChildren":False},
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
    return {"id":sid,"name":name,"colNumber":30,"rowNumber":700,"rows":rows,"cols":cols,
     "merges":merges,"cells":cells,"styles":sstyles,"formats":sformats,"borders":{},
     "conditionalFormats":[],"dataValidationRules":[],"figures":[],"tables":[],
     "areGridLinesVisible":grid,"isVisible":True,"headerGroups":{},"comments":{}}

cells={
 "A1":"Chiffre d'affaires — toutes sociétés",
 "A2":"Factures clients validées · filtres Période / Société / Catégorie en haut · mise à jour instantanée",
 "A4":"CA HT TOTAL","A5":"=PIVOT.VALUE(2,\"price_subtotal\")",
 "A40":"DÉTAIL PAR SOCIÉTÉ ET ACTIVITÉ (CA HT + quantités)",
 "A41":"=PIVOT(2, 120, TRUE, TRUE)",
 "A165":"CA PAR ARTICLE — Société › Activité › Article (équivalent rapport Sage)",
 "A166":"=PIVOT(1, 600, TRUE, TRUE)",
 "A770":"ÉVOLUTION MENSUELLE — CA HT par société et activité",
 "A771":"=PIVOT(3, 200, TRUE, TRUE)",
}
sheet_styles={"A1":1,"A2":2,"A4:C4":4,"A5:C5":5,"A40:F40":3,"A165:F165":3,"A770:N770":3}
sheet_formats={"A5:C5":1}
merges=["A1:H1","A2:H2","A4:C4","A5:C5","A40:F40","A165:F165","A770:N770"]
cols={"0":{"size":320},"1":{"size":130},"2":{"size":130},"3":{"size":130},"4":{"size":130},"5":{"size":130}}
rows={"0":{"size":44},"1":{"size":22},"3":{"size":24},"4":{"size":42},"39":{"size":30},"164":{"size":30},"769":{"size":30}}

def chart(cid, ctype, mode, groupby, title, x, y, w, h, legend="top"):
    d = {"title":{"text":title},"background":"","legendPosition":legend,
         "metaData":{"groupBy":[groupby],"measure":"price_subtotal","order":None,
                     "resModel":"account.invoice.report","mode":mode,"cumulatedStart":False},
         "searchParams":{"comparison":None,"context":{},"domain":DOM,"groupBy":[groupby],"orderBy":[]},
         "type":ctype,"dataSets":[],"humanize":True,"verticalAxisPosition":"left",
         "stacked":False,"cumulatedStart":False,"fillArea":(mode=="line"),"chartId":cid,
         "fieldMatching":{F_PERIOD:{"chain":"invoice_date","type":"date","offset":0},
                          F_COMPANY:{"chain":"company_id","type":"many2one"},
                          F_CATEG:{"chain":"product_categ_id","type":"many2one"}}}
    return {"id":cid,"width":w,"height":h,"tag":"chart","data":d,
            "offset":{"x":x,"y":y},"col":0,"row":0}

figs=[
  chart("chart-ca-soc","odoo_bar","bar","company_id","CA HT par société",0,150,555,330),
  chart("chart-ca-cat","odoo_pie","pie","product_categ_id","Répartition du CA par activité",575,150,555,330),
  chart("chart-ca-mois","odoo_line","line","invoice_date:month","Évolution mensuelle du CA HT",0,495,1130,330),
]
dash={"id":"s_dash","name":"Dashboard","colNumber":30,"rowNumber":1000,"rows":rows,"cols":cols,
 "merges":merges,"cells":cells,"styles":sheet_styles,"formats":sheet_formats,"borders":{},
 "conditionalFormats":[],"dataValidationRules":[],"figures":figs,"tables":[],
 "areGridLinesVisible":False,"isVisible":True,"headerGroups":{},"comments":{}}

doc={"version":"18.5.10","sheets":[dash],
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
ok=m.execute_kw(DB,uid,P,"spreadsheet.dashboard","write",[[DASH_ID],
    {"spreadsheet_data":data,"name":"Chiffre d'affaires par société"}])
print("dashboard",DASH_ID,"mis à jour:",ok)
