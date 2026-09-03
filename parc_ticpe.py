# -*- coding: utf-8 -*-
"""Relevé Excel des heures de fonctionnement des engins de chantier (carrière).

Rapport « type TICPE » demandé pour les aides spécifiques aux carrières :
pour chaque engin (chargeuses, pelles, tombereaux, chariots élévateurs), les
heures de fonctionnement sur la période, calculées à partir des relevés
d'odomètre Odoo (compteurs horaires) : dernière valeur avant le début de
période → dernière valeur de la période. Servi par app.py :
GET /parc-ticpe.xlsx?k=<maquignon.parc_pdf_key>&du=YYYY-MM-DD&au=YYYY-MM-DD.
"""
import datetime
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# fleet.vehicle.model.category des engins de chantier
CATEGORIES_ENGINS = {169: "Chargeuse", 170: "Pelle", 171: "Tombereau", 172: "Chariot élévateur"}
FUEL = {"diesel": "Gazole/GNR", "gasoline": "Essence", "electric": "Électrique",
        "hybrid": "Hybride", "cng": "GNC", "lpg": "GPL", "hydrogen": "Hydrogène"}


def _d(s):
    return datetime.date.fromisoformat(str(s)[:10]) if s else None


def generer(call_kw, du, au):
    """Construit le classeur et renvoie ses octets. du/au : dates ISO."""
    vehs = call_kw("fleet.vehicle", "search_read",
                   [[["active", "=", True], ["category_id", "in", list(CATEGORIES_ENGINS)]]],
                   {"fields": ["name", "license_plate", "vin_sn", "model_year",
                               "category_id", "fuel_type"], "order": "category_id, name",
                    "limit": 500})
    odos = call_kw("fleet.vehicle.odometer", "search_read",
                   [[["vehicle_id", "in", [v["id"] for v in vehs]]]],
                   {"fields": ["vehicle_id", "date", "value", "unit"],
                    "order": "date asc, id asc", "limit": 10000})
    par_veh = {}
    for o in odos:
        par_veh.setdefault(o["vehicle_id"][0], []).append(o)

    wb = Workbook()
    ws = wb.active
    ws.title = "Heures engins"
    gras = Font(bold=True)
    titre = Font(bold=True, size=13)
    head_fill = PatternFill("solid", fgColor="0F172A")
    head_font = Font(bold=True, color="FFFFFF", size=9)
    cat_fill = PatternFill("solid", fgColor="E2E8F0")
    warn_font = Font(color="B45309", size=9)
    fine = Side(style="thin", color="CBD5E1")
    bord = Border(left=fine, right=fine, top=fine, bottom=fine)
    centre = Alignment(horizontal="center")

    ws["A1"] = "Relevé des heures de fonctionnement — engins de chantier (carrière)"
    ws["A1"].font = titre
    ws["A2"] = ("Période du %s au %s · établi le %s · source : relevés de compteurs horaires Odoo "
                "(heures = dernier relevé de la période − dernier relevé avant la période)"
                % (_d(du).strftime("%d/%m/%Y"), _d(au).strftime("%d/%m/%Y"),
                   datetime.date.today().strftime("%d/%m/%Y")))
    ws["A2"].font = Font(size=9, color="64748B")

    entetes = ["Catégorie", "Engin", "N° de châssis / série", "Code parc", "Année",
               "Carburant", "Relevé initial", "Date", "Relevé final", "Date",
               "Heures de fonctionnement", "Observation"]
    ws.append([])
    ws.append(entetes)
    lh = ws.max_row
    for c in range(1, len(entetes) + 1):
        cell = ws.cell(row=lh, column=c)
        cell.fill = head_fill
        cell.font = head_font
        cell.border = bord
        cell.alignment = centre

    ddu, dau = _d(du), _d(au)
    total, cat_tot, cat_cour, cat_row0 = 0.0, 0.0, None, None

    def ligne_total_cat(nom):
        ws.append(["", "TOTAL %s" % nom, "", "", "", "", "", "", "", "", round(cat_tot, 1), ""])
        r = ws.max_row
        for c in range(1, len(entetes) + 1):
            ws.cell(row=r, column=c).font = gras
            ws.cell(row=r, column=c).fill = cat_fill
            ws.cell(row=r, column=c).border = bord

    for v in vehs:
        cat = v["category_id"][1]
        if cat != cat_cour:
            if cat_cour is not None:
                ligne_total_cat(cat_cour)
            cat_cour, cat_tot = cat, 0.0
        rel = par_veh.get(v["id"], [])
        avant = [o for o in rel if _d(o["date"]) < ddu]
        dans = [o for o in rel if ddu <= _d(o["date"]) <= dau]
        deb = avant[-1] if avant else (dans[0] if dans else None)
        fin = dans[-1] if dans else None
        heures, obs = None, ""
        if deb and fin and fin is not deb:
            heures = round(fin["value"] - deb["value"], 1)
            if heures < 0:
                heures, obs = None, "relevés incohérents (compteur en baisse)"
            elif deb in dans:
                obs = "pas de relevé avant la période : départ = 1er relevé de la période"
        elif fin and deb is fin:
            obs = "un seul relevé sur la période — heures non calculables"
        elif not rel:
            obs = "aucun relevé de compteur"
        else:
            obs = "aucun relevé sur la période"
        nom = v["name"].split("/")[-2] if "/" in v["name"] else v["name"]
        ws.append([cat, nom, v["vin_sn"] or "", v["license_plate"] or "",
                   v["model_year"] or "", FUEL.get(v["fuel_type"], v["fuel_type"] or ""),
                   deb["value"] if deb else "", _d(deb["date"]).strftime("%d/%m/%Y") if deb else "",
                   fin["value"] if fin else "", _d(fin["date"]).strftime("%d/%m/%Y") if fin else "",
                   heures if heures is not None else "", obs])
        r = ws.max_row
        for c in range(1, len(entetes) + 1):
            ws.cell(row=r, column=c).border = bord
            if c in (7, 8, 9, 10, 11):
                ws.cell(row=r, column=c).alignment = centre
        if obs:
            ws.cell(row=r, column=12).font = warn_font
        if heures:
            cat_tot += heures
            total += heures
    if cat_cour is not None:
        ligne_total_cat(cat_cour)
    ws.append(["", "TOTAL GÉNÉRAL", "", "", "", "", "", "", "", "", round(total, 1), ""])
    r = ws.max_row
    for c in range(1, len(entetes) + 1):
        ws.cell(row=r, column=c).font = Font(bold=True, size=11)
        ws.cell(row=r, column=c).border = bord

    for col, w in zip("ABCDEFGHIJKL", (16, 30, 22, 12, 8, 12, 12, 12, 12, 12, 20, 42)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A%d" % (lh + 1)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
