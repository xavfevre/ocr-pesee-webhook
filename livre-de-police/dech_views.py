# -*- coding: utf-8 -*-
import json, urllib.request, ssl, http.cookiejar
URL="https://maquignon.odoo.com"; DB="maquignon"; U="isabelle@maquignon.com"; P="Isamaq71*"
ctx=ssl.create_default_context(); cj=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=ctx))
def call(path,payload):
    r=urllib.request.Request(URL+path,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    return json.loads(op.open(r,timeout=180).read())
def kw(m,meth,args,kwargs=None):
    r=call("/web/dataset/call_kw",{"jsonrpc":"2.0","method":"call","params":{"model":m,"method":meth,"args":args,"kwargs":kwargs or {}}})
    if r.get("error"): raise Exception(str(r["error"].get("data",{}).get("message",r["error"]))[:400])
    return r["result"]
call("/web/session/authenticate",{"jsonrpc":"2.0","params":{"db":DB,"login":U,"password":P}})

# 0) libellés x_name pour import auto
for model,label in [("x_livre_police","N° de pesée"),("x_dap","N° DAP")]:
    f=kw("ir.model.fields","search_read",[[("model","=",model),("name","=","x_name")]],{"fields":["id"]})
    kw("ir.model.fields","write",[[f[0]["id"]],{"field_description":label}])
print("x_name renommés")

# 1) test computes
rid = kw("x_livre_police","create",[{"x_name":"TEST1","x_studio_net":12340,"x_studio_code":"TP86170504"}])
r = kw("x_livre_police","read",[[rid],["x_studio_tonnage","x_studio_code_dechet","x_studio_designation"]])[0]
print("computes:", r)
kw("x_livre_police","unlink",[[rid]])
assert abs(r["x_studio_tonnage"]-12.34)<0.001 and r["x_studio_code_dechet"]=="17 05 04", "computes KO"
print("computes OK")

def ensure_view(model,vtype,arch,name):
    ex=kw("ir.ui.view","search_read",[[("model","=",model),("type","=",vtype),("name","=",name)]],{"fields":["id"]})
    if ex:
        kw("ir.ui.view","write",[[ex[0]["id"]],{"arch_db":arch}]); return ex[0]["id"]
    return kw("ir.ui.view","create",[{"name":name,"model":model,"type":vtype,"arch_db":arch}])

# 2) vues x_livre_police
LIST = '''<list editable="bottom" multi_edit="1" default_order="x_studio_date desc">
  <field name="x_name" string="N° pesée"/>
  <field name="x_studio_date"/>
  <field name="x_studio_client"/>
  <field name="x_studio_chantier"/>
  <field name="x_studio_produit" optional="show"/>
  <field name="x_studio_net" sum="Total kg" optional="hide"/>
  <field name="x_studio_tonnage" sum="Total t"/>
  <field name="x_studio_code"/>
  <field name="x_studio_code_dechet"/>
  <field name="x_studio_designation" optional="hide"/>
  <field name="x_studio_transporteur" optional="show"/>
  <field name="x_studio_vehicule" optional="show"/>
  <field name="x_studio_dap_id"/>
  <field name="x_studio_facture" optional="show"/>
  <field name="x_studio_controle" optional="show"/>
</list>'''
FORM = '''<form>
  <sheet>
    <group>
      <group string="Pesée">
        <field name="x_name" string="N° pesée"/>
        <field name="x_studio_date"/>
        <field name="x_studio_poids1"/>
        <field name="x_studio_poids2"/>
        <field name="x_studio_net"/>
        <field name="x_studio_tonnage"/>
      </group>
      <group string="Provenance">
        <field name="x_studio_client"/>
        <field name="x_studio_chantier"/>
        <field name="x_studio_transporteur"/>
        <field name="x_studio_vehicule"/>
        <field name="x_studio_produit"/>
      </group>
      <group string="Codification (livre de police)">
        <field name="x_studio_code"/>
        <field name="x_studio_code_dechet"/>
        <field name="x_studio_designation"/>
        <field name="x_studio_controle"/>
      </group>
      <group string="Références">
        <field name="x_studio_dap_id"/>
        <field name="x_studio_facture"/>
      </group>
    </group>
  </sheet>
</form>'''
SEARCH = '''<search>
  <field name="x_name"/>
  <field name="x_studio_client"/>
  <field name="x_studio_chantier"/>
  <field name="x_studio_code"/>
  <filter name="sans_dap" string="Sans DAP" domain="[('x_studio_dap_id','=',False)]"/>
  <filter name="sans_code" string="Sans code" domain="[('x_studio_code','=',False)]"/>
  <separator/>
  <filter name="mois" string="Date" date="x_studio_date"/>
  <separator/>
  <filter name="g_client" string="Par client" context="{'group_by':'x_studio_client'}"/>
  <filter name="g_code" string="Par code" context="{'group_by':'x_studio_code'}"/>
  <filter name="g_dap" string="Par DAP" context="{'group_by':'x_studio_dap_id'}"/>
</search>'''
v1=ensure_view("x_livre_police","list",LIST,"x_livre_police list")
v2=ensure_view("x_livre_police","form",FORM,"x_livre_police form")
v3=ensure_view("x_livre_police","search",SEARCH,"x_livre_police search")
print("vues livre:", v1,v2,v3)

# 3) vues x_dap
LIST2='''<list default_order="x_name desc">
  <field name="x_name" string="N° DAP"/>
  <field name="x_studio_date"/>
  <field name="x_studio_client"/>
  <field name="x_studio_chantier"/>
  <field name="x_studio_code"/>
  <field name="x_studio_tonnage_estime"/>
</list>'''
FORM2='''<form>
  <sheet>
    <group>
      <group string="DAP">
        <field name="x_name" string="N° DAP"/>
        <field name="x_studio_date"/>
        <field name="x_studio_code"/>
        <field name="x_studio_tonnage_estime"/>
      </group>
      <group string="Producteur">
        <field name="x_studio_client"/>
        <field name="x_studio_adresse"/>
        <field name="x_studio_chantier"/>
      </group>
    </group>
  </sheet>
</form>'''
v4=ensure_view("x_dap","list",LIST2,"x_dap list")
v5=ensure_view("x_dap","form",FORM2,"x_dap form")
print("vues dap:", v4,v5)

# 4) actions + menus
def ensure_act(name, model):
    ex=kw("ir.actions.act_window","search_read",[[("name","=",name),("res_model","=",model)]],{"fields":["id"]})
    if ex: return ex[0]["id"]
    return kw("ir.actions.act_window","create",[{"name":name,"res_model":model,"view_mode":"list,form"}])
a1=ensure_act("Entrées décharge","x_livre_police")
a2=ensure_act("DAP","x_dap")
def ensure_menu(name,parent,seq,act=None):
    dom=[("name","=",name)] + ([("parent_id","=",parent)] if parent else [("parent_id","=",False)])
    ex=kw("ir.ui.menu","search_read",[dom],{"fields":["id"]})
    vals={"name":name,"sequence":seq}
    if parent: vals["parent_id"]=parent
    if act: vals["action"]="ir.actions.act_window,%d"%act
    if ex:
        kw("ir.ui.menu","write",[[ex[0]["id"]],vals]); return ex[0]["id"]
    return kw("ir.ui.menu","create",[vals])
root=ensure_menu("Décharge Haims",False,55)
me1=ensure_menu("Entrées décharge",root,1,a1)
me2=ensure_menu("DAP",root,2,a2)
print("menus:",root,me1,me2)
