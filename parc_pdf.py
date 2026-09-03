# -*- coding: utf-8 -*-
"""PDF récapitulatif du parc automobile — contrôles obligatoires.

Reprend les données et les règles de la page Odoo /parc-controles (vue 7968) :
dernière date = dernier service Fleet « Terminé » du type lié, sinon la date
saisie ; échéance = date + périodicité, bornée par la règle du 1er contrôle
technique à 4 ans après immatriculation (CT léger et antipollution VUL).
Servi par app.py : GET /parc-pdf?k=<maquignon.parc_pdf_key>.
"""
import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CATN = {"vp": "Voitures", "vul": "Utilitaires", "pl_porteur": "Camions porteurs",
        "pl_tracteur": "Tracteurs routiers", "remorque": "Remorques",
        "terrassement": "Engins de terrassement", "levage": "Levage"}
FOND = {"retard": "#fecaca", "proche": "#fde68a", "ok": "#bbf7d0",
        "vide": "#e2e8f0", "cv": "#fecaca"}


def _d(s):
    return datetime.date.fromisoformat(str(s)[:10]) if s else None


def _echeance(dd, acq, tname, per, today):
    p = dd + datetime.timedelta(days=30 * per) if dd else None
    m4 = None
    if acq and (("léger" in tname) or ("antipollution" in tname.lower())):
        m4 = acq + datetime.timedelta(days=1461)
    if p and m4:
        return max(p, m4)
    if p:
        return p
    return m4 if (m4 and m4 >= today) else None


def generer(call_kw):
    """Construit le PDF et renvoie ses octets."""
    today = datetime.date.today()
    rows = call_kw("x_controle_vehicule", "search_read", [[]],
                   {"fields": ["x_vehicule_id", "x_type_id", "x_derniere_date",
                               "x_cv_limite", "x_categorie"], "limit": 2000,
                    "order": "x_vehicule_id"})
    types = {t["id"]: t for t in call_kw(
        "x_type_controle", "search_read", [[]],
        {"fields": ["x_name", "x_periodicite_mois", "x_fleet_service_type_id"]})}
    vehs = call_kw("fleet.vehicle", "search_read", [[["active", "=", True]]],
                   {"fields": ["name", "license_plate", "acquisition_date"],
                    "order": "name", "limit": 500})
    logs = call_kw("fleet.vehicle.log.services", "search_read",
                   [[["state", "=", "done"]]],
                   {"fields": ["vehicle_id", "service_type_id", "date"], "limit": 10000})
    last_log = {}
    for lg in logs:
        if lg["date"] and lg["service_type_id"]:
            k = (lg["vehicle_id"][0], lg["service_type_id"][0])
            dt = _d(lg["date"])
            if k not in last_log or dt > last_log[k]:
                last_log[k] = dt
    by_veh, cat_veh = {}, {}
    for r in rows:
        by_veh.setdefault(r["x_vehicule_id"][0], {})[r["x_type_id"][0]] = r
        cat_veh[r["x_vehicule_id"][0]] = r["x_categorie"]

    st = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=st["Title"], fontSize=15, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=st["Normal"], fontSize=8.5,
                         textColor=colors.HexColor("#64748b"))
    hcat = ParagraphStyle("hcat", parent=st["Heading2"], fontSize=11, spaceBefore=8,
                          spaceAfter=3, textColor=colors.HexColor("#15324f"))
    cell = ParagraphStyle("cell", parent=st["Normal"], fontSize=7.6, leading=9)

    elts = [Paragraph("Parc automobile — Récapitulatif des contrôles obligatoires", h1),
            Paragraph("État au %s · saisi = date du dernier contrôle réalisé → échéance · "
                      "MANQUANT = aucune saisie · règle appliquée : 1er contrôle technique "
                      "4 ans après immatriculation (véhicules récents)" % today.strftime("%d/%m/%Y"),
                      sub), Spacer(1, 4 * mm)]
    stats = {"retard": 0, "proche": 0, "ok": 0, "vide": 0}
    data, fonds = None, []

    def flush():
        nonlocal data
        if data and len(data) > 1:
            t = Table(data, colWidths=[52 * mm, 62 * mm, 26 * mm, 22 * mm, 24 * mm,
                                       24 * mm, 55 * mm], repeatRows=1)
            sty = [("FONTSIZE", (0, 0), (-1, -1), 7.6),
                   ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                   ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                   ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                   ("TOPPADDING", (0, 0), (-1, -1), 2),
                   ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
            for i, fl in enumerate(fonds):
                if fl:
                    sty.append(("BACKGROUND", (3, i + 1), (5, i + 1), colors.HexColor(fl)))
            t.setStyle(TableStyle(sty))
            elts.append(t)
        data = None

    cats_seen = object()
    for v in sorted(vehs, key=lambda x: (cat_veh.get(x["id"], "zz"), x["name"])):
        vid = v["id"]
        if vid not in by_veh:
            continue
        cat = cat_veh.get(vid, "")
        if cat != cats_seen:
            flush()
            fonds = []
            elts.append(Paragraph(CATN.get(cat, cat or "Autres"), hcat))
            data = [["Véhicule", "Contrôle", "Dernier fait", "Échéance", "État",
                     "Contre-visite", "Observation"]]
            cats_seen = cat
        acq = _d(v["acquisition_date"])
        for tid, r in sorted(by_veh[vid].items()):
            ty = types[tid]
            fst = ty["x_fleet_service_type_id"] and ty["x_fleet_service_type_id"][0]
            dd = (last_log.get((vid, fst)) if fst else None) or _d(r["x_derniere_date"])
            ech = _echeance(dd, acq, ty["x_name"], ty["x_periodicite_mois"], today)
            cv = _d(r["x_cv_limite"])
            if cv:
                etat, lab, obs = "cv", "CONTRE-VISITE", "avant le %s" % cv.strftime("%d/%m/%Y")
            elif not ech:
                etat, lab, obs = "vide", "MANQUANT", "à renseigner"
            elif ech < today:
                etat, lab, obs = "retard", "EN RETARD", "depuis %d j" % (today - ech).days
            elif (ech - today).days <= 30:
                etat, lab, obs = "proche", "SOUS 30 J", "dans %d j" % (ech - today).days
            else:
                etat, lab, obs = "ok", "À JOUR", ""
            if not dd and ech:
                obs = "1er contrôle (véhicule récent, jamais saisi)"
            stats["vide" if etat == "vide" else ("retard" if etat in ("retard", "cv") else etat)] += 1
            nom = v["name"].split("/")[-2] if "/" in v["name"] else v["name"]
            data.append([Paragraph("<b>%s — %s</b>" % (nom, v["license_plate"] or ""), cell),
                         Paragraph(ty["x_name"], cell),
                         dd.strftime("%d/%m/%Y") if dd else "—",
                         ech.strftime("%d/%m/%Y") if ech else "—",
                         lab, cv.strftime("%d/%m/%Y") if cv else "", Paragraph(obs, cell)])
            fonds.append(FOND.get(etat))
    flush()
    elts.insert(2, Paragraph(
        "<b>%d</b> contrôles suivis · <b>%d</b> en retard/contre-visite · <b>%d</b> sous 30 jours "
        "· <b>%d</b> à jour · <b>%d</b> manquants (à renseigner)"
        % (sum(stats.values()), stats["retard"], stats["proche"], stats["ok"], stats["vide"]), sub))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=10 * mm, bottomMargin=10 * mm,
                      leftMargin=10 * mm, rightMargin=10 * mm).build(elts)
    return buf.getvalue()
