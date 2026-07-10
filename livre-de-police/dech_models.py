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

DECHETS = [("170101","Bétons"),("170102","Briques"),("170103","Tuiles et céramiques"),
           ("170107","Mélange béton/briques/tuiles/céramiques"),("170302","Mélanges bitumineux"),
           ("170504","Terres et pierres (y compris déblais)")]
CODES = [f"{t}{d}{w}" for t in ("TP","BAT","COL","PART") for d in ("86","37") for w,_ in DECHETS]

def get_model(model):
    r = kw("ir.model","search_read",[[("model","=",model)]],{"fields":["id"]})
    return r[0]["id"] if r else None

def ensure_model(model, name):
    mid = get_model(model)
    if not mid:
        mid = kw("ir.model","create",[{"name":name,"model":model,"state":"manual"}])
        print("modèle créé:", model, mid)
    else:
        print("modèle existant:", model, mid)
    return mid

def ensure_field(mid, model, name, ttype, label, extra=None):
    ex = kw("ir.model.fields","search_read",[[("model","=",model),("name","=",name)]],{"fields":["id"]})
    if ex: return ex[0]["id"]
    vals = {"model_id":mid,"name":name,"ttype":ttype,"field_description":label,"state":"manual"}
    vals.update(extra or {})
    fid = kw("ir.model.fields","create",[vals])
    print("  champ:", name, label)
    return fid

# ═══ Modèle 1 : Entrées décharge ═══
m1 = ensure_model("x_livre_police", "Entrée décharge (livre de police)")
sel_code = json.dumps([[c, c] for c in CODES])
ensure_field(m1,"x_livre_police","x_studio_date","datetime","Date 1")
ensure_field(m1,"x_livre_police","x_studio_poids1","float","Poids 1")
ensure_field(m1,"x_livre_police","x_studio_poids2","float","Poids 2")
ensure_field(m1,"x_livre_police","x_studio_net","float","Net")
ensure_field(m1,"x_livre_police","x_studio_vehicule","char","Code Véhicule")
ensure_field(m1,"x_livre_police","x_studio_transporteur","char","Nom Transporteur")
ensure_field(m1,"x_livre_police","x_studio_client","char","Nom Client")
ensure_field(m1,"x_livre_police","x_studio_produit","char","Nom Produit")
ensure_field(m1,"x_livre_police","x_studio_chantier","char","Nom Lieu")
ensure_field(m1,"x_livre_police","x_studio_code","selection","Code",{"selection":sel_code})
ensure_field(m1,"x_livre_police","x_studio_facture","char","N° facture")
ensure_field(m1,"x_livre_police","x_studio_controle","selection","Contrôle visuel",
             {"selection": json.dumps([["conforme","Conforme"],["non_conforme","Non conforme (refus)"]])})
# tonnage + code déchet européen + désignation (calculés)
ensure_field(m1,"x_livre_police","x_studio_tonnage","float","Tonnage (t)",{"compute":
"for r in self:\n    r['x_studio_tonnage'] = (r.x_studio_net or 0.0) / 1000.0\n","depends":"x_studio_net"})
ensure_field(m1,"x_livre_police","x_studio_code_dechet","char","Code déchet",{"compute":
"import re as _re\nfor r in self:\n    m = _re.match(r'(TP|BAT|COL|PART)(86|37)(\\\\d{6})', r.x_studio_code or '')\n    r['x_studio_code_dechet'] = ('%s %s %s' % (m.group(3)[0:2], m.group(3)[2:4], m.group(3)[4:6])) if m else ''\n","depends":"x_studio_code"})
DESIG = {k:v for k,v in DECHETS}
ensure_field(m1,"x_livre_police","x_studio_designation","char","Désignation déchet",{"compute":
"_d = " + repr(DESIG) + "\nfor r in self:\n    c = (r.x_studio_code or '')[-6:]\n    r['x_studio_designation'] = _d.get(c, '')\n","depends":"x_studio_code"})

# ═══ Modèle 2 : DAP ═══
m2 = ensure_model("x_dap", "DAP (acceptation préalable)")
ensure_field(m2,"x_dap","x_studio_client","char","Producteur / détenteur")
ensure_field(m2,"x_dap","x_studio_adresse","char","Adresse producteur")
ensure_field(m2,"x_dap","x_studio_chantier","char","Chantier d'origine")
ensure_field(m2,"x_dap","x_studio_code","selection","Code",{"selection":sel_code})
ensure_field(m2,"x_dap","x_studio_date","date","Date")
ensure_field(m2,"x_dap","x_studio_tonnage_estime","float","Tonnage estimé (t)")
# lien entrée -> DAP
ensure_field(m1,"x_livre_police","x_studio_dap_id","many2one","DAP",{"relation":"x_dap"})

# droits d'accès
for model,mid in [("x_livre_police",m1),("x_dap",m2)]:
    ex = kw("ir.model.access","search_read",[[("model_id","=",mid)]],{"fields":["id"]})
    if not ex:
        kw("ir.model.access","create",[{"name":"access_"+model,"model_id":mid,
            "group_id": False, "perm_read":1,"perm_write":1,"perm_create":1,"perm_unlink":1}])
        print("droits créés:", model)
print("MODELES OK")
