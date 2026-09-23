# -*- coding: utf-8 -*-
"""Réécrit les sections 2012 (saisie d'un jour) et 2014 (approbation d'une demande) de ocr/heures_actions.py
pour la saisie directe récup / sans solde par le salarié et les heures sup mises en récup par défaut."""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = 'ocr/heures_actions.py'
src = io.open(P, encoding='utf-8').read()

NEW_2012 = r'''# ─── 2012 : saisie des heures d'un jour + mouvements de récup ────────────────
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
                  ["x_type", "x_hs_payees"], limit=1)
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
        note = (ctx.get("hj_note") or "").strip() or False
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

'''

NEW_2014 = r'''# ─── 2014 : réponse à une demande de congés (bureau) ─────────────────────────
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


'''


def replace_section(src, start_marker, end_marker, new):
    i = src.index(start_marker)
    j = src.index(end_marker, i + 1)
    return src[:i] + new + src[j:]


# 2012 : de l'en-tête de section jusqu'au bloc « Récup : mouvements » (conservé)
src2 = replace_section(src, "# ─── 2012 : saisie des heures d'un jour", "    # --- Récup : mouvements d'heures saisis par le salarié (ou le bureau) ---", NEW_2012)
src2 = replace_section(src2, "# ─── 2014 : réponse à une demande de congés (bureau)", "# ─── 2020 : régénérer le lien personnel", NEW_2014)
assert src2.count("def _a2012(") == 1 and src2.count("def _a2014(") == 1 and src2.count("def _delta_recup(") == 1
io.open(P, "w", encoding="utf-8", newline="\n").write(src2)
import py_compile
py_compile.compile(P, doraise=True)
print("heures_actions.py réécrit :", len(src), "->", len(src2), "chars ; compilation OK")
