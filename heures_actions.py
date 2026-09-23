# -*- coding: utf-8 -*-
"""Actions RH portées d'Odoo vers Render (économie du module de personnalisations).

Chaque fonction reproduit À L'IDENTIQUE l'action serveur Odoo du même numéro
(code d'origine archivé dans odoo-scan-page/action_heures_*.py). Le contrat
d'interface du relais /heures/rpc est inchangé : les pages envoient
{action_id, ctx} et reçoivent le dict « action » ; HeuresErreur joue le rôle
du UserError d'Odoo (message affiché tel quel à l'utilisateur).

Les écritures passent par XML-RPC : les automatisations Odoo (miroir
hr.leave, e-mails de demande de congés…) se déclenchent normalement.
"""
import datetime
from zoneinfo import ZoneInfo

TZ_PARIS = ZoneInfo("Europe/Paris")
TZ_UTC = ZoneInfo("UTC")


class HeuresErreur(Exception):
    """Equivalent du UserError : message destiné à l'utilisateur."""


# Caches process-local : chaque aller-retour XML-RPC coûte ~200 ms, on évite
# de repayer à chaque saisie ce qui ne bouge presque jamais.
_PARAM_TTL = {"maquignon.rh_admin_key": 3600.0, "maquignon.heures_verrou": 20.0}
_param_cache = {}
_cal_cache = {}


def _param(call, cle):
    import time as _t
    ttl = _PARAM_TTL.get(cle, 0.0)
    if ttl:
        val, expire = _param_cache.get(cle, (None, 0.0))
        if _t.monotonic() < expire:
            return val
    val = call("ir.config_parameter", "get_param", cle) or ""
    if ttl:
        _param_cache[cle] = (val, _t.monotonic() + ttl)
    return val


def _admin_ok(call, ctx):
    adm = (ctx.get("hj_k") or "")
    return bool(adm and adm == _param(call, "maquignon.rh_admin_key"))


def _emp(call, emp_id, champs):
    recs = call("hr.employee", "read", [int(emp_id)], champs)
    return recs[0] if recs else None


def _cal_info(call, cal_id):
    """Calendrier + plages : [{dayofweek, week_type, display_type, hour_from, hour_to}]."""
    import time as _t
    entree = _cal_cache.get(cal_id)
    if entree and _t.monotonic() < entree[2]:
        return entree[0], entree[1]
    cal = call("resource.calendar", "read", [cal_id],
               ["name", "two_weeks_calendar", "company_id"])[0]
    atts = call("resource.calendar.attendance", "search_read",
                [["calendar_id", "=", cal_id]],
                ["dayofweek", "week_type", "display_type", "hour_from", "hour_to"])
    _cal_cache[cal_id] = (cal, atts, _t.monotonic() + 300.0)
    return cal, atts


def _rngs_jour(cal, atts, d):
    """Plages [début, fin] du calendrier pour la date d (cycle 2 semaines géré)."""
    days = (d - datetime.date(1970, 1, 5)).days
    wt = str((days // 7) % 2)
    rngs = []
    for att in atts:
        if att["dayofweek"] != str(d.weekday()):
            continue
        if cal["two_weeks_calendar"] and att["week_type"] and att["week_type"] != wt:
            continue
        if att["display_type"]:
            continue
        rngs.append([att["hour_from"], att["hour_to"]])
    return rngs


def _purge_pointages(call, emp_id, d):
    """Supprime les pointages Présences du jour (heure de Paris)."""
    day0 = datetime.datetime(d.year, d.month, d.day, tzinfo=TZ_PARIS).astimezone(TZ_UTC).replace(tzinfo=None)
    day1 = (datetime.datetime(d.year, d.month, d.day, tzinfo=TZ_PARIS)
            + datetime.timedelta(days=1)).astimezone(TZ_UTC).replace(tzinfo=None)
    ids = call("hr.attendance", "search",
               [["employee_id", "=", emp_id],
                ["check_in", ">=", day0.strftime("%Y-%m-%d %H:%M:%S")],
                ["check_in", "<", day1.strftime("%Y-%m-%d %H:%M:%S")]])
    if ids:
        call("hr.attendance", "unlink", ids)


def _decoupe_conge(rngs, c_de, c_a):
    """Retire le créneau [c_de, c_a] des plages ; renvoie les plages restantes."""
    keep = []
    for r in rngs:
        a0, a1 = r[0], r[1]
        if c_a <= a0 or c_de >= a1:
            keep.append([a0, a1])
        elif c_de <= a0 and c_a >= a1:
            continue
        elif c_de <= a0:
            keep.append([c_a, a1])
        elif c_a >= a1:
            keep.append([a0, c_de])
        else:
            if (c_de - a0) >= (a1 - c_a):
                keep.append([a0, c_de])
            else:
                keep.append([c_a, a1])
    return keep


def _deux_creneaux(keep):
    """Garde les 2 plages les plus longues, ventilées matin / après-midi."""
    keep2 = sorted(sorted(keep, key=lambda r: r[1] - r[0], reverse=True)[:2], key=lambda r: r[0])
    m, am = [0.0, 0.0], [0.0, 0.0]
    if len(keep2) == 2:
        m, am = keep2[0], keep2[1]
    elif keep2:
        if keep2[0][0] < 12.5:
            m = keep2[0]
        else:
            am = keep2[0]
    return keep2, m, am


# ─── 2012 : saisie des heures d'un jour + mouvements de récup ────────────────
TYPES_JOUR = ("travail", "cp", "maladie", "ferie", "absence", "recup", "repos", "sans_solde")
TYPES_SALARIE = ("travail", "recup", "sans_solde")   # posés par le salarié lui-même, sans validation
TYPES_BUREAU = ("cp", "maladie", "ferie", "absence", "repos")
LBL_JOUR = {"cp": "Congés payés", "recup": "Récupération", "maladie": "Maladie", "ferie": "Férié",
            "absence": "Absence", "sans_solde": "Sans solde", "repos": "Repos"}


def _quart(v):
    """Arrondi au quart d'heure."""
    return round(float(v or 0.0) * 4) / 4.0


def _fr(h):
    return ("%.2f" % h).replace(".", ",")


def _hm(h):
    return "%02d:%02d" % (int(h), round((h - int(h)) * 60))


def _delta_recup(typ, heures, theo, h_ss, payees):
    """Heures du jour comptées dans le solde « à récupérer » (x_hs) :
    - jour travaillé : travaillé + sans solde − horaire. Les heures faites en plus s'ajoutent au solde
      (heures sup en récup par défaut), les heures manquantes s'en déduisent (récup prise ou non expliquée),
      les heures sans solde ne sont ni dues ni payées. Si les heures sup sont payées, le surplus n'entre pas.
    - journée entière en récup : − horaire. Journée sans solde, congé, maladie, férié, absence : 0."""
    if typ == "travail":
        h = min(heures, theo) if payees else heures
        return round(h + h_ss - theo, 4)
    if typ == "recup":
        return round(-theo, 4)
    return 0.0


def _a2012(call, ctx):
    action = {}
    emp_id = ctx.get("hj_emp")
    dstr = ctx.get("hj_date")
    if emp_id and dstr:
        emp = _emp(call, emp_id, ["x_heures_token", "resource_calendar_id"])
        tok = (ctx.get("hj_token") or "")
        is_adm = _admin_ok(call, ctx)
        if not emp or not (is_adm or (tok and tok == (emp["x_heures_token"] or ""))):
            raise HeuresErreur("Lien invalide — demandez votre lien personnel à votre responsable.")
        d = datetime.datetime.strptime(dstr, "%Y-%m-%d").date()
        typ = ctx.get("hj_type") or "travail"
        if typ not in TYPES_JOUR:
            raise HeuresErreur("Type de journée inconnu.")
        ex = call("x_heures_jour", "search_read",
                  [["x_employee_id", "=", emp["id"]], ["x_date", "=", dstr]],
                  ["x_type", "x_hs_payees", "x_note"], limit=1)
        ex = ex[0] if ex else None
        if not is_adm:
            verrou = _param(call, "maquignon.heures_verrou")
            if verrou and dstr <= verrou:
                raise HeuresErreur("Les feuilles d'heures jusqu'au %s sont verrouillées (paie établie). Contactez le bureau pour toute correction."
                                   % datetime.datetime.strptime(verrou, "%Y-%m-%d").strftime("%d/%m/%Y"))
            if typ not in TYPES_SALARIE:
                raise HeuresErreur("Seul le bureau peut enregistrer un congé payé, une maladie, un jour férié ou une absence. Pour des congés, utilisez « Demander des congés » en bas de page.")
            if ex and ex["x_type"] in TYPES_BUREAU:
                raise HeuresErreur("Cette journée a été enregistrée par le bureau (congé, maladie, férié…) : elle n'est pas modifiable ici. Prévenez le bureau en cas d'erreur.")
        md = float(ctx.get("hj_m_deb") or 0.0)
        mf = float(ctx.get("hj_m_fin") or 0.0)
        ad = float(ctx.get("hj_am_deb") or 0.0)
        af = float(ctx.get("hj_am_fin") or 0.0)
        theo, rngs = 0.0, []
        if emp["resource_calendar_id"]:
            cal, atts = _cal_info(call, emp["resource_calendar_id"][0])
            rngs = _rngs_jour(cal, atts, d)
            theo = sum(r[1] - r[0] for r in rngs)
        heures = max(mf - md, 0.0) + max(af - ad, 0.0) if typ == "travail" else 0.0
        periode = (ctx.get("hj_periode") or "journee")
        partiel = bool(is_adm and typ not in ("travail", "repos")
                       and periode in ("matin", "apresmidi", "horaires"))
        h_recup = h_ss = 0.0
        payees = bool(ex and ex.get("x_hs_payees"))
        if is_adm and "hj_hs_payees" in ctx:
            payees = bool(int(ctx.get("hj_hs_payees") or 0))
        if "hj_note" in ctx:
            note = (ctx.get("hj_note") or "").strip() or False
        else:
            # note existante conservée (bureau), sauf la note automatique d'une saisie partielle
            # récup / sans solde : la nouvelle saisie fait foi
            note = (ex and ex.get("x_note")) or False
            if note and (note.startswith("Récup ") or note.startswith("Sans solde ")):
                note = False
        theo_j = theo
        if partiel:
            if periode == "matin":
                keep = [r for r in rngs if r[0] >= 12.5]
            elif periode == "apresmidi":
                keep = [r for r in rngs if r[0] < 12.5]
            else:
                c_de = float(ctx.get("hj_c_de") or 0.0)
                c_a = float(ctx.get("hj_c_a") or 0.0)
                if not (0.0 <= c_de < c_a <= 24.0):
                    raise HeuresErreur("Renseignez les horaires du congé (début avant fin).")
                keep = _decoupe_conge(rngs, c_de, c_a)
            if not keep:
                partiel = False
            else:
                keep2, m, am = _deux_creneaux(keep)
                md, mf, ad, af = m[0], m[1], am[0], am[1]
                heures = sum(r[1] - r[0] for r in keep2)
                if typ in ("recup", "sans_solde"):
                    # récup / sans solde partiel : l'horaire reste entier, les heures retirées
                    # sont des heures de récup prises ou des heures sans solde
                    retire = max(theo - heures, 0.0)
                    if typ == "recup":
                        h_recup = retire
                    else:
                        h_ss = retire
                    note = "%s %s h (bureau)" % ("Récup" if typ == "recup" else "Sans solde", _fr(retire))
                    typ = "travail"
                else:
                    # congé / maladie / férié / absence partiel : le reste de la journée est travaillé,
                    # l'horaire attendu se limite aux plages restantes
                    theo_j = heures
                    if periode == "matin":
                        perlbl = "matin en congé"
                    elif periode == "apresmidi":
                        perlbl = "après-midi en congé"
                    else:
                        perlbl = "congé de %.2gh à %.2gh" % (c_de, c_a)
                    note = "%s — %s (bureau)" % (LBL_JOUR.get(typ, "Congé"), perlbl)
                    typ = "travail"
        if not partiel:
            if typ == "travail":
                try:
                    h_recup = _quart(ctx.get("hj_h_recup") or 0.0)
                    h_ss = _quart(ctx.get("hj_h_ss") or 0.0)
                except (TypeError, ValueError):
                    raise HeuresErreur("Heures de récup / sans solde invalides.")
                # créneaux « de telle heure à telle heure » : la durée fait foi, note automatique
                plages = []
                for cle, lbl in (("recup", "Récup"), ("ss", "Sans solde")):
                    de, a = ctx.get("hj_%s_de" % cle), ctx.get("hj_%s_a" % cle)
                    if de in (None, "") or a in (None, ""):
                        continue
                    try:
                        de, a = float(de), float(a)
                    except (TypeError, ValueError):
                        raise HeuresErreur("Créneau de %s invalide." % lbl.lower())
                    if not (0.0 <= de < a <= 24.0):
                        raise HeuresErreur("%s : indiquez une heure de début avant l'heure de fin." % lbl)
                    for (h1, h2) in ((md, mf), (ad, af)):
                        if h2 > h1 and de < h2 and a > h1:
                            raise HeuresErreur("Le créneau %s de %s à %s chevauche vos heures travaillées (%s-%s). Corrigez les horaires."
                                               % (lbl.lower(), _hm(de), _hm(a), _hm(h1), _hm(h2)))
                    if cle == "recup":
                        h_recup = _quart(a - de)
                    else:
                        h_ss = _quart(a - de)
                    plages.append("%s %s-%s" % (lbl, _hm(de), _hm(a)))
                if plages:
                    note = " · ".join(plages)
                if h_recup < 0 or h_ss < 0 or h_recup > 12 or h_ss > 12:
                    raise HeuresErreur("Heures de récup / sans solde : entre 0 et 12 h.")
                manque = max(theo - heures, 0.0)
                if h_recup + h_ss > manque + 0.01:
                    raise HeuresErreur("Vous indiquez %s h de récup et %s h sans solde, mais il ne manque que %s h par rapport à l'horaire du jour (%s h prévues, %s h travaillées). Corrigez les heures."
                                       % (_fr(h_recup), _fr(h_ss), _fr(manque), _fr(theo), _fr(heures)))
                # toute la journée déclarée dans les champs = journée entière
                if theo > 0 and heures <= 0.01 and abs(h_recup - theo) <= 0.01:
                    typ = "recup"
                elif theo > 0 and heures <= 0.01 and abs(h_ss - theo) <= 0.01:
                    typ = "sans_solde"
            if typ in ("recup", "sans_solde"):
                if theo <= 0:
                    raise HeuresErreur("Pas d'horaire prévu ce jour : rien à poser en récup ou sans solde.")
                h_recup = theo if typ == "recup" else 0.0
                h_ss = theo if typ == "sans_solde" else 0.0
            elif typ != "travail":
                h_recup = h_ss = 0.0
        hs = _delta_recup(typ, heures, theo_j, h_ss, payees)
        vals = {"x_employee_id": emp["id"], "x_date": dstr, "x_type": typ,
                "x_m_deb": md, "x_m_fin": mf, "x_am_deb": ad, "x_am_fin": af,
                "x_heures": heures, "x_theo": theo_j, "x_hs": hs,
                "x_h_recup": h_recup, "x_h_sans_solde": h_ss, "x_hs_payees": payees,
                "x_note": note}
        if "hj_decouchage" in ctx:
            vals["x_decouchage"] = bool(int(ctx.get("hj_decouchage") or 0))
        if ex:
            call("x_heures_jour", "write", [ex["id"]], vals)
        else:
            call("x_heures_jour", "create", [vals])
        # Synchronisation Présences : la saisie web vaut pointage kiosque.
        _purge_pointages(call, emp["id"], d)
        if typ == "travail":
            for (h1, h2) in [(md, mf), (ad, af)]:
                if h2 > h1:
                    ci = (datetime.datetime(d.year, d.month, d.day, tzinfo=TZ_PARIS)
                          + datetime.timedelta(hours=h1)).astimezone(TZ_UTC).replace(tzinfo=None)
                    co = (datetime.datetime(d.year, d.month, d.day, tzinfo=TZ_PARIS)
                          + datetime.timedelta(hours=h2)).astimezone(TZ_UTC).replace(tzinfo=None)
                    call("hr.attendance", "create", [{
                        "employee_id": emp["id"],
                        "check_in": ci.strftime("%Y-%m-%d %H:%M:%S"),
                        "check_out": co.strftime("%Y-%m-%d %H:%M:%S")}])
        # ancien champ « + heures à récupérer » (x_recup_ligne) : conservé pour les pages en cache
        rq = None
        if "hj_recup" in ctx and typ == "travail":
            try:
                rq = float(ctx.get("hj_recup") or 0.0)
            except (TypeError, ValueError):
                raise HeuresErreur("Heures à récupérer invalides.")
            if rq < 0 or rq > 12:
                raise HeuresErreur("Heures à récupérer : entre 0 et 12 h.")
            rq = round(rq * 4) / 4.0
            lignes = call("x_recup_ligne", "search_read",
                          [["x_employee_id", "=", emp["id"]], ["x_date", "=", dstr]], ["id", "x_heures"])
            if rq > 0:
                if lignes:
                    call("x_recup_ligne", "write", [lignes[0]["id"]], {"x_heures": rq})
                    if len(lignes) > 1:
                        call("x_recup_ligne", "unlink", [l["id"] for l in lignes[1:]])
                else:
                    call("x_recup_ligne", "create", [{
                        "x_employee_id": emp["id"], "x_date": dstr, "x_heures": rq,
                        "x_note": "saisi avec les heures du jour"}])
            elif lignes:
                call("x_recup_ligne", "unlink", [l["id"] for l in lignes])
        action = {"hj_ok": 1, "type": typ, "heures": heures, "theo": theo_j, "hs": hs,
                  "h_recup": h_recup, "h_ss": h_ss, "payees": 1 if payees else 0,
                  "partiel": 1 if partiel else 0, "recup": rq or 0}

    # --- Récup : mouvements d'heures saisis par le salarié (ou le bureau) ---
    if ctx.get("recup_add") or ctx.get("recup_del"):
        emp2 = _emp(call, ctx.get("ra_emp") or 0, ["x_heures_token"])
        tok2 = (ctx.get("ra_token") or "")
        is_adm2 = _admin_ok(call, ctx)
        if not (emp2 and (is_adm2 or (tok2 and emp2["x_heures_token"] and tok2 == emp2["x_heures_token"]))):
            raise HeuresErreur("Lien invalide — demandez votre lien personnel à votre responsable.")
        verrou2 = _param(call, "maquignon.heures_verrou")
        if ctx.get("recup_del"):
            lg = call("x_recup_ligne", "read", [int(ctx.get("ra_id") or 0)], ["x_employee_id", "x_date"])
            lg = lg[0] if lg else None
            if not lg or (lg["x_employee_id"] and lg["x_employee_id"][0]) != emp2["id"]:
                raise HeuresErreur("Ligne introuvable.")
            if not is_adm2 and verrou2 and str(lg["x_date"])[:10] <= verrou2:
                raise HeuresErreur("Cette ligne porte sur une période verrouillée (paie établie). Contactez le bureau.")
            call("x_recup_ligne", "unlink", [lg["id"]])
            action = {"ok": 1, "del": 1}
        else:
            try:
                dr = datetime.datetime.strptime(str(ctx.get("ra_date"))[:10], "%Y-%m-%d").date()
            except Exception:
                raise HeuresErreur("Date invalide.")
            try:
                hres = float(ctx.get("ra_h"))
            except Exception:
                raise HeuresErreur("Nombre d'heures invalide.")
            if hres < 0.25 or hres > 12:
                raise HeuresErreur("Heures à mettre en récup : entre 0,25 et 12 h.")
            if dr > datetime.date.today():
                raise HeuresErreur("La date ne peut pas être dans le futur.")
            if not is_adm2 and verrou2 and dr.strftime("%Y-%m-%d") <= verrou2:
                raise HeuresErreur("Les feuilles d'heures de cette période sont verrouillées (paie établie). Contactez le bureau.")
            lid = call("x_recup_ligne", "create", [{
                "x_employee_id": emp2["id"], "x_date": dr.strftime("%Y-%m-%d"),
                "x_heures": hres, "x_note": (ctx.get("ra_note") or "")[:200]}])
            lid = lid[0] if isinstance(lid, list) else lid
            action = {"ok": 1, "id": lid}
    return action


# ─── 2013 : demande de congés (salarié) ──────────────────────────────────────
def _a2013(call, ctx):
    emp_id = ctx.get("dc_emp")
    if not emp_id:
        return {}
    emp = _emp(call, emp_id, ["x_heures_token"])
    tok = (ctx.get("dc_token") or "")
    if not emp or not (tok and tok == (emp["x_heures_token"] or "")):
        raise HeuresErreur("Lien invalide.")
    du, au = ctx.get("dc_du"), ctx.get("dc_au")
    if not du or not au or du > au:
        raise HeuresErreur("Dates invalides.")
    periode = ctx.get("dc_periode") or "journee"
    if periode not in ("journee", "matin", "apresmidi", "horaires"):
        periode = "journee"
    h_de = h_a = 0.0
    if periode == "horaires":
        try:
            h_de = float(ctx.get("dc_h_de") or 0.0)
            h_a = float(ctx.get("dc_h_a") or 0.0)
        except Exception:
            h_de = h_a = 0.0
        if not (0.0 <= h_de < h_a <= 24.0):
            raise HeuresErreur("Horaires invalides.")
    rid = call("x_demande_conge", "create", [{
        "x_employee_id": emp["id"], "x_du": du, "x_au": au,
        "x_type": ctx.get("dc_type") or "cp",
        "x_periode": periode, "x_h_de": h_de, "x_h_a": h_a,
        "x_motif": (ctx.get("dc_motif") or "").strip() or False,
        "x_statut": "attente"}])
    rid = rid[0] if isinstance(rid, list) else rid
    return {"dc_ok": 1, "id": rid}


# ─── 2014 : réponse à une demande de congés (bureau) ─────────────────────────
def _a2014(call, ctx):
    dc_id = ctx.get("dc_id")
    if not (dc_id and _admin_ok(call, ctx)):
        return {}
    dc = call("x_demande_conge", "read", [int(dc_id)],
              ["x_employee_id", "x_type", "x_periode", "x_du", "x_au", "x_h_de", "x_h_a"])[0]
    decision = ctx.get("dc_decision")
    if decision not in ("approuve", "refuse"):
        raise HeuresErreur("Décision invalide.")
    call("x_demande_conge", "write", [dc["id"]],
         {"x_statut": decision, "x_reponse": (ctx.get("dc_reponse") or "").strip() or False})
    n = 0
    if decision == "approuve":
        emp = _emp(call, dc["x_employee_id"][0], ["resource_calendar_id"])
        cal = atts = None
        if emp["resource_calendar_id"]:
            cal, atts = _cal_info(call, emp["resource_calendar_id"][0])
        typmap = {"cp": "cp", "recup": "recup", "sans_solde": "sans_solde", "maternite": "absence",
                  "paternite": "absence", "evt_familial": "absence", "enfant_malade": "absence"}
        typlbl = {"cp": "Congés payés", "recup": "Récupération", "sans_solde": "Sans solde",
                  "maternite": "Congé maternité", "paternite": "Congé paternité",
                  "evt_familial": "Événement familial", "enfant_malade": "Enfant malade"}
        jtyp = typmap.get(dc["x_type"], "cp")
        periode = dc["x_periode"] or "journee"
        d = datetime.datetime.strptime(str(dc["x_du"])[:10], "%Y-%m-%d").date()
        fin = datetime.datetime.strptime(str(dc["x_au"])[:10], "%Y-%m-%d").date()
        while d <= fin:
            rngs = _rngs_jour(cal, atts, d) if cal else []
            theo = sum(r[1] - r[0] for r in rngs)
            if theo > 0:
                dstr = d.strftime("%Y-%m-%d")
                if periode == "matin":
                    keep = [r for r in rngs if r[0] >= 12.5]
                elif periode == "apresmidi":
                    keep = [r for r in rngs if r[0] < 12.5]
                elif periode == "horaires":
                    keep = _decoupe_conge(rngs, dc["x_h_de"], dc["x_h_a"])
                else:
                    keep = []
                if periode == "journee" or not keep:
                    vals = {"x_employee_id": emp["id"], "x_date": dstr, "x_type": jtyp,
                            "x_m_deb": 0.0, "x_m_fin": 0.0, "x_am_deb": 0.0, "x_am_fin": 0.0,
                            "x_heures": 0.0, "x_theo": theo,
                            "x_hs": _delta_recup(jtyp, 0.0, theo, theo if jtyp == "sans_solde" else 0.0, False),
                            "x_h_recup": theo if jtyp == "recup" else 0.0,
                            "x_h_sans_solde": theo if jtyp == "sans_solde" else 0.0,
                            "x_note": "%s approuvé (demande %s)" % (typlbl.get(dc["x_type"], "Congé"), dc["id"])}
                    purge = True
                else:
                    keep2, m, am = _deux_creneaux(keep)
                    tot = sum(r[1] - r[0] for r in keep2)
                    if jtyp in ("recup", "sans_solde"):
                        retire = max(theo - tot, 0.0)
                        h_r = retire if jtyp == "recup" else 0.0
                        h_s = retire if jtyp == "sans_solde" else 0.0
                        vals = {"x_employee_id": emp["id"], "x_date": dstr, "x_type": "travail",
                                "x_m_deb": m[0], "x_m_fin": m[1], "x_am_deb": am[0], "x_am_fin": am[1],
                                "x_heures": tot, "x_theo": theo,
                                "x_hs": _delta_recup("travail", tot, theo, h_s, False),
                                "x_h_recup": h_r, "x_h_sans_solde": h_s,
                                "x_note": "%s %s h (demande %s)" % ("Récup" if jtyp == "recup" else "Sans solde", _fr(retire), dc["id"])}
                    else:
                        if periode == "matin":
                            perlbl = "matin en congé"
                        elif periode == "apresmidi":
                            perlbl = "après-midi en congé"
                        else:
                            perlbl = "congé de %.2gh à %.2gh" % (dc["x_h_de"], dc["x_h_a"])
                        vals = {"x_employee_id": emp["id"], "x_date": dstr, "x_type": "travail",
                                "x_m_deb": m[0], "x_m_fin": m[1], "x_am_deb": am[0], "x_am_fin": am[1],
                                "x_heures": tot, "x_theo": tot, "x_hs": 0.0,
                                "x_h_recup": 0.0, "x_h_sans_solde": 0.0,
                                "x_note": "%s — %s (demande %s)" % (typlbl.get(dc["x_type"], "Congé"), perlbl, dc["id"])}
                    purge = False
                ex = call("x_heures_jour", "search",
                          [["x_employee_id", "=", emp["id"]], ["x_date", "=", dstr]], limit=1)
                if ex:
                    call("x_heures_jour", "write", ex, vals)
                else:
                    call("x_heures_jour", "create", [vals])
                if purge:
                    _purge_pointages(call, emp["id"], d)
                n += 1
            d = d + datetime.timedelta(days=1)
    return {"dc_ok": 1, "jours": n}


# ─── 2020 : régénérer le lien personnel d'un salarié ─────────────────────────
def _a2020(call, ctx):
    emp_id = ctx.get("emp_id")
    newtok = (ctx.get("new_token") or "").strip()
    if not (emp_id and _admin_ok(call, ctx)):
        return {}
    if len(newtok) < 12 or len(newtok) > 64:
        raise HeuresErreur("Token invalide.")
    call("hr.employee", "write", [int(emp_id)], {"x_heures_token": newtok})
    return {"ok": 1}


# ─── 2021 : semaine type + acquis CP / récup / contrat / matricule ───────────
def _a2021(call, ctx):
    action = {}
    emp_id = ctx.get("emp_id")
    est_adm = _admin_ok(call, ctx)
    hor = ctx.get("horaires")
    hor_b = ctx.get("horaires_b") or []
    deux = bool(ctx.get("deux_semaines")) and len(hor_b) == 7
    if emp_id and est_adm and hor and len(hor) == 7:
        emp = _emp(call, emp_id, ["name", "company_id", "resource_calendar_id"])
        JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        weeks = [(hor, "0", 1, "Semaine A")]
        if deux:
            weeks.append((hor_b, "1", 26, "Semaine B"))
        att_vals = []
        tot = 0.0
        ndays = 0
        for hh, wt, seq, lbl in weeks:
            if deux:
                att_vals.append((0, 0, {"name": lbl, "dayofweek": "0",
                                        "hour_from": 0.0, "hour_to": 0.0,
                                        "day_period": "morning", "week_type": wt,
                                        "display_type": "line_section", "sequence": seq - 1}))
            for i in range(7):
                md = float(hh[i][0] or 0)
                mf = float(hh[i][1] or 0)
                ad = float(hh[i][2] or 0)
                af = float(hh[i][3] or 0)
                day = False
                if mf > md:
                    v = {"name": JOURS[i] + " matin", "dayofweek": str(i),
                         "hour_from": md, "hour_to": mf, "day_period": "morning",
                         "sequence": seq + i * 3}
                    if deux:
                        v["week_type"] = wt
                    att_vals.append((0, 0, v))
                    tot += mf - md
                    day = True
                if af > ad:
                    v = {"name": JOURS[i] + " après-midi", "dayofweek": str(i),
                         "hour_from": ad, "hour_to": af, "day_period": "afternoon",
                         "sequence": seq + i * 3 + 1}
                    if deux:
                        v["week_type"] = wt
                    att_vals.append((0, 0, v))
                    tot += af - ad
                    day = True
                if day:
                    ndays += 1
        if not att_vals:
            raise HeuresErreur("Aucune plage horaire saisie.")
        name = "Horaire — %s" % emp["name"]
        cal_id = emp["resource_calendar_id"] and emp["resource_calendar_id"][0]
        cal_nom = emp["resource_calendar_id"] and emp["resource_calendar_id"][1] or ""
        if cal_id and cal_nom.startswith("Horaire — "):
            call("resource.calendar", "write", [cal_id], {"attendance_ids": [(5, 0, 0)]})
            call("resource.calendar", "write", [cal_id],
                 {"name": name, "two_weeks_calendar": deux, "attendance_ids": att_vals})
            newcal = cal_id
        else:
            newcal = call("resource.calendar", "create", [{
                "name": name, "company_id": emp["company_id"][0],
                "two_weeks_calendar": deux, "attendance_ids": att_vals}])
            newcal = newcal[0] if isinstance(newcal, list) else newcal
            try:
                call("hr.employee", "write", [emp["id"]], {"resource_calendar_id": newcal})
            except Exception as e:
                det = str(e)
                if "attribution" in det or "allocation" in det:
                    raise HeuresErreur("Impossible de changer l'horaire de %s : un de ses congés déjà validés n'est couvert par aucune attribution de congés (période close ou attribution manquante). Créez l'attribution correspondante dans Congés, puis réessayez." % emp["name"])
                raise HeuresErreur("Impossible de changer l'horaire de %s : %s" % (emp["name"], det[-200:]))
        if ndays:
            call("resource.calendar", "write", [newcal], {"hours_per_day": tot / ndays})
        _cal_cache.pop(newcal, None)
        if cal_id:
            _cal_cache.pop(cal_id, None)
        action = {"ok": 1, "total": tot, "deux": deux, "cal": newcal,
                  "semaine": tot / 2.0 if deux else tot}

    # --- Saisie des congés acquis N / N-1 depuis la page Horaires par défaut ---
    if ctx.get("cp_mode") and emp_id and est_adm:
        emp = _emp(call, emp_id, ["name"])
        resultat = {}
        for cle, type_id, libelle in [("cp_n", 1, "Congés payés"), ("cp_n1", 7, "Congés Payés N-1")]:
            brut = ctx.get(cle)
            if brut in (None, ""):
                continue
            try:
                val = float(brut)
            except Exception:
                raise HeuresErreur("Valeur invalide pour %s." % libelle)
            if val < 0 or val > 100:
                raise HeuresErreur("Valeur hors limites pour %s (0 à 100 jours)." % libelle)
            allocs = call("hr.leave.allocation", "search_read",
                          [["employee_id", "=", emp["id"]],
                           ["holiday_status_id", "=", type_id], ["state", "=", "validate"]],
                          ["allocation_type", "date_from"], order="id")
            aujourd = datetime.date.today()
            periode_debut = datetime.date(aujourd.year if aujourd.month >= 6 else aujourd.year - 1, 6, 1).strftime("%Y-%m-%d")
            if allocs:
                # consolidation : une seule allocation validée porte la valeur
                # saisie ; les autres sont refusées (0 refusé par Odoo v19)
                accr = [a for a in allocs if a["allocation_type"] == "accrual"]
                keeper = (accr or allocs)[-1]
                if val > 0:
                    vals_k = {"number_of_days": val}
                    if not keeper["date_from"] or str(keeper["date_from"])[:10] > periode_debut:
                        vals_k["date_from"] = periode_debut
                    call("hr.leave.allocation", "write", [keeper["id"]], vals_k)
                    autres = [a["id"] for a in allocs if a["id"] != keeper["id"]]
                else:
                    autres = [a["id"] for a in allocs]
                if autres:
                    call("hr.leave.allocation", "action_refuse", autres)
            else:
                nid = call("hr.leave.allocation", "create", [{
                    "name": "%s (%g jour(s))" % (libelle, val),
                    "employee_id": emp["id"],
                    "holiday_status_id": type_id,
                    "number_of_days": val,
                    "allocation_type": "regular",
                    "date_from": periode_debut}])
                nid = nid[0] if isinstance(nid, list) else nid
                call("hr.leave.allocation", "action_approve", [nid])
            resultat[cle] = val
        brut_r = ctx.get("recup_h")
        if brut_r not in (None, ""):
            try:
                val_r = float(brut_r)
            except Exception:
                raise HeuresErreur("Valeur invalide pour les heures à récupérer.")
            if val_r < -500 or val_r > 500:
                raise HeuresErreur("Heures à récupérer hors limites (-500 à 500).")
            call("hr.employee", "write", [emp["id"]], {"x_recup_solde": val_r})
            resultat["recup_h"] = val_r
        brut_cm = ctx.get("contrat_mensuel")
        if brut_cm is not None:
            if str(brut_cm).strip() == "":
                call("hr.employee", "write", [emp["id"]], {"x_contrat_mensuel": 0})
            else:
                try:
                    v_cm = float(str(brut_cm).replace(",", "."))
                except Exception:
                    raise HeuresErreur("Contrat mensuel invalide.")
                if v_cm < 0 or v_cm > 300:
                    raise HeuresErreur("Contrat mensuel hors limites (0 à 300 h).")
                call("hr.employee", "write", [emp["id"]], {"x_contrat_mensuel": v_cm})
        brut_m = ctx.get("matricule")
        if brut_m is not None:
            call("hr.employee", "write", [emp["id"]], {"x_matricule_paie": (str(brut_m).strip() or False)})
        if resultat:
            # une saisie de CP peut débloquer le miroir natif : relancer les
            # jours d'août sans hr.leave (la réécriture de x_note déclenche
            # l'automatisation miroir côté Odoo)
            for rec2 in call("x_heures_jour", "search_read",
                             [["x_employee_id", "=", emp["id"]], ["x_date", ">=", "2026-08-01"]],
                             ["x_type", "x_note"]):
                est_conge = rec2["x_type"] in ("cp", "maladie", "recup", "absence") or \
                    (rec2["x_type"] == "travail" and rec2["x_note"] and "en congé" in rec2["x_note"])
                if est_conge and not call("hr.leave", "search_count",
                                          [["x_hj_id", "=", rec2["id"]], ["state", "=", "validate"]]):
                    call("x_heures_jour", "write", [rec2["id"]], {"x_note": rec2["x_note"]})
        brut_d = ctx.get("cp_date")
        if resultat:
            if brut_d:
                try:
                    ref = datetime.datetime.strptime(str(brut_d)[:10], "%Y-%m-%d").date()
                except Exception:
                    raise HeuresErreur("Date de saisie invalide (format attendu AAAA-MM-JJ).")
            else:
                ref = datetime.date.today()
            call("hr.employee", "write", [emp["id"]], {"x_cp_ref_date": ref.strftime("%Y-%m-%d")})
            resultat["cp_date"] = ref.strftime("%Y-%m-%d")
        action = {"ok": 1, "maj": resultat}
    return action


# ─── 2048 : coordonnées personnelles du salarié ──────────────────────────────
def _a2048(call, ctx):
    emp_id = ctx.get("co_emp")
    if not emp_id:
        return {}
    ALLOWED = {"co_mobile": ("private_phone", "Portable"),
               "co_email": ("private_email", "Email perso"),
               "co_rue": ("private_street", "Adresse"),
               "co_cp": ("private_zip", "Code postal"),
               "co_ville": ("private_city", "Ville"),
               "co_urg_nom": ("emergency_contact", "Contact urgence"),
               "co_urg_tel": ("emergency_phone", "Tél. urgence")}
    emp = _emp(call, emp_id, ["x_heures_token"] + [f for f, _ in ALLOWED.values()])
    tok = (ctx.get("co_token") or "")
    if not emp or not (tok and tok == (emp["x_heures_token"] or "")):
        raise HeuresErreur("Lien invalide — demandez votre lien personnel à votre responsable.")
    vals, changes = {}, []
    for k, (f, lbl) in ALLOWED.items():
        if k in ctx:
            new = (ctx.get(k) or "").strip()
            old = emp[f] or ""
            if new != old:
                vals[f] = new or False
                changes.append("%s : « %s » → « %s »" % (lbl, old or "—", new or "—"))
    if vals:
        call("hr.employee", "write", [emp["id"]], vals)
        call("hr.employee", "message_post", [emp["id"]],
             body="📇 Coordonnées mises à jour par le salarié depuis sa page personnelle — " + " ; ".join(changes))
    return {"ok": 1, "changed": len(vals)}


# ─── 2050 : verrou de paie ───────────────────────────────────────────────────
def _a2050(call, ctx):
    if not _admin_ok(call, ctx):
        raise HeuresErreur("Clé responsables requise.")
    vl = (ctx.get("vl_date") or "").strip()
    if vl:
        datetime.datetime.strptime(vl, "%Y-%m-%d")
        call("ir.config_parameter", "set_param", "maquignon.heures_verrou", vl)
    else:
        call("ir.config_parameter", "set_param", "maquignon.heures_verrou", "")
    _param_cache.pop("maquignon.heures_verrou", None)
    return {"ok": 1, "verrou": vl}


# ─── 2069 : décision manager sur une demande (lien signé e-mail) ─────────────
def _a2069(call, ctx):
    dc_id = ctx.get("dc_id")
    tok = (ctx.get("dc_token") or "").strip()
    decision = ctx.get("dc_decision")
    if not dc_id or not tok:
        raise HeuresErreur("Lien invalide.")
    dc = call("x_demande_conge", "read", [int(dc_id)], ["x_token", "x_statut"])
    dc = dc[0] if dc else None
    if not dc or not dc["x_token"] or dc["x_token"] != tok:
        raise HeuresErreur("Lien invalide ou expiré.")
    if dc["x_statut"] != "attente":
        raise HeuresErreur("Cette demande a déjà été traitée (%s)."
                           % {"approuve": "approuvée", "refuse": "refusée"}.get(dc["x_statut"], dc["x_statut"]))
    if decision not in ("approuve", "refuse"):
        raise HeuresErreur("Décision invalide.")
    adm = _param(call, "maquignon.rh_admin_key")
    reponse = (ctx.get("dc_reponse") or "").strip() or \
        ("Validé par le responsable (email)" if decision == "approuve" else "Refusé par le responsable (email)")
    _a2014(call, {"dc_id": dc["id"], "dc_decision": decision,
                  "dc_reponse": reponse, "hj_k": adm})
    return {"ok": 1, "statut": decision}


# ─── 2090 : plages de paie par salarié, mémorisées dès la saisie ─────────────
def _a2090(call, ctx):
    """La page Heures admin envoie l'état des dates de TOUTES ses lignes :
    plage valide -> mémorisée, ligne vidée -> oubliée. Les salariés absents
    de l'envoi (autre société filtrée) ne sont pas touchés."""
    import json
    import re
    if not _admin_ok(call, ctx):
        raise HeuresErreur("Clé responsables requise.")
    lignes = ctx.get("lignes")
    if not isinstance(lignes, dict):
        raise HeuresErreur("Plages invalides.")
    brut = call("ir.config_parameter", "get_param", "maquignon.heures_export_exc") or "{}"
    try:
        excs = json.loads(brut)
    except Exception:
        excs = {}
    fmt = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for k, v in lignes.items():
        if not str(k).isdigit():
            continue
        k = str(k)
        if (isinstance(v, (list, tuple)) and len(v) == 2 and v[0] and v[1]
                and fmt.match(str(v[0])) and fmt.match(str(v[1])) and str(v[0]) <= str(v[1])):
            excs[k] = [str(v[0]), str(v[1])]
        else:
            excs.pop(k, None)
    call("ir.config_parameter", "set_param", "maquignon.heures_export_exc", json.dumps(excs))
    return {"ok": 1, "n": len(excs)}


HANDLERS = {2012: _a2012, 2013: _a2013, 2014: _a2014, 2020: _a2020,
            2021: _a2021, 2048: _a2048, 2050: _a2050, 2069: _a2069,
            2090: _a2090}


def executer(call, action_id, ctx):
    return HANDLERS[int(action_id)](call, ctx) or {}
