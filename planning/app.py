"""
Planning interventions PROTEC — Vue web journalière
Connexion Odoo via XML-RPC, affichage des planning.slot du jour.
"""

import os
import xmlrpc.client
import socket
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request

app = Flask(__name__)
socket.setdefaulttimeout(15)

ODOO_URL      = os.environ.get("ODOO_URL",      "https://protec-s3t.odoo.com")
ODOO_DB       = os.environ.get("ODOO_DB",       "protec-s3t")
ODOO_USER     = os.environ.get("ODOO_USER",     "s3t@orange.fr")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "")

TZ = ZoneInfo("Europe/Paris")

def odoo_connect():
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models

def x(models, uid, model, method, *params, **kw):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, list(params), kw)

def utc_str_to_local(dt_str):
    if not dt_str:
        return None
    dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("UTC"))
    return dt_utc.astimezone(TZ)

def get_slots_for_date(target_date: date):
    uid, models = odoo_connect()

    start_local = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=TZ)
    end_local   = start_local + timedelta(days=1)
    start_utc   = start_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
    end_utc     = end_local.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")

    slots = x(models, uid, "planning.slot", "search_read",
        [["start_datetime", ">=", start_utc],
         ["start_datetime", "<",  end_utc]],
        fields=[
            "name", "start_datetime", "end_datetime",
            "partner_id", "partner_street", "partner_zip", "partner_city",
            "partner_phone", "employee_ids", "role_id",
        ],
        order="start_datetime asc",
        limit=200,
    )

    all_emp_ids = list({eid for s in slots for eid in s.get("employee_ids", [])})
    emp_map = {}
    if all_emp_ids:
        emps = x(models, uid, "hr.employee", "read", all_emp_ids, fields=["id", "name"])
        emp_map = {e["id"]: e["name"] for e in emps}

    result = []
    for s in slots:
        sl = utc_str_to_local(s["start_datetime"])
        el = utc_str_to_local(s["end_datetime"])
        result.append({
            "id":          s["id"],
            "ref":         s["name"] or "",
            "start_str":   sl.strftime("%H:%M") if sl else "—",
            "end_str":     el.strftime("%H:%M") if el else "—",
            "client":      s["partner_id"][1]    if s["partner_id"]    else "—",
            "adresse":     " ".join(filter(None, [
                               s.get("partner_street", ""),
                               s.get("partner_zip", ""),
                               s.get("partner_city", ""),
                           ])) or "",
            "telephone":   s.get("partner_phone") or "",
            "techniciens": [emp_map.get(eid, f"#{eid}") for eid in s.get("employee_ids", [])],
            "role":        s["role_id"][1] if s.get("role_id") else "",
        })
    return result


@app.route("/")
def index():
    date_str = request.args.get("date")
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        target = date.today()

    error = None
    slots = []
    try:
        slots = get_slots_for_date(target)
    except Exception as e:
        error = str(e)

    prev_date = (target - timedelta(days=1)).isoformat()
    next_date = (target + timedelta(days=1)).isoformat()
    today     = date.today().isoformat()

    JOURS = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    MOIS  = ["janvier","février","mars","avril","mai","juin",
             "juillet","août","septembre","octobre","novembre","décembre"]
    date_label = f"{JOURS[target.weekday()]} {target.day} {MOIS[target.month-1]} {target.year}"

    return render_template("index.html",
        slots=slots,
        date_label=date_label,
        target=target.isoformat(),
        prev_date=prev_date,
        next_date=next_date,
        today=today,
        error=error,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
