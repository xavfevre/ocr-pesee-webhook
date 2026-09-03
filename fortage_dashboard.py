# -*- coding: utf-8 -*-
"""Tableau de bord Odoo « Redevance Tuffeau (droit de fortage) » (spreadsheet.dashboard).

Reproduit l'état papier du droit de fortage : volumes facturés (Vol. Total des
lignes de factures clients validées de la SARL MAQUIGNON) des produits taggés
« Pierres Tuffeau », HORS tuffeau d'Usseau « (U) » et de Coulmeau « (COULMEAU) »,
ventilés produit × mois de l'exercice (avril → mars), avec la redevance
mensuelle = total m³ × taux (18 €/m³ par défaut, modifiable via le paramètre
système `maquignon.fortage_taux`).

Le champ x_studio_vol_total (related sale_line_ids.x_studio_vol) n'est pas
agrégeable en SQL : pas de pivot live possible, le document est donc régénéré
en statique par app.py (endpoint /rebuild-fortage-dashboard + recalage
nocturne) avec un `call_kw(model, method, args, kwargs)` déjà authentifié.
"""
import json
from datetime import date

DASH_NAME = "Redevance Tuffeau (droit de fortage)"
DASH_GROUP_ID = 11          # groupe « États mensuels »
COMPANY_ID = 1              # SARL MAQUIGNON
TAG_TUFFEAU = 19            # tag produit « Pierres Tuffeau »
EXCLUS = ("(U)", "(COULMEAU)")   # tuffeau d'Usseau et de Coulmeau : hors fortage
TAUX_DEFAUT = 18.0          # €/m³ — surchargé par ir.config_parameter maquignon.fortage_taux
MOIS_NOMS = ["Avril", "Mai", "Juin", "Juillet", "Août", "Septembre",
             "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars"]

INK = "#0E2E31"; TEAL = "#01666B"; TEALD = "#013E42"
FORMATS = {"m3": "#,##0.000", "eur": "#,##0.00 €"}


def col(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _styles():
    return {
        "title": {"bold": True, "fontSize": 22, "textColor": "#FFFFFF", "fillColor": TEAL, "verticalAlign": "middle"},
        "sub": {"italic": True, "fontSize": 10, "textColor": "#BFE0E0", "fillColor": TEALD, "verticalAlign": "middle"},
        "lhdr": {"bold": True, "fontSize": 10, "textColor": "#FFFFFF", "fillColor": "#4C5A67",
                 "align": "center", "verticalAlign": "middle"},
        "prod": {"fontSize": 10, "textColor": INK, "verticalAlign": "middle"},
        "val": {"fontSize": 10, "textColor": INK, "align": "right", "verticalAlign": "middle"},
        "tot": {"bold": True, "fontSize": 11, "textColor": TEAL, "fillColor": "#E4F1F1",
                "align": "right", "verticalAlign": "middle"},
        "totl": {"bold": True, "fontSize": 11, "textColor": TEAL, "fillColor": "#E4F1F1", "verticalAlign": "middle"},
        "red": {"bold": True, "fontSize": 11, "textColor": "#B45309", "fillColor": "#FBEBD3",
                "align": "right", "verticalAlign": "middle"},
        "redl": {"bold": True, "fontSize": 11, "textColor": "#B45309", "fillColor": "#FBEBD3",
                 "verticalAlign": "middle"},
        "warn": {"italic": True, "fontSize": 9, "textColor": "#7A8791", "verticalAlign": "middle"},
    }


def exercice_debut(aujourdhui=None):
    """Premier jour de l'exercice en cours (avril → mars)."""
    d = aujourdhui or date.today()
    an = d.year if d.month >= 4 else d.year - 1
    return date(an, 4, 1)


def compute(call_kw, aujourdhui=None):
    """Volumes facturés par produit × mois de l'exercice. Renvoie le dict de build_doc."""
    debut = exercice_debut(aujourdhui)
    fin = date(debut.year + 1, 4, 1)
    taux = TAUX_DEFAUT
    raw = call_kw("ir.config_parameter", "get_param", ["maquignon.fortage_taux"], {})
    if raw:
        try:
            taux = float(str(raw).replace(",", "."))
        except ValueError:
            pass

    # périmètre produits : tag « Pierres Tuffeau », hors Usseau (U) et Coulmeau
    prods = call_kw("product.product", "search_read",
                    [[["product_tag_ids", "in", [TAG_TUFFEAU]]]],
                    {"fields": ["default_code", "name"],
                     "context": {"active_test": False}, "limit": 2000})
    scope = {}
    for p in prods:
        if any(x in (p["name"] or "") for x in EXCLUS):
            continue
        code = p["default_code"] or ""
        scope[p["id"]] = ("[%s] %s" % (code, p["name"])) if code else p["name"]

    lines = call_kw("account.move.line", "search_read",
                    [[["move_id.move_type", "in", ["out_invoice", "out_refund"]],
                      ["move_id.state", "=", "posted"],
                      ["company_id", "=", COMPANY_ID],
                      ["product_id", "in", list(scope)],
                      ["move_id.invoice_date", ">=", debut.isoformat()],
                      ["move_id.invoice_date", "<", fin.isoformat()]]],
                    {"fields": ["product_id", "x_studio_vol_total", "move_id"], "limit": 100000})
    move_ids = list({l["move_id"][0] for l in lines})
    dates = {}
    for i in range(0, len(move_ids), 1000):
        for m in call_kw("account.move", "read", [move_ids[i:i + 1000]], {"fields": ["invoice_date"]}):
            dates[m["id"]] = m["invoice_date"]

    vols = {}          # (libellé produit, index mois 0-11) → m³
    for l in lines:
        d = dates.get(l["move_id"][0])
        if not d:
            continue
        y, mo = int(d[:4]), int(d[5:7])
        idx = (y - debut.year) * 12 + mo - 4          # avril = 0 … mars = 11
        if not 0 <= idx <= 11:
            continue
        key = (scope[l["product_id"][0]], idx)
        vols[key] = vols.get(key, 0.0) + (l["x_studio_vol_total"] or 0.0)

    produits = sorted({k[0] for k in vols})
    return {"debut": debut, "taux": taux, "produits": produits, "vols": vols}


def build_doc(data):
    debut, taux, produits, vols = data["debut"], data["taux"], data["produits"], data["vols"]
    cells = {}; styles = {}; formats = {}; merges = []; rows = {}
    ncol = 14                                          # A produit + 12 mois + N total
    last = col(ncol)

    cells["A1"] = "Redevance Tuffeau — droit de fortage (%s €/m³)" % ("%g" % taux).replace(".", ",")
    cells["A2"] = ("Exercice %d-%d · volumes facturés (Vol. Total, factures clients validées SARL MAQUIGNON) · "
                   "produits « Pierres Tuffeau » hors tuffeau d'Usseau (U) et de Coulmeau · mois = date de facture"
                   % (debut.year, debut.year + 1))
    styles["A1:%s1" % last] = "title"; merges.append("A1:%s1" % last)
    styles["A2:%s2" % last] = "sub"; merges.append("A2:%s2" % last)
    rows["0"] = {"size": 44}; rows["1"] = {"size": 22}; rows["2"] = {"size": 8}

    hr = 4
    cells["A%d" % hr] = "Produit"
    for i, nom in enumerate(MOIS_NOMS):
        an = debut.year if i < 9 else debut.year + 1
        cells["%s%d" % (col(i + 2), hr)] = "%s %d" % (nom, an)
    cells["%s%d" % (last, hr)] = "TOTAL"
    styles["A%d:%s%d" % (hr, last, hr)] = "lhdr"
    rows[str(hr - 1)] = {"size": 24}

    r = hr
    for prod in produits:
        r += 1
        cells["A%d" % r] = prod
        for i in range(12):
            v = vols.get((prod, i), 0.0)
            if v:
                cells["%s%d" % (col(i + 2), r)] = round(v, 3)
        cells["%s%d" % (last, r)] = "=SUM(B%d:M%d)" % (r, r)
        styles["A%d" % r] = "prod"
        styles["B%d:%s%d" % (r, last, r)] = "val"

    rt = r + 1                                          # TOTAL m³
    cells["A%d" % rt] = "TOTAL m³"
    for i in range(12):
        c = col(i + 2)
        cells["%s%d" % (c, rt)] = "=SUM(%s%d:%s%d)" % (c, hr + 1, c, r)
    cells["%s%d" % (last, rt)] = "=SUM(B%d:M%d)" % (rt, rt)
    styles["A%d" % rt] = "totl"; styles["B%d:%s%d" % (rt, last, rt)] = "tot"
    rows[str(rt - 1)] = {"size": 24}

    rr = rt + 1                                         # redevance €
    cells["A%d" % rr] = "Redevance (× %s €/m³)" % ("%g" % taux).replace(".", ",")
    for i in range(12):
        c = col(i + 2)
        cells["%s%d" % (c, rr)] = "=ROUND(%s%d*%s,2)" % (c, rt, "%g" % taux)
    cells["%s%d" % (last, rr)] = "=SUM(B%d:M%d)" % (rr, rr)
    styles["A%d" % rr] = "redl"; styles["B%d:%s%d" % (rr, last, rr)] = "red"
    rows[str(rr - 1)] = {"size": 26}

    rn = rr + 2
    cells["A%d" % rn] = ("ℹ️ Recalculé automatiquement chaque nuit (et via le bouton de recalage). Les avoirs "
                         "tuffeau sont comptés comme sur l'état papier. Taux modifiable : paramètre système "
                         "« maquignon.fortage_taux ». Les filtres Période/Société ne s'appliquent pas.")
    styles["A%d:%s%d" % (rn, last, rn)] = "warn"; merges.append("A%d:%s%d" % (rn, last, rn))

    formats["B%d:%s%d" % (hr + 1, last, rt)] = "m3"
    formats["B%d:%s%d" % (rr, last, rr)] = "eur"

    cols = {"0": {"size": 300}}
    for i in range(1, ncol):
        cols[str(i)] = {"size": 88}
    sheet = {"id": "fortage", "name": "Redevance Tuffeau", "colNumber": ncol + 2, "rowNumber": rn + 4,
             "rows": rows, "cols": cols, "merges": merges, "cells": cells, "styles": styles, "formats": formats,
             "borders": {}, "conditionalFormats": [], "dataValidationRules": [], "figures": [], "tables": [],
             "areGridLinesVisible": False, "isVisible": True, "headerGroups": {}, "comments": {}}
    return {"version": "18.5.10", "sheets": [sheet], "styles": _styles(), "formats": FORMATS, "borders": {},
            "revisionId": "START_REVISION", "uniqueFigureIds": True,
            "settings": {"locale": {"name": "French / Français", "code": "fr_FR", "thousandsSeparator": " ",
                                    "decimalSeparator": ",", "dateFormat": "dd/mm/yyyy", "timeFormat": "hh:mm:ss",
                                    "formulaArgSeparator": ";", "weekStart": 1}},
            "pivots": {}, "pivotNextId": 1, "customTableStyles": {},
            "globalFilters": [], "lists": {}, "listNextId": 1, "chartOdooMenusReferences": {}}


def rebuild(call_kw):
    """Recalcule les volumes, régénère le document et l'écrit dans Odoo."""
    data = compute(call_kw)
    doc = json.dumps(build_doc(data), ensure_ascii=False)
    json.loads(doc)
    ids = call_kw("spreadsheet.dashboard", "search", [[["name", "=", DASH_NAME]]], {})
    if not ids:
        raise RuntimeError("dashboard %r introuvable" % DASH_NAME)
    call_kw("spreadsheet.dashboard", "write", [ids, {"spreadsheet_data": doc}], {})
    tot = round(sum(data["vols"].values()), 3)
    return {"produits": len(data["produits"]), "m3_exercice": tot, "taux": data["taux"]}
