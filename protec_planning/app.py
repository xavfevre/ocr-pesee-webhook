"""
Planning chauffeur PROTEC + app mobile « Ma tournée » + Fiche de fin de travaux
Monté comme Blueprint sous /protec dans l'app principale (même service Render
que le webhook Maquignon) — ou exécutable seul pour les tests.

- /protec/                 : planning semaine (grille jours x chauffeurs)
- /protec/mois             : planning mois (bandeaux par semaine)
- /protec/ma-tournee       : page mobile chauffeur (lien signé HMAC)
- /protec/fiche/<slot_id>  : fiche de fin de travaux (formulaire mobile)
- /protec/liens            : page admin des liens chauffeurs

Données : Odoo v19 SaaS PROTEC via XML-RPC (planning.slot).
Env vars : PROTEC_ODOO_USER, PROTEC_ODOO_PASSWORD, PROTEC_PLANNING_SECRET
"""
import os, json, time, hmac, hashlib, socket
import urllib.request, http.cookiejar
import xmlrpc.client
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from flask import Blueprint, Flask, render_template, request, redirect, url_for, abort, Response

bp = Blueprint("protec", __name__, template_folder="templates")
socket.setdefaulttimeout(25)

ODOO_URL      = os.environ.get("PROTEC_ODOO_URL",      "https://protec-s3t.odoo.com")
ODOO_DB       = os.environ.get("PROTEC_ODOO_DB",       "protec-s3t")
ODOO_USER     = os.environ.get("PROTEC_ODOO_USER",     "")
ODOO_PASSWORD = os.environ.get("PROTEC_ODOO_PASSWORD", "")
SECRET        = os.environ.get("PROTEC_PLANNING_SECRET", "")

TZ  = ZoneInfo("Europe/Paris")
UTC = ZoneInfo("UTC")

# Employés à exclure (comptes techniques)
EXCLUDED_EMPLOYEE_IDS = {1, 3, 8, 9}  # compte technique + Manon + Natacha (hors terrain)

# Palette couleurs vives par chauffeur (stable sur l'id employé)
PALETTE = ["#2563eb", "#16a34a", "#ea580c", "#9333ea", "#0d9488",
           "#db2777", "#ca8a04", "#4f46e5", "#dc2626", "#0891b2"]
# Couleurs et ordre fixes, identiques aux pages planning du site
CMAP = {4: "#2563eb", 5: "#eab308", 6: "#dc2626", 7: "#111827",
        10: "#7c3aed", 2: "#7c3aed", 8: "#0d9488", 1: "#db2777", 9: "#ea580c"}
OMAP = {4: 1, 5: 2, 6: 3, 7: 4, 10: 5, 2: 6, 8: 7, 9: 8, 1: 9}

# ─── Fiche de fin de travaux : natures de travaux par onglet ────────────────
# (les codes existants sont conservés → compatibilité des fiches déjà remplies)
TRAVAUX_TABS = [
    ("deb", "Débouchage", [
        ("deb_brancht_eu", "Débouchage branchement EU", "U"),
        ("deb_brancht_ep", "Débouchage branchement EP", "U"),
        ("deb_reseau_eu",  "Débouchage réseau EU",      "U"),
        ("deb_reseau_ep",  "Débouchage réseau EP",      "U"),
    ]),
    ("curage", "Curage", [
        ("curage_eu", "Curage réseau EU", "ML"),
        ("curage_ep", "Curage réseau EP", "ML"),
    ]),
    ("poste", "Poste de relevage", [
        ("poste_relevage", "Poste de relevage", "U"),
    ]),
    ("bac", "Bac à graisse", [
        ("bac_graisse", "Bac à graisse", "U"),
    ]),
    ("step", "Station d'épuration", [
        ("step", "Station d'épuration", "U"),
    ]),
    ("fosse", "Fosse", [
        ("fosse_septique",    "Fosse septique",    "U"),
        ("fosse_toutes_eaux", "Fosse toutes eaux", "U"),
    ]),
    ("autre", "Autre", [
        ("autre", "Autre (préciser dans commentaires)", "H"),
    ]),
]
# Liste à plat (POST + chatter) — compatibilité avec le code existant
TRAVAUX = [row for _k, _lbl, rows in TRAVAUX_TABS for row in rows]
DECHETS = [
    ("sable",   "Sable"),
    ("graisse", "Graisse"),
    ("refus",   "Refus dégrillage"),
    ("vidange", "Matières de vidanges"),
    ("autre",   "Autre"),
]

@bp.app_context_processor
def inject_base():
    # "/protec" quand monté sous prefix, "" en exécution seule
    return {"BASE": url_for("protec.week_view").rstrip("/")}

# ─── Helpers Odoo ─────────────────────────────────────────────────────────────
_uid_cache = {"uid": None}

def odoo_connect():
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    if _uid_cache["uid"]:
        return _uid_cache["uid"], models
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ValueError("Authentification Odoo échouée")
    _uid_cache["uid"] = uid
    return uid, models

def x(models, uid, model, method, *params, **kw):
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, list(params), kw)

def utc_to_local(dt_str):
    if not dt_str:
        return None
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return dt.astimezone(TZ)

def local_range_to_utc(d_start: date, d_end: date):
    """[d_start 00:00, d_end 00:00) heure de Paris → chaînes UTC Odoo."""
    s = datetime(d_start.year, d_start.month, d_start.day, tzinfo=TZ).astimezone(UTC)
    e = datetime(d_end.year, d_end.month, d_end.day, tzinfo=TZ).astimezone(UTC)
    return s.strftime("%Y-%m-%d %H:%M:%S"), e.strftime("%Y-%m-%d %H:%M:%S")

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())

def emp_color(emp_id: int) -> str:
    if not emp_id:
        return "#64748b"
    return CMAP.get(emp_id, PALETTE[emp_id % len(PALETTE)])

MOIS_FR  = ["janvier","février","mars","avril","mai","juin","juillet","août",
            "septembre","octobre","novembre","décembre"]
MOIS_ABR = ["jan","fév","mar","avr","mai","juin","juil","août","sep","oct","nov","déc"]
JOURS_FR = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
JOURS_LONG = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]

# ─── Sécurité HMAC ────────────────────────────────────────────────────────────
def _sign(payload: str) -> str:
    return hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:20]

def driver_sig(emp_id: int) -> str:
    return _sign(f"driver:{emp_id}")

def fiche_token(slot_id: int) -> str:
    return _sign(f"fdt:{slot_id}")

def check_sig(payload: str, sig: str) -> bool:
    return bool(SECRET) and hmac.compare_digest(_sign(payload), sig or "")

# ─── Données ──────────────────────────────────────────────────────────────────
SLOT_FIELDS = ["name", "start_datetime", "end_datetime",
               "partner_id", "partner_city", "partner_zip", "partner_street",
               "partner_phone", "employee_ids", "role_id", "x_fdt_fait"]

_emp_cache = {"t": 0.0, "data": None}

def get_all_employees(uid, models):
    now = time.time()
    if _emp_cache["data"] is not None and now - _emp_cache["t"] < 600:
        return _emp_cache["data"]
    emps = x(models, uid, "hr.employee", "search_read",
        [["active", "=", True]],
        fields=["id", "name"], order="name asc", limit=100)
    data = sorted([e for e in emps if e["id"] not in EXCLUDED_EMPLOYEE_IDS],
                  key=lambda e: (OMAP.get(e["id"], 99), e["name"]))
    _emp_cache["t"], _emp_cache["data"] = now, data
    return data

def emp_name_map(uid, models):
    return {e["id"]: e["name"] for e in get_all_employees(uid, models)}

def fetch_slots(uid, models, d_start: date, d_end: date, emp_id=None):
    s_utc, e_utc = local_range_to_utc(d_start, d_end)
    domain = [["start_datetime", ">=", s_utc], ["start_datetime", "<", e_utc]]
    if emp_id:
        domain.append(["employee_ids", "in", [emp_id]])
    return x(models, uid, "planning.slot", "search_read", domain,
             fields=SLOT_FIELDS, order="start_datetime asc", limit=2000)

def slot_to_card(s):
    sl = utc_to_local(s["start_datetime"])
    el = utc_to_local(s["end_datetime"])
    return {
        "id":     s["id"],
        "ref":    (s["name"] or "").strip(),
        "day":    sl.date().isoformat(),
        "start":  sl.strftime("%H:%M"),
        "end":    el.strftime("%H:%M") if el else "",
        "client": s["partner_id"][1] if s["partner_id"] else "—",
        "street": s.get("partner_street") or "",
        "zip":    s.get("partner_zip") or "",
        "ville":  s.get("partner_city") or "",
        "tel":    (s.get("partner_phone") or "").strip(),
        "role":   s["role_id"][1] if s.get("role_id") else "",
        "fdt":    bool(s.get("x_fdt_fait")),
        "emp_ids": [e for e in s.get("employee_ids", []) if e not in EXCLUDED_EMPLOYEE_IDS],
        "token":  fiche_token(s["id"]),
    }

def build_matrix(slots, columns):
    """matrix[(day_iso, emp_id)] = [cards] ; emp 0 = non assigné."""
    matrix, counts = {}, {}
    col_ids = {c["id"] for c in columns}
    for s in slots:
        card = slot_to_card(s)
        targets = [e for e in card["emp_ids"] if e in col_ids] or [0]
        for eid in targets:
            if eid not in col_ids:
                continue
            matrix.setdefault((card["day"], eid), []).append(card)
            counts[eid] = counts.get(eid, 0) + 1
    for c in columns:
        c["total"] = counts.get(c["id"], 0)
    return matrix

def make_columns(all_emps, emp_filter=None, with_unassigned=True):
    cols = [{"id": e["id"], "name": e["name"], "color": emp_color(e["id"])}
            for e in all_emps if not emp_filter or e["id"] == emp_filter]
    if with_unassigned and not emp_filter:
        cols.append({"id": 0, "name": "Non assigné", "color": "#ef4444"})
    return cols

def week_label(ws: date) -> str:
    we = ws + timedelta(days=5)
    num = ws.isocalendar()[1]
    if ws.month == we.month:
        return f"S{num} — {ws.day} au {we.day} {MOIS_ABR[we.month-1]} {we.year}"
    return f"S{num} — {ws.day} {MOIS_ABR[ws.month-1]} au {we.day} {MOIS_ABR[we.month-1]} {we.year}"

def common_nav(emp_filter, all_emps):
    return {
        "emp_filter": emp_filter or 0,
        "drivers": [{"id": e["id"], "name": e["name"], "color": emp_color(e["id"])} for e in all_emps],
    }

# ─── VUE SEMAINE ──────────────────────────────────────────────────────────────
@bp.route("/")
def week_view():
    week_str = request.args.get("week")
    emp_filter = request.args.get("c", type=int)
    try:
        ws = datetime.strptime(week_str, "%Y-%m-%d").date() if week_str else date.today()
    except ValueError:
        ws = date.today()
    week_start = monday_of(ws)
    days = [week_start + timedelta(days=i) for i in range(6)]  # Lun → Sam

    error, columns, matrix = None, [], {}
    all_emps = []
    try:
        uid, models = odoo_connect()
        all_emps = get_all_employees(uid, models)
        columns = make_columns(all_emps, emp_filter)
        slots = fetch_slots(uid, models, week_start, week_start + timedelta(days=7), emp_filter)
        matrix = build_matrix(slots, columns)
    except Exception as e:
        error = str(e)

    day_labels = [{"iso": d.isoformat(),
                   "dow": JOURS_FR[d.weekday()], "num": f"{d.day}/{d.month}",
                   "is_today": d == date.today()} for d in days]

    qs_c = f"&c={emp_filter}" if emp_filter else ""
    return render_template("week.html",
        days=day_labels, columns=columns, matrix=matrix,
        cur_week=week_start.isoformat(),
        week_label=week_label(week_start),
        prev_week=(week_start - timedelta(days=7)).isoformat(),
        next_week=(week_start + timedelta(days=7)).isoformat(),
        this_week=monday_of(date.today()).isoformat(),
        is_current=(week_start == monday_of(date.today())),
        month_str=f"{week_start.year}-{week_start.month:02d}",
        qs_c=qs_c, error=error,
        total_slots=sum(len(v) for v in matrix.values()),
        **common_nav(emp_filter, all_emps))

# ─── VUE MOIS (bandeaux par semaine) ─────────────────────────────────────────
@bp.route("/mois")
def month_view():
    m_str = request.args.get("m")
    emp_filter = request.args.get("c", type=int)
    today = date.today()
    try:
        y, m = (int(v) for v in m_str.split("-")) if m_str else (today.year, today.month)
    except (ValueError, AttributeError):
        y, m = today.year, today.month
    first = date(y, m, 1)
    last = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)

    # Semaines couvrant le mois
    weeks = []
    wcur = monday_of(first)
    while wcur <= last:
        weeks.append(wcur)
        wcur += timedelta(days=7)

    error, columns, matrix = None, [], {}
    all_emps = []
    try:
        uid, models = odoo_connect()
        all_emps = get_all_employees(uid, models)
        columns = make_columns(all_emps, emp_filter)
        slots = fetch_slots(uid, models, weeks[0], weeks[-1] + timedelta(days=7), emp_filter)
        matrix = build_matrix(slots, columns)
    except Exception as e:
        error = str(e)

    week_blocks = []
    for wstart in weeks:
        days = []
        for i in range(6):  # Lun → Sam
            d = wstart + timedelta(days=i)
            days.append({"iso": d.isoformat(), "dow": JOURS_FR[d.weekday()],
                         "num": f"{d.day}/{d.month}",
                         "in_month": d.month == m, "is_today": d == today})
        total = sum(len(matrix.get((dd["iso"], c["id"]), [])) for dd in days for c in columns)
        week_blocks.append({"label": week_label(wstart), "days": days, "total": total,
                            "week_iso": wstart.isoformat()})

    prev_m = date(y - 1, 12, 1) if m == 1 else date(y, m - 1, 1)
    next_m = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    qs_c = f"&c={emp_filter}" if emp_filter else ""

    return render_template("mois.html",
        weeks=week_blocks, columns=columns, matrix=matrix,
        month_label=f"{MOIS_FR[m-1].capitalize()} {y}",
        month_str=f"{y}-{m:02d}",
        prev_month=f"{prev_m.year}-{prev_m.month:02d}",
        next_month=f"{next_m.year}-{next_m.month:02d}",
        this_month=f"{today.year}-{today.month:02d}",
        is_current=(y == today.year and m == today.month),
        this_week=monday_of(today).isoformat(),
        qs_c=qs_c, error=error,
        total_slots=sum(len(v) for v in matrix.values()),
        **common_nav(emp_filter, all_emps))

# ─── MA TOURNÉE (mobile chauffeur) ───────────────────────────────────────────
@bp.route("/ma-tournee")
def ma_tournee():
    emp_id = request.args.get("c", type=int)
    sig = request.args.get("s", "")
    if not emp_id or not check_sig(f"driver:{emp_id}", sig):
        abort(403)

    error, emp_name, dayblocks = None, "", []
    try:
        uid, models = odoo_connect()
        emp_name = emp_name_map(uid, models).get(emp_id) or f"Chauffeur {emp_id}"

        today = date.today()
        slots = fetch_slots(uid, models, today - timedelta(days=1), today + timedelta(days=15), emp_id)
        by_day = {}
        cards = []
        for s in slots:
            card = slot_to_card(s)
            by_day.setdefault(card["day"], []).append(card)
            cards.append(card)

        # Lieu d'intervention / interlocuteur / objet depuis la commande liée
        refs = list({c["ref"].split()[0] for c in cards if c["ref"]})
        somap = {}
        if refs:
            sos = x(models, uid, "sale.order", "search_read",
                [["name", "in", refs]],
                fields=["name", "x_studio_lieu_dintervention_2",
                        "x_studio_interlocuteur_1", "x_studio_lieu_dintervention_1"])
            somap = {o["name"]: o for o in sos}
        for c in cards:
            so = somap.get(c["ref"].split()[0]) if c["ref"] else None
            c["lieu"] = (so or {}).get("x_studio_lieu_dintervention_2") or ""
            c["inter"] = (so or {}).get("x_studio_interlocuteur_1") or ""
            c["objet"] = (so or {}).get("x_studio_lieu_dintervention_1") or ""

        # Toujours afficher aujourd'hui même vide
        all_days = sorted(set(by_day.keys()) | {today.isoformat()})
        for iso in all_days:
            d = date.fromisoformat(iso)
            dayblocks.append({
                "iso": iso,
                "label": f"{JOURS_LONG[d.weekday()]} {d.day} {MOIS_ABR[d.month-1]}",
                "is_today": d == today,
                "cards": by_day.get(iso, []),
            })
    except Exception as e:
        error = str(e)

    return render_template("tournee.html",
        emp_name=emp_name, emp_id=emp_id, sig=sig,
        dayblocks=dayblocks, today_iso=date.today().isoformat(), error=error)

# ─── FICHE DE FIN DE TRAVAUX ─────────────────────────────────────────────────
FDT_FIELDS = ["x_fdt_fait", "x_fdt_date", "x_fdt_vehicule", "x_fdt_heure_arrivee",
              "x_fdt_heure_depart", "x_fdt_temps_trajet", "x_fdt_operateurs",
              "x_fdt_commentaires", "x_fdt_data", "x_fdt_signataire"]

@bp.route("/fiche/<int:slot_id>", methods=["GET", "POST"])
def fiche(slot_id):
    token = request.args.get("t", "")
    if not check_sig(f"fdt:{slot_id}", token):
        abort(403)

    uid, models = odoo_connect()
    recs = x(models, uid, "planning.slot", "read", [slot_id],
             fields=SLOT_FIELDS + FDT_FIELDS + ["partner_street2"])
    if not recs:
        abort(404)
    s = recs[0]
    card = slot_to_card(s)

    emp_names = ""
    if card["emp_ids"]:
        nmap = emp_name_map(uid, models)
        emp_names = ", ".join(nmap.get(i, "") for i in card["emp_ids"] if nmap.get(i))

    if request.method == "POST":
        f = request.form
        data = {"travaux": {}, "dechets": {}}
        for code, _label, _unit in TRAVAUX:
            qte = f.get(f"trav_{code}_qte", "").strip()
            temps = f.get(f"trav_{code}_temps", "").strip()
            if qte or temps:
                data["travaux"][code] = {"qte": qte, "temps": temps}
        for code, _label in DECHETS:
            row = {
                "badge_protec": bool(f.get(f"dech_{code}_bp")),
                "badge_cclst":  bool(f.get(f"dech_{code}_bc")),
                "volume":       f.get(f"dech_{code}_vol", "").strip(),
                "destination":  f.get(f"dech_{code}_dest", "").strip(),
                "temps":        f.get(f"dech_{code}_temps", "").strip(),
            }
            if any(row.values()):
                data["dechets"][code] = row

        def bin_val(field_val):
            if field_val and field_val.startswith("data:"):
                return field_val.split(",", 1)[1]
            return None

        vals = {
            "x_fdt_fait": True,
            "x_fdt_date": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "x_fdt_vehicule":      f.get("vehicule", "").strip(),
            "x_fdt_heure_arrivee": f.get("heure_arrivee", "").strip(),
            "x_fdt_heure_depart":  f.get("heure_depart", "").strip(),
            "x_fdt_temps_trajet":  f.get("temps_trajet", "").strip(),
            "x_fdt_operateurs":    f.get("operateurs", "").strip(),
            "x_fdt_commentaires":  f.get("commentaires", "").strip(),
            "x_fdt_data":          json.dumps(data, ensure_ascii=False),
            "x_fdt_signataire":    f.get("signataire", "").strip(),
        }
        sig = bin_val(f.get("signature", ""))
        if sig:
            vals["x_fdt_signature"] = sig
        nphotos = 0
        for i in (1, 2, 3, 4):
            pv = f.get(f"photo_{i}", "")
            b = bin_val(pv)
            if b:
                vals[f"x_fdt_photo_{i}"] = b
                nphotos += 1
            elif pv == "KEEP":
                nphotos += 1
        x(models, uid, "planning.slot", "write", [slot_id], vals)

        # Message chatter pour le bureau (mail.message direct : message_post
        # échappe le HTML passé par XML-RPC en v19)
        try:
            html = render_fiche_html(card, vals, data, nphotos)
            subtype = x(models, uid, "ir.model.data", "check_object_reference", "mail", "mt_note")
            x(models, uid, "mail.message", "create", [{
                "model": "planning.slot", "res_id": slot_id,
                "message_type": "comment", "subtype_id": subtype[1],
                "body": html,
            }])
        except Exception:
            pass

        back = request.args.get("back", "")
        return redirect(url_for(".fiche", slot_id=slot_id, t=token, back=back, ok=1))

    # GET : présence signature/photos sans télécharger les binaires
    bins = x(models, uid, "planning.slot", "read", [slot_id],
             fields=["x_fdt_signature", "x_fdt_photo_1", "x_fdt_photo_2",
                     "x_fdt_photo_3", "x_fdt_photo_4"],
             context={"bin_size": True})[0]
    has = {
        "sig": bool(bins.get("x_fdt_signature")),
        "p1": bool(bins.get("x_fdt_photo_1")),
        "p2": bool(bins.get("x_fdt_photo_2")),
        "p3": bool(bins.get("x_fdt_photo_3")),
        "p4": bool(bins.get("x_fdt_photo_4")),
    }

    # GET : préremplissage
    saved_data = {}
    if s.get("x_fdt_data"):
        try:
            saved_data = json.loads(s["x_fdt_data"])
        except (ValueError, TypeError):
            saved_data = {}

    # Nb de lignes remplies par onglet (badge)
    _sv_trav = saved_data.get("travaux", {}) if isinstance(saved_data, dict) else {}
    tab_counts = {tkey: sum(1 for code, _l, _u in rows if code in _sv_trav)
                  for tkey, _tl, rows in TRAVAUX_TABS}

    prefill = {
        "vehicule":      s.get("x_fdt_vehicule") or "",
        "heure_arrivee": s.get("x_fdt_heure_arrivee") or card["start"],
        "heure_depart":  s.get("x_fdt_heure_depart") or card["end"],
        "temps_trajet":  s.get("x_fdt_temps_trajet") or "",
        "operateurs":    s.get("x_fdt_operateurs") or emp_names,
        "commentaires":  s.get("x_fdt_commentaires") or "",
    }
    d = date.fromisoformat(card["day"])
    adresse = ", ".join(p for p in [card["street"], f"{card['zip']} {card['ville']}".strip()] if p)
    ref0 = card["ref"].split()[0] if card["ref"] else ""
    if ref0:
        so_l = x(models, uid, "sale.order", "search_read",
                 [["name", "=", ref0]], fields=["x_studio_lieu_dintervention_2"], limit=1)
        if so_l and so_l[0].get("x_studio_lieu_dintervention_2"):
            adresse = so_l[0]["x_studio_lieu_dintervention_2"]

    return render_template("fiche.html",
        card=card, slot_id=slot_id, token=token,
        date_label=f"{d.day:02d}/{d.month:02d}/{d.year}",
        adresse=adresse, prefill=prefill,
        travaux=TRAVAUX, travaux_tabs=TRAVAUX_TABS, tab_counts=tab_counts, dechets=DECHETS,
        saved=saved_data,
        has=has,
        signataire=s.get("x_fdt_signataire") or "",
        deja_fait=bool(s.get("x_fdt_fait")),
        ok=request.args.get("ok"),
        back=request.args.get("back", ""))

def render_fiche_html(card, vals, data, nphotos=0):
    """Résumé HTML de la fiche pour le chatter Odoo."""
    rows_t = ""
    labels_t = {c: (l, u) for c, l, u in TRAVAUX}
    for code, v in data.get("travaux", {}).items():
        label, unit = labels_t.get(code, (code, ""))
        rows_t += f"<tr><td>{label}</td><td>{v.get('qte','')} {unit}</td><td>{v.get('temps','')} h</td></tr>"
    rows_d = ""
    labels_d = dict(DECHETS)
    for code, v in data.get("dechets", {}).items():
        badges = " ".join(b for b, on in [("PROTEC", v.get("badge_protec")), ("CCLST", v.get("badge_cclst"))] if on)
        rows_d += (f"<tr><td>{labels_d.get(code, code)}</td><td>{badges}</td>"
                   f"<td>{v.get('volume','')}</td><td>{v.get('destination','')}</td><td>{v.get('temps','')}</td></tr>")
    html = (
        f"<p><b>📝 Fiche de fin de travaux</b> — {card['client']}</p>"
        f"<p>Véhicule : {vals['x_fdt_vehicule'] or '—'} · "
        f"Arrivée : {vals['x_fdt_heure_arrivee'] or '—'} · Départ : {vals['x_fdt_heure_depart'] or '—'} · "
        f"Trajet A/R : {vals['x_fdt_temps_trajet'] or '—'} · Opérateur(s) : {vals['x_fdt_operateurs'] or '—'}</p>"
        + (f"<p>✍️ Signé par : <b>{vals.get('x_fdt_signataire')}</b></p>" if vals.get('x_fdt_signataire') else "")
        + (f"<p>📷 {nphotos} photo(s) jointe(s) — voir l'onglet Fiche de fin de travaux</p>" if nphotos else "")
    )
    if rows_t:
        html += ("<table border='1' cellpadding='3'><tr><th>Nature des travaux</th><th>Quantité</th><th>Temps</th></tr>"
                 + rows_t + "</table>")
    if vals["x_fdt_commentaires"]:
        html += f"<p><b>Commentaires :</b><br/>{vals['x_fdt_commentaires']}</p>"
    if rows_d:
        html += ("<table border='1' cellpadding='3'><tr><th>Déchets</th><th>Badge</th><th>Vol. m³</th>"
                 "<th>Destination</th><th>Tps dépotage</th></tr>" + rows_d + "</table>")
    return html

# ─── BON D'INTERVENTION (PDF chiffré, via session web du compte technique) ──
BI_REPORT = "protec_custom.report_deliveryslip_priced"
_web_session = {"opener": None}

def _web_opener():
    if _web_session["opener"] is not None:
        return _web_session["opener"]
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    payload = json.dumps({"jsonrpc": "2.0", "method": "call",
        "params": {"db": ODOO_DB, "login": ODOO_USER, "password": ODOO_PASSWORD}}).encode()
    req = urllib.request.Request(f"{ODOO_URL}/web/session/authenticate", data=payload,
                                 headers={"Content-Type": "application/json"})
    opener.open(req, timeout=30)
    _web_session["opener"] = opener
    return opener

@bp.route("/bi/<int:slot_id>")
def bi_pdf(slot_id):
    token = request.args.get("t", "")
    if not check_sig(f"fdt:{slot_id}", token):
        abort(403)
    uid, models = odoo_connect()
    rec = x(models, uid, "planning.slot", "read", [slot_id], fields=["name"])
    if not rec:
        abort(404)
    ref = (rec[0]["name"] or "").strip().split()[0] if rec[0].get("name") else ""
    if not ref:
        return "Pas de commande liée à cette intervention.", 404
    picks = x(models, uid, "stock.picking", "search_read",
              [["origin", "=", ref], ["picking_type_id.sequence_code", "=", "ASS/BI/"]],
              fields=["id", "name", "company_id"], order="id desc", limit=1)
    if not picks:
        return "Pas de bon d'intervention pour cette intervention.", 404
    pid, pname = picks[0]["id"], picks[0]["name"]
    cid = picks[0]["company_id"][0] if picks[0].get("company_id") else 2
    # allowed_company_ids dans l'URL : requis pour les enregistrements hors
    # société par défaut de la session (multi-sociétés)
    import urllib.parse as _up
    ctx = _up.quote(json.dumps({"allowed_company_ids": [cid]}))
    for _attempt in (1, 2):
        try:
            op = _web_opener()
            r = op.open(f"{ODOO_URL}/report/pdf/{BI_REPORT}/{pid}?context={ctx}", timeout=60)
            pdf = r.read()
            if pdf[:4] == b"%PDF":
                fn = pname.replace("/", "_")
                return Response(pdf, mimetype="application/pdf",
                                headers={"Content-Disposition": f'inline; filename="BI_{fn}.pdf"'})
        except Exception:
            pass
        _web_session["opener"] = None  # session expirée : ré-authentifier et réessayer
    return "Erreur de génération du PDF — réessayez.", 502

# ─── PWA : hors connexion pour les chauffeurs ────────────────────────────────
SW_JS = """
const CACHE = 'protec-tournee-v1';
self.addEventListener('install', function (e) { self.skipWaiting(); });
self.addEventListener('activate', function (e) { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', function (e) {
  const req = e.request;
  if (req.method !== 'GET') return;
  const p = new URL(req.url).pathname;
  if (p.indexOf('/ma-tournee') === -1 && p.indexOf('/fiche/') === -1 &&
      p.indexOf('/bi/') === -1 && p.indexOf('/icon-') === -1) return;
  e.respondWith(
    fetch(req).then(function (r) {
      if (r.ok) { var cp = r.clone(); caches.open(CACHE).then(function (c) { c.put(req, cp); }); }
      return r;
    }).catch(function () { return caches.match(req); })
  );
});
"""

@bp.route("/sw.js")
def sw_js():
    return Response(SW_JS, mimetype="application/javascript",
                    headers={"Cache-Control": "no-cache"})

@bp.route("/manifest.json")
def manifest():
    c = request.args.get("c", "")
    sg = request.args.get("s", "")
    base = BASE_PREFIX()
    start = f"{base}/ma-tournee?c={c}&s={sg}" if c else f"{base}/"
    return json.dumps({
        "name": "Ma tournée PROTEC", "short_name": "Tournée",
        "start_url": start, "scope": base + "/",
        "display": "standalone", "background_color": "#3a5a99",
        "theme_color": "#3a5a99",
        "icons": [{"src": f"{base}/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": f"{base}/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }), 200, {"Content-Type": "application/manifest+json"}

def BASE_PREFIX():
    return url_for("protec.week_view").rstrip("/")

_icon_cache = {}

@bp.route("/icon-<int:size>.png")
def icon(size):
    if size not in (192, 512):
        abort(404)
    if size not in _icon_cache:
        from PIL import Image, ImageDraw, ImageFont
        import io
        img = Image.new("RGB", (size, size), "#3a5a99")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", int(size * 0.55))
        except Exception:
            font = ImageFont.load_default()
        d.text((size / 2, size / 2), "P", fill="#ffffff", font=font, anchor="mm")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        _icon_cache[size] = buf.getvalue()
    return Response(_icon_cache[size], mimetype="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})

# ─── LIENS CHAUFFEURS (admin) ────────────────────────────────────────────────
@bp.route("/liens")
def liens():
    if not SECRET or request.args.get("token") != SECRET:
        abort(403)
    error, rows = None, []
    try:
        uid, models = odoo_connect()
        for e in get_all_employees(uid, models):
            url = url_for(".ma_tournee", c=e["id"], s=driver_sig(e["id"]), _external=True)
            rows.append({"id": e["id"], "name": e["name"], "color": emp_color(e["id"]),
                         "url": url})
    except Exception as ex:
        error = str(ex)
    return render_template("liens.html", rows=rows, error=error)

@bp.route("/health")
def health():
    return {"status": "ok", "app": "protec-planning"}

# ─── Exécution seule (tests locaux) ──────────────────────────────────────────
def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    create_app().run(host="0.0.0.0", port=port, debug=False)
