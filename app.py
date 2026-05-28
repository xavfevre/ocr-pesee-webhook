# -*- coding: utf-8 -*-
"""
Backend proxy pour l'appli chauffeur (Odoo Online / SaaS).
- 1 seul utilisateur API de service (clé API Odoo).
- Auth chauffeur par PIN (champ hr.employee.pin, le même que le kiosque Shop Floor).
- Le backend détient la clé, scope CHAQUE requête au chauffeur connecté.

Déploiement Render :
  - Build command : pip install -r requirements.txt
  - Start command : gunicorn app:app
  - Variables d'env : voir la section Config ci-dessous.
"""
import os, functools
import xmlrpc.client
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# ============================================================
# CONFIG (variables d'environnement sur Render)
# ============================================================
ODOO_URL  = os.environ.get("ODOO_URL",  "https://maquignon.odoo.com")
ODOO_DB   = os.environ.get("ODOO_DB",   "maquignon")
ODOO_USER = os.environ["ODOO_USER"]          # login du user de service
ODOO_KEY  = os.environ["ODOO_API_KEY"]       # Clé API : Préférences > Sécurité du compte
APP_SECRET = os.environ.get("APP_SECRET", "CHANGE-ME-secret-long-aleatoire")
TOKEN_TTL  = 60 * 60 * 12                     # 12h de session

# ---- Points à adapter à ton instance ----
WORKSHEET_MODEL = "x_project_task_worksheet_template_1"  # modèle feuille de travail
WS_TASK_FIELD   = "x_project_task_id"                    # m2o feuille -> tâche
DRIVER_FIELD    = "user_ids"   # <<< comment une tâche est reliée au chauffeur.
                               #     "user_ids" (assignés, m2m) par défaut.
                               #     Si champ dédié type "x_studio_chauffeur" (m2o res.users) -> mets son nom.
DONE_STAGE_NAME = "TRANSPORT REALISE"  # nom d'étape au "Terminer" (optionnel)

# ============================================================
app = Flask(__name__)
CORS(app)  # PROD : restreindre origins=["https://ton-app.netlify.app"]
signer = URLSafeTimedSerializer(APP_SECRET)

# ---------- XML-RPC ----------
_common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
_models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
_uid = None

def uid():
    global _uid
    if _uid is None:
        _uid = _common.authenticate(ODOO_DB, ODOO_USER, ODOO_KEY, {})
        if not _uid:
            raise RuntimeError("Authentification Odoo échouée (login/clé API).")
    return _uid

def odoo(model, method, *args, **kw):
    return _models.execute_kw(ODOO_DB, uid(), ODOO_KEY, model, method, list(args), kw)

# ---------- Auth chauffeur (PIN) ----------
def driver_by_pin(pin):
    emps = odoo("hr.employee", "search_read",
                [["pin", "=", str(pin)]],
                fields=["id", "name", "user_id"], limit=1)
    if not emps:
        return None
    e = emps[0]
    return {"employee_id": e["id"],
            "name": e["name"],
            "user_id": e["user_id"][0] if e["user_id"] else None}

def make_token(driver):
    return signer.dumps(driver)

def read_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        abort(401)
    try:
        return signer.loads(auth[7:], max_age=TOKEN_TTL)
    except (BadSignature, SignatureExpired):
        abort(401)

def require_driver(fn):
    @functools.wraps(fn)
    def wrapper(*a, **k):
        return fn(read_token(), *a, **k)
    return wrapper

# ---------- Helpers métier ----------
def driver_domain(driver):
    if DRIVER_FIELD == "user_ids":
        return [["user_ids", "in", [driver["user_id"]]]]
    return [[DRIVER_FIELD, "=", driver["user_id"]]]

def owns_task(driver, tid):
    return bool(odoo("project.task", "search", driver_domain(driver) + [["id", "=", tid]]))

def get_worksheet(task_id, create=False):
    ws = odoo(WORKSHEET_MODEL, "search_read", [[WS_TASK_FIELD, "=", task_id]], limit=1)
    if ws:
        return ws[0]
    if create:
        wid = odoo(WORKSHEET_MODEL, "create", {WS_TASK_FIELD: task_id})
        return odoo(WORKSHEET_MODEL, "read", [wid])[0]
    return None

def worksheet_schema():
    """Génère dynamiquement la liste des champs x_studio_* de la feuille de travail."""
    fg = odoo(WORKSHEET_MODEL, "fields_get", [],
              attributes=["string", "type", "selection", "readonly"])
    out = []
    for name, meta in fg.items():
        if not name.startswith("x_studio_"):
            continue
        out.append({"name": name,
                    "label": meta.get("string", name),
                    "type": meta.get("type"),
                    "selection": meta.get("selection"),
                    "readonly": meta.get("readonly", False)})
    out.sort(key=lambda f: f["label"])
    return out

# ============================================================
# API
# ============================================================
@app.get("/health")
def health():
    return jsonify(ok=True, uid=bool(uid()))

@app.post("/api/login")
def login():
    pin = (request.get_json(silent=True) or {}).get("pin")
    d = driver_by_pin(pin) if pin else None
    if not d or not d["user_id"]:
        return jsonify(error="PIN invalide ou employé sans utilisateur lié."), 401
    return jsonify(token=make_token(d), name=d["name"])

@app.get("/api/tasks")
@require_driver
def list_tasks(driver):
    recs = odoo("project.task", "search_read",
                driver_domain(driver),
                fields=["id", "name", "date_deadline", "planned_date_begin",
                        "partner_id", "stage_id"],
                order="planned_date_begin asc, date_deadline asc",
                limit=100)
    return jsonify(recs)

@app.get("/api/tasks/<int:tid>")
@require_driver
def task_detail(driver, tid):
    if not owns_task(driver, tid):
        abort(403)
    # En-tête : on lit un set sûr (ajoute ici tes champs adresse x_studio_* une fois confirmés)
    task = odoo("project.task", "read", [tid],
                fields=["name", "partner_id", "date_deadline",
                        "planned_date_begin", "stage_id"])[0]
    ws = get_worksheet(tid, create=False)
    return jsonify(task=task,
                   schema=worksheet_schema(),
                   worksheet=ws,
                   worksheet_model=WORKSHEET_MODEL)

@app.post("/api/tasks/<int:tid>/worksheet")
@require_driver
def save_worksheet(driver, tid):
    if not owns_task(driver, tid):
        abort(403)
    vals = request.get_json(silent=True) or {}
    vals = {k: v for k, v in vals.items() if k.startswith("x_studio_")}
    if not vals:
        return jsonify(error="Aucun champ x_studio_ à enregistrer."), 400
    ws = get_worksheet(tid, create=True)
    odoo(WORKSHEET_MODEL, "write", [ws["id"]], vals)
    return jsonify(ok=True, worksheet_id=ws["id"])

@app.post("/api/tasks/<int:tid>/photo")
@require_driver
def save_photo(driver, tid):
    """Upload binaire base64. body: {field, data, target?}  target='task' pour écrire sur la tâche."""
    if not owns_task(driver, tid):
        abort(403)
    body = request.get_json(silent=True) or {}
    field, data = body.get("field"), body.get("data")
    if not field or not data:
        return jsonify(error="'field' et 'data' (base64) requis."), 400
    if body.get("target") == "task":
        odoo("project.task", "write", [tid], {field: data})
    else:
        ws = get_worksheet(tid, create=True)
        odoo(WORKSHEET_MODEL, "write", [ws["id"]], {field: data})
    return jsonify(ok=True)

@app.post("/api/tasks/<int:tid>/done")
@require_driver
def mark_done(driver, tid):
    if not owns_task(driver, tid):
        abort(403)
    stage = (request.get_json(silent=True) or {}).get("stage", DONE_STAGE_NAME)
    if stage:
        st = odoo("project.task.type", "search", [["name", "=", stage]], limit=1)
        if st:
            odoo("project.task", "write", [tid], {"stage_id": st[0]})
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
