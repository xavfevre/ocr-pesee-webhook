# -*- coding: utf-8 -*-
"""Tableau de bord Odoo « Redevance Tuffeau (droit de fortage) » (spreadsheet.dashboard).

Reproduit l'état papier du droit de fortage : volumes facturés (m³) des produits
« Pierres Tuffeau », par produit × mois de l'exercice (avril → mars), total m³
mensuel et redevance = total × taux (18 €/m³ par défaut, paramètre système
`maquignon.fortage_taux`).

Version live : les valeurs sont des formules PIVOT.VALUE sur account.move.line
(mesure x_vol_m3, related STOCKÉ de sale_line_ids.x_studio_vol créé exprès —
l'original x_studio_vol_total, non stocké, n'est pas agrégeable en SQL), avec
un filtre global « Carrière » branché sur les étiquettes produits :
  - 34 Carrière principale (fortage)  ← valeur par défaut, périmètre du fortage
  - 35 Carrière Usseau (U)
  - 36 Carrière Coulmeau (COULMEAU)
Le recalage (endpoint /rebuild-fortage-dashboard + nocturne) ne sert qu'à
régénérer les LIGNES du tableau (produits réellement facturés sur l'exercice)
et les colonnes de l'exercice courant ; les montants, eux, sont temps réel.
"""
import json
from datetime import date

DASH_NAME = "Droit de fortage"
DASH_ID = 37                # repli si le tableau de bord est renommé dans Odoo
DASH_GROUP_ID = 11          # groupe « États mensuels »
COMPANY_ID = 1              # SARL MAQUIGNON
TAG_TUFFEAU = 19            # tag produit « Pierres Tuffeau »
TAG_PRINCIPALE = 34         # tag « Carrière principale (fortage) »
TAGS_CARRIERE = [34, 35, 36]
TAUX_DEFAUT = 18.0          # €/m³ — surchargé par ir.config_parameter maquignon.fortage_taux
MOIS_NOMS = ["Avril", "Mai", "Juin", "Juillet", "Août", "Septembre",
             "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars"]

INK = "#0E2E31"; TEAL = "#01666B"; TEALD = "#013E42"
FORMATS = {"m3": "#,##0.000", "eur": "#,##0.00[$ €]"}

DOMAIN = ["&", "&", "&",
          ["move_id.move_type", "in", ["out_invoice", "out_refund"]],
          ["move_id.state", "=", "posted"],
          ["company_id", "=", COMPANY_ID],
          ["product_id.product_tag_ids", "in", [TAG_TUFFEAU]]]


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


def tag_carrieres(call_kw):
    """Pose l'étiquette carrière sur les produits tuffeau qui n'en ont pas encore
    (règle du nommage historique : « (U) » → Usseau, « (COULMEAU) » → Coulmeau,
    sinon carrière principale). Renvoie le nombre de produits étiquetés."""
    prods = call_kw("product.product", "search_read",
                    [[["product_tag_ids", "in", [TAG_TUFFEAU]],
                      ["product_tag_ids", "not in", TAGS_CARRIERE]]],
                    {"fields": ["name"], "context": {"active_test": False}, "limit": 2000})
    for p in prods:
        n = p["name"] or ""
        tid = 35 if "(U)" in n else 36 if "(COULMEAU)" in n else TAG_PRINCIPALE
        call_kw("product.product", "write", [[p["id"]], {"product_tag_ids": [(4, tid)]}], {})
    return len(prods)


def compute(call_kw, aujourdhui=None):
    """Lignes du tableau : produits tuffeau (toutes carrières) facturés sur l'exercice."""
    debut = exercice_debut(aujourdhui)
    fin = date(debut.year + 1, 4, 1)
    taux = TAUX_DEFAUT
    raw = call_kw("ir.config_parameter", "get_param", ["maquignon.fortage_taux"], {})
    if raw:
        try:
            taux = float(str(raw).replace(",", "."))
        except ValueError:
            pass

    groups = call_kw("account.move.line", "read_group",
                     [DOMAIN + [["date", ">=", debut.isoformat()], ["date", "<", fin.isoformat()]],
                      ["x_vol_m3:sum"], ["product_id"]], {"lazy": False})
    pids = [g["product_id"][0] for g in groups if g.get("product_id") and (g.get("x_vol_m3") or 0)]
    prods = call_kw("product.product", "read", [pids], {"fields": ["default_code", "name"]}) if pids else []
    produits = {}                       # libellé → [ids de variantes]
    for p in prods:
        code = p["default_code"] or ""
        lbl = ("[%s] %s" % (code, p["name"])) if code else p["name"]
        produits.setdefault(lbl, []).append(p["id"])
    return {"debut": debut, "taux": taux, "produits": produits}


def build_doc(data):
    debut, taux, produits = data["debut"], data["taux"], data["produits"]
    staux = "%g" % taux
    cells = {}; styles = {}; formats = {}; merges = []; rows = {}
    ncol = 14                                          # A produit + 12 mois + N total
    last = col(ncol)
    mois_cle = ["%02d/%d" % (m, debut.year if m >= 4 else debut.year + 1)
                for m in list(range(4, 13)) + [1, 2, 3]]

    cells["A1"] = "Redevance Tuffeau — droit de fortage (%s €/m³)" % staux.replace(".", ",")
    cells["A2"] = ("Exercice %d-%d · volumes facturés en m³ (factures clients validées SARL MAQUIGNON) · "
                   "temps réel · choisir la carrière dans le filtre (fortage = Carrière principale)"
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

    def pv(mois, pid=None):
        prod = ',"product_id",%d' % pid if pid else ""
        return 'IFERROR(PIVOT.VALUE(1,"x_vol_m3"%s,"date:month","%s"),0)' % (prod, mois)

    r = hr
    for lbl in sorted(produits):
        r += 1
        cells["A%d" % r] = lbl
        for i, mois in enumerate(mois_cle):
            cells["%s%d" % (col(i + 2), r)] = "=" + "+".join(pv(mois, pid) for pid in produits[lbl])
        cells["%s%d" % (last, r)] = "=SUM(B%d:M%d)" % (r, r)
        styles["A%d" % r] = "prod"
        styles["B%d:%s%d" % (r, last, r)] = "val"

    rt = r + 1                                          # TOTAL m³ (respecte le filtre carrière)
    cells["A%d" % rt] = "TOTAL m³"
    for i, mois in enumerate(mois_cle):
        cells["%s%d" % (col(i + 2), rt)] = "=" + pv(mois)
    cells["%s%d" % (last, rt)] = "=SUM(B%d:M%d)" % (rt, rt)
    styles["A%d" % rt] = "totl"; styles["B%d:%s%d" % (rt, last, rt)] = "tot"
    rows[str(rt - 1)] = {"size": 24}

    rr = rt + 1                                         # redevance €
    cells["A%d" % rr] = "Redevance (× %s €/m³)" % staux.replace(".", ",")
    for i in range(12):
        c = col(i + 2)
        cells["%s%d" % (c, rr)] = "=ROUND(%s%d*%s,2)" % (c, rt, staux)
    cells["%s%d" % (last, rr)] = "=SUM(B%d:M%d)" % (rr, rr)
    styles["A%d" % rr] = "redl"; styles["B%d:%s%d" % (rr, last, rr)] = "red"
    rows[str(rr - 1)] = {"size": 26}

    rn = rr + 2
    cells["A%d" % rn] = ("ℹ️ Montants temps réel (factures validées). Le droit de fortage ne porte que sur la "
                         "Carrière principale : la ligne Redevance n'a de sens qu'avec ce filtre (par défaut). "
                         "Étiquettes « Carrière … » posées automatiquement sur les nouveaux produits tuffeau et "
                         "lignes de produits recalées chaque nuit. Taux : paramètre système « maquignon.fortage_taux ».")
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
    pivot = {"type": "ODOO", "model": "account.move.line", "name": "Volumes tuffeau facturés",
             "formulaId": "1",
             "rows": [{"fieldName": "product_id"}],
             "columns": [{"fieldName": "date", "granularity": "month"}],
             "measures": [{"id": "x_vol_m3", "fieldName": "x_vol_m3", "aggregator": "sum",
                           "userDefinedName": "m³"}],
             "domain": DOMAIN, "context": {}, "sortedColumn": None,
             "fieldMatching": {"flt_carriere": {"chain": "product_id.product_tag_ids", "type": "many2many"},
                               "flt_period": {"chain": "date", "type": "date", "offset": 0}}}
    gfilters = [{"id": "flt_carriere", "type": "relation", "label": "Carrière",
                 "modelName": "product.tag", "includeChildren": False,
                 "domainOfAllowedValues": [["id", "in", TAGS_CARRIERE]],
                 "defaultValue": {"operator": "in", "ids": [TAG_PRINCIPALE]}},
                # pas de defaultValue : « Toutes les périodes », l'exercice complet
                # reste affiché ; le filtre ne fait que restreindre les colonnes.
                {"id": "flt_period", "type": "date", "label": "Période"}]
    return {"version": "18.5.10", "sheets": [sheet], "styles": _styles(), "formats": FORMATS, "borders": {},
            "revisionId": "START_REVISION", "uniqueFigureIds": True,
            "settings": {"locale": {"name": "French / Français", "code": "fr_FR", "thousandsSeparator": " ",
                                    "decimalSeparator": ",", "dateFormat": "dd/mm/yyyy", "timeFormat": "hh:mm:ss",
                                    "formulaArgSeparator": ";", "weekStart": 1}},
            "pivots": {"1": pivot}, "pivotNextId": 2, "customTableStyles": {},
            "globalFilters": gfilters, "lists": {}, "listNextId": 1, "chartOdooMenusReferences": {}}


def rebuild(call_kw):
    """Régénère les lignes du tableau (produits de l'exercice) et l'écrit dans Odoo."""
    nouveaux = tag_carrieres(call_kw)
    data = compute(call_kw)
    doc = json.dumps(build_doc(data), ensure_ascii=False)
    json.loads(doc)
    ids = call_kw("spreadsheet.dashboard", "search", [[["name", "=", DASH_NAME]]], {})
    if not ids:
        ids = call_kw("spreadsheet.dashboard", "search", [[["id", "=", DASH_ID]]], {})
    if not ids:
        raise RuntimeError("dashboard %r introuvable" % DASH_NAME)
    call_kw("spreadsheet.dashboard", "write", [ids, {"spreadsheet_data": doc}], {})
    return {"produits": len(data["produits"]), "taux": data["taux"], "produits_etiquetes": nouveaux}
