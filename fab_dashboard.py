# -*- coding: utf-8 -*-
"""Tableau de bord Odoo « Fabrication — Commandes en cours » (spreadsheet.dashboard).

Le tableur o-spreadsheet ne sait pas redimensionner ses zones : chaque tableau
réserve un nombre de lignes fixe. Ce module régénère le document en dimensionnant
chaque tableau sur son nombre réel de commandes (+ marge), afin d'éliminer les
blancs entre tableaux. Appelé par app.py (endpoint /rebuild-fab-dashboard et
recalage quotidien) avec un `call_kw(model, method, args, kwargs)` déjà
authentifié (XML-RPC ou JSON-RPC).
"""
import json

DASH_NAME = "Fabrication — Commandes en cours"
MARGIN = 3      # lignes vides gardées sous chaque tableau (croissance intra-journée)
MIN_ROWS = 6
MAX_ROWS = 200

INK = "#0E2E31"; TEAL = "#01666B"; TEALD = "#013E42"
ACC = {"teal": ("#01666B", "#E4F1F1"), "green": ("#177245", "#E1F3E7"),
       "red": ("#B4232A", "#F9E4E5"), "amber": ("#B45309", "#FBEBD3")}
# couleurs officielles des pierres (product.category.x_studio_couleur_hex)
STONES = {"tuf": "#58A2F0", "hai": "#26CE38", "mig": "#F3B353",
          "ric": "#11F6E3", "sir": "#FEE829", "ter": "#F617F6"}
FAMS = [("TUFFEAU", "tuf", 12), ("HAIMS", "hai", 7), ("MIGNE", "mig", 8),
        ("TERVOUX", "ter", 11), ("RICHEMONT", "ric", 9), ("SIREUIL", "sir", 10)]

FORMATS = {"m3": "#,##0.00", "num": "#,##0", "d": "dd/mm/yyyy", "hide": ";;;"}

NOTR = ["x_studio_of_tranches", "=", 0]
DOM_NP = [["x_studio_fab_encours", "=", True], "&", ["x_studio_of_non_planifies", ">", 0], NOTR]
DOM_AP = ["&", ["x_studio_fab_encours", "=", True], "&", "&",
          ["x_studio_of_non_planifies", "=", 0], ["x_studio_of_non_programmes", ">", 0], NOTR]
DOM_PR = ["&", ["x_studio_fab_encours", "=", True], "&", "&",
          ["x_studio_of_non_planifies", "=", 0], ["x_studio_of_non_programmes", "=", 0], NOTR]
DOM_TR = ["&", ["x_studio_fab_encours", "=", True], ["x_studio_of_tranches", ">", 0]]
COLSL = ["date_order", "name", "partner_id", "x_studio_of_liste", "x_studio_produits_fab",
         "x_studio_pierres_faites", "x_studio_vol_of", "x_studio_vol_reste",
         "x_studio_of_non_planifies", "x_studio_date_planif"]
HDRS = ["Date cde", "N° commande", "Client", "N° OF (restants)", "Produits (familles)",
        "Pierres faites", "m³ commande", "m³ restant", "OF non plan.", "Planifié le"]
SPAN = 10


def col(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _styles():
    styles = {
        "title": {"bold": True, "fontSize": 24, "textColor": "#FFFFFF", "fillColor": TEAL, "verticalAlign": "middle"},
        "sub": {"italic": True, "fontSize": 11, "textColor": "#BFE0E0", "fillColor": TEALD, "verticalAlign": "middle"},
        "sect": {"bold": True, "fontSize": 12, "textColor": "#FFFFFF", "fillColor": TEAL, "verticalAlign": "middle"},
        "kcap": {"italic": True, "fontSize": 9, "textColor": "#7A8791", "align": "center", "verticalAlign": "middle"},
        "lhdr": {"bold": True, "fontSize": 10, "textColor": "#FFFFFF", "fillColor": "#4C5A67", "verticalAlign": "middle"},
        "warn": {"bold": True, "fontSize": 11, "textColor": "#B45309", "fillColor": "#FBEBD3", "verticalAlign": "middle"},
    }
    for n, (dk, lt) in ACC.items():
        styles["kl_%s" % n] = {"bold": True, "fontSize": 10, "textColor": "#FFFFFF", "fillColor": dk,
                               "align": "center", "verticalAlign": "middle"}
        styles["kv_%s" % n] = {"bold": True, "fontSize": 20, "textColor": dk, "fillColor": lt,
                               "align": "center", "verticalAlign": "middle"}
    for n, hx in STONES.items():
        r, g, b = int(hx[1:3], 16), int(hx[3:5], 16), int(hx[5:7], 16)
        txt = "#0F172A" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6 else "#FFFFFF"
        lt = "#%02X%02X%02X" % (int(r + (255 - r) * 0.82), int(g + (255 - g) * 0.82), int(b + (255 - b) * 0.82))
        dk = "#%02X%02X%02X" % (int(r * 0.55), int(g * 0.55), int(b * 0.55))
        styles["kl_%s" % n] = {"bold": True, "fontSize": 10, "textColor": txt, "fillColor": hx,
                               "align": "center", "verticalAlign": "middle"}
        styles["kv_%s" % n] = {"bold": True, "fontSize": 20, "textColor": dk, "fillColor": lt,
                               "align": "center", "verticalAlign": "middle"}
        styles["kp_%s" % n] = {"bold": True, "fontSize": 11, "textColor": dk, "fillColor": lt,
                               "align": "center", "verticalAlign": "middle"}
    styles["kp_teal"] = {"bold": True, "fontSize": 11, "textColor": "#01666B", "fillColor": "#E4F1F1",
                         "align": "center", "verticalAlign": "middle"}
    return styles


def _mklist(lid, dom_full):
    return {"id": lid, "model": "sale.order", "columns": COLSL, "domain": dom_full,
            "context": {}, "orderBy": [{"name": "date_order", "asc": True}],
            "name": "Commandes fab", "fieldMatching": {}}


def _pivots():
    def cnt(pid, name, dom):
        return {"type": "ODOO", "model": "sale.order", "name": name, "formulaId": pid, "rows": [], "columns": [],
                "measures": [{"id": "__count", "fieldName": "__count", "aggregator": "sum", "userDefinedName": "Nb"},
                             {"id": "x_studio_vol_reste", "fieldName": "x_studio_vol_reste",
                              "aggregator": "sum", "userDefinedName": "m³ restant"}],
                "domain": dom, "context": {}, "sortedColumn": None, "fieldMatching": {}}
    pivots = {"1": cnt("1", "Compteurs non planifiées", ["&"] + DOM_NP),
              "2": cnt("2", "Compteurs à programmer", DOM_AP),
              "3": cnt("3", "Compteurs programmées", DOM_PR)}
    for i, (nm, acc, cid) in enumerate(FAMS, start=4):
        pivots[str(i)] = {"type": "ODOO", "model": "mrp.production", "name": "À programmer %s" % nm,
                          "formulaId": str(i), "rows": [], "columns": [],
                          "measures": [{"id": "x_studio_vol_total", "fieldName": "x_studio_vol_total",
                                        "aggregator": "sum", "userDefinedName": "m³"}],
                          "domain": ["&", "&", ["state", "in", ["draft", "confirmed", "progress", "to_close"]],
                                     ["company_id", "=", 1], ["x_studio_catgorie", "child_of", [cid]]],
                          "context": {}, "sortedColumn": None, "fieldMatching": {}}
    return pivots


def build_doc(counts):
    """counts = {'np': int, 'ap': int, 'pr': int, 'tr': int} → dict o-spreadsheet."""
    cells = {}; styles = {}; formats = {}; merges = []; rows = {}; cfs = []

    def reserve(n):
        return max(min(n + MARGIN, MAX_ROWS), MIN_ROWS)

    cells["A1"] = "Fabrication — Commandes en cours"
    cells["A2"] = ("Instantané temps réel · 🔴 aucun OT affecté · 🟠 OT affectés sans date · "
                   "🟢 dates posées sur tous les OF restants · triées de la plus ancienne à la plus récente")
    styles["A1:%s1" % col(SPAN)] = "title"; merges.append("A1:%s1" % col(SPAN))
    styles["A2:%s2" % col(SPAN)] = "sub"; merges.append("A2:%s2" % col(SPAN))
    rows["0"] = {"size": 48}; rows["1"] = {"size": 24}; rows["2"] = {"size": 10}
    rows["3"] = {"size": 20}; rows["4"] = {"size": 42}; rows["5"] = {"size": 16}

    def kpi(c0, span, label, formula, accent, fmt, caption, r0=4):
        a = col(c0 + 1); b = col(c0 + span)
        for rr, txt, st in ((r0, label, "kl_%s" % accent), (r0 + 1, formula, "kv_%s" % accent),
                            (r0 + 2, caption, "kcap")):
            rng = "%s%d:%s%d" % (a, rr, b, rr)
            cells["%s%d" % (a, rr)] = txt; styles[rng] = st
            if span > 1:
                merges.append(rng)
        formats["%s%d:%s%d" % (a, r0 + 1, b, r0 + 1)] = fmt

    kpi(0, 2, "NON PLANIFIÉES", '=IFERROR(PIVOT.VALUE(1,"__count"),0)', "red", "num", "commandes")
    kpi(2, 1, "m³", '=IFERROR(PIVOT.VALUE(1,"x_studio_vol_reste"),0)', "red", "m3", "à planifier")
    kpi(3, 2, "À PROGRAMMER", '=IFERROR(PIVOT.VALUE(2,"__count"),0)', "amber", "num", "OT affectés sans date")
    kpi(5, 1, "m³", '=IFERROR(PIVOT.VALUE(2,"x_studio_vol_reste"),0)', "amber", "m3", "à programmer")
    kpi(6, 2, "PROGRAMMÉES", '=IFERROR(PIVOT.VALUE(3,"__count"),0)', "green", "num", "dates posées")
    kpi(8, 2, "m³", '=IFERROR(PIVOT.VALUE(3,"x_studio_vol_reste"),0)', "teal", "m3", "programmés")

    # volume à programmer par pierre (couleur officielle de la pierre)
    r = 8
    cells["A%d" % r] = "🪨 RESTE À PRODUIRE PAR PIERRE  ·  tous les OF non terminés : non planifiés + à programmer + programmés + tranches + production hors commandes"
    styles["A%d:%s%d" % (r, col(SPAN), r)] = "sect"; merges.append("A%d:%s%d" % (r, col(SPAN), r))
    rows[str(r - 1)] = {"size": 26}
    rows["8"] = {"size": 20}; rows["9"] = {"size": 42}; rows["10"] = {"size": 16}
    card_pos = [(0, 2), (2, 2), (4, 1), (5, 1), (6, 1), (7, 1)]
    ap_fam = counts.get("ap_fam", {})
    vcells = []
    for i, ((nm, acc, cid), (c0, sp)) in enumerate(zip(FAMS, card_pos)):
        kpi(c0, sp, nm, '=IFERROR(PIVOT.VALUE(%d,"x_studio_vol_total"),0)' % (i + 4), acc, "m3",
            "m³ à produire", r0=9)
        vcells.append("%s10" % col(c0 + 1))
    kpi(8, 2, "TOTAL", "=" + "+".join(vcells), "teal", "m3", "m³ à produire · toutes pierres", r0=9)

    # section dédiée : ventilation par pierre du bloc « à programmer »
    r = 13
    cells["A%d" % r] = ("🟠 À PROGRAMMER PAR PIERRE  ·  ventilation des commandes « OT affectés sans date » "
                        "(recalculée à chaque recalage)")
    styles["A%d:%s%d" % (r, col(SPAN), r)] = "sect"; merges.append("A%d:%s%d" % (r, col(SPAN), r))
    rows["12"] = {"size": 26}
    rows["13"] = {"size": 20}; rows["14"] = {"size": 42}; rows["15"] = {"size": 16}
    for i, ((nm, acc, cid), (c0, sp)) in enumerate(zip(FAMS, card_pos)):
        kpi(c0, sp, nm, ap_fam.get(acc, 0.0), acc, "m3", "m³ à programmer", r0=14)
    kpi(8, 2, "TOTAL", '=IFERROR(PIVOT.VALUE(2,"x_studio_vol_reste"),0)', "amber", "m3",
        "m³ à programmer · temps réel", r0=14)

    def list_block(band_row, txt, list_id, nrows):
        rng = "A%d:%s%d" % (band_row, col(SPAN), band_row)
        cells["A%d" % band_row] = txt; styles[rng] = "sect"; merges.append(rng)
        rows[str(band_row - 1)] = {"size": 28}
        hr = band_row + 1
        for i, h in enumerate(HDRS):
            cells["%s%d" % (col(i + 1), hr)] = h
        styles["A%d:%s%d" % (hr, col(SPAN), hr)] = "lhdr"
        for i in range(1, nrows + 1):
            rr = hr + i
            for j, f in enumerate(COLSL):
                cells["%s%d" % (col(j + 1), rr)] = '=IFERROR(ODOO.LIST(%s,%d,"%s"),"")' % (list_id, i, f)
        formats["A%d:A%d" % (hr + 1, hr + nrows)] = "d"
        formats["G%d:H%d" % (hr + 1, hr + nrows)] = "m3"
        formats["I%d:I%d" % (hr + 1, hr + nrows)] = "num"
        formats["J%d:J%d" % (hr + 1, hr + nrows)] = "d"
        cfs.append({"id": "cf%s" % list_id, "ranges": ["A%d:%s%d" % (hr + 1, col(SPAN), hr + nrows)],
                    "rule": {"type": "CellIsRule", "operator": "customFormula",
                             "values": ['=AND($B%d<>"",ISEVEN(ROW($B%d)))' % (hr + 1, hr + 1)],
                             "style": {"fillColor": "#EAF1F7"}}})
        return hr + nrows

    end1 = list_block(18, "🔴 COMMANDES NON PLANIFIÉES  ·  aucun OT affecté sur au moins un OF",
                      "1", reserve(counts["np"]))
    end2 = list_block(end1 + 2, "🟠 COMMANDES À PROGRAMMER  ·  OT affectés mais sans date de passage",
                      "2", reserve(counts["ap"]))
    end3 = list_block(end2 + 2, "🟢 COMMANDES PROGRAMMÉES  ·  dates posées sur les OT",
                      "3", reserve(counts["pr"]))
    end4 = list_block(end3 + 2, "🟣 COMMANDES TRANCHES  ·  au moins un OF de tranches restant (sciage)",
                      "4", reserve(counts["tr"]))
    rn = end4 + 2
    cells["A%d" % rn] = ("ℹ️ Liste mise à jour automatiquement quand les OF changent d'état ou quand les OT "
                         "sont affectés. « m³ restant » = volume des OF non terminés. Tableaux redimensionnés "
                         "chaque nuit sur le nombre réel de commandes. Les filtres Période/Société ne "
                         "s'appliquent pas (vue temps réel).")
    styles["A%d:%s%d" % (rn, col(SPAN), rn)] = "warn"; merges.append("A%d:%s%d" % (rn, col(SPAN), rn))

    cols = {"0": {"size": 92}, "1": {"size": 112}, "2": {"size": 195}, "3": {"size": 170}, "4": {"size": 205},
            "5": {"size": 95}, "6": {"size": 100}, "7": {"size": 100}, "8": {"size": 92}, "9": {"size": 92}}
    sheet = {"id": "dash", "name": "Dashboard", "colNumber": 16, "rowNumber": rn + 5,
             "rows": rows, "cols": cols, "merges": merges, "cells": cells, "styles": styles, "formats": formats,
             "borders": {}, "conditionalFormats": cfs, "dataValidationRules": [], "figures": [], "tables": [],
             "areGridLinesVisible": False, "isVisible": True, "headerGroups": {}, "comments": {}}
    lists = {"1": _mklist("1", ["&"] + DOM_NP), "2": _mklist("2", DOM_AP),
             "3": _mklist("3", DOM_PR), "4": _mklist("4", DOM_TR)}
    return {"version": "18.5.10", "sheets": [sheet], "styles": _styles(), "formats": FORMATS, "borders": {},
            "revisionId": "START_REVISION", "uniqueFigureIds": True,
            "settings": {"locale": {"name": "French / Français", "code": "fr_FR", "thousandsSeparator": " ",
                                    "decimalSeparator": ",", "dateFormat": "dd/mm/yyyy", "timeFormat": "hh:mm:ss",
                                    "formulaArgSeparator": ";", "weekStart": 1}},
            "pivots": _pivots(), "pivotNextId": 10, "customTableStyles": {},
            "globalFilters": [], "lists": lists, "listNextId": 5, "chartOdooMenusReferences": {}}


def compute_counts(call_kw):
    def n(dom_prefix):
        return call_kw("sale.order", "search_count", [dom_prefix], {})
    counts = {"np": n(["&"] + DOM_NP), "ap": n(DOM_AP), "pr": n(DOM_PR), "tr": n(DOM_TR)}
    # ventilation par pierre du volume des commandes « à programmer » (recalculée à chaque rebuild)
    orders = call_kw("sale.order", "search_read", [DOM_AP], {"fields": ["name"], "limit": 1000})
    names = [o["name"] for o in orders]
    ap_fam = {}
    for nm, acc, cid in FAMS:
        if names:
            g = call_kw("mrp.production", "read_group",
                        [["&", "&", "&", ["origin", "in", names],
                          ["state", "in", ["draft", "confirmed", "progress", "to_close"]],
                          ["company_id", "=", 1], ["x_studio_catgorie", "child_of", [cid]]],
                         ["x_studio_vol_total:sum"], []], {"lazy": False})
            ap_fam[acc] = round((g[0]["x_studio_vol_total"] or 0.0) if g else 0.0, 2)
        else:
            ap_fam[acc] = 0.0
    counts["ap_fam"] = ap_fam
    return counts


def rebuild(call_kw):
    """Recalcule les compteurs, régénère le document et l'écrit dans Odoo."""
    counts = compute_counts(call_kw)
    data = json.dumps(build_doc(counts), ensure_ascii=False)
    json.loads(data)
    ids = call_kw("spreadsheet.dashboard", "search", [[["name", "=", DASH_NAME]]], {})
    if not ids:
        raise RuntimeError("dashboard %r introuvable" % DASH_NAME)
    call_kw("spreadsheet.dashboard", "write", [ids, {"spreadsheet_data": data}], {})
    return counts
