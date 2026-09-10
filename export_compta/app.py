# -*- coding: utf-8 -*-
"""Export comptable Sage — multi-sociétés (même esprit que la page /protec/ebp).

Remplace les actions serveur Odoo 1459 (« Export journal pour logiciel compta
extérieur ») et 1671 (« Export journal Caisse pour Sage ») pour pouvoir
supprimer ce code payant d'Odoo. Formats de fichiers STRICTEMENT identiques
aux exports historiques validés par le cabinet (CSV `;`, cp1252) :
- ventes / banque : écritures groupées par (compte, analytique) — logique 1459 ;
- caisse : ligne à ligne (tickets comptoir) — logique 1671.

Page /export-compta : société + mois → aperçu par journal (pièces, lignes,
total débit) puis téléchargement par journal ou ZIP complet. Le ZIP contient
aussi `nouveaux_clients_*.txt` : les clients des écritures exportées jamais
transmis à Sage (`x_sage_envoye_le` vide), à importer dans le dossier — avec
option pour les marquer transmis.

Jeton : ir.config_parameter `maquignon.compta_key` (?token=...).
"""
import calendar
import re
import io
import os
import zipfile
from datetime import date

import xmlrpc.client
from flask import Blueprint, request, abort, Response

bp = Blueprint("export_compta", __name__)

ODOO_URL = os.environ.get("ODOO_URL", "")
ODOO_DB = os.environ.get("ODOO_DB", "")
ODOO_USER = os.environ.get("ODOO_USER", "")
ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "")

import threading as _threading
_tls = _threading.local()


def _cn():
    """Connexion XML-RPC propre à chaque thread (un ServerProxy partagé n'est pas sûr en parallèle)."""
    if not hasattr(_tls, "c"):
        _tls.c = {}
    return _tls.c


def _q(model, method, *params, **kw):
    _conn = _cn()
    if "uid" not in _conn:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
        _conn["uid"] = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        _conn["models"] = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
    return _conn["models"].execute_kw(ODOO_DB, _conn["uid"], ODOO_PASSWORD,
                                      model, method, list(params), kw)


def _check_token():
    import hmac
    tok = request.args.get("token", "") or request.form.get("token", "")
    ref = _q("ir.config_parameter", "get_param", "maquignon.compta_key") or ""
    if not (tok and ref and hmac.compare_digest(tok, ref)):
        abort(403)


ENTETE = ("Numéro de pièce;Numéro facture;Code journal;Date facture;Code client;"
          "Référence client;Nom client;Code compte;Libellé compte;Date échéance;"
          "Débit;Crédit;URL Facture;Plan;Analytique;Type écriture")


def _mois_bornes(mois):
    y, mo = int(mois[:4]), int(mois[5:7])
    return (f"{y:04d}-{mo:02d}-01", f"{y:04d}-{mo:02d}-{calendar.monthrange(y, mo)[1]:02d}")


def _periode(args):
    """Bornes (du, au) : plage libre du/au (YYYY-MM-DD, prioritaire — rapprochements
    en cours de mois) sinon le mois complet. Renvoie aussi le libellé affiché."""
    import re
    du, au = (args.get("du") or "").strip(), (args.get("au") or "").strip()
    if (re.match(r"^\d{4}-\d{2}-\d{2}$", du) and re.match(r"^\d{4}-\d{2}-\d{2}$", au)
            and du <= au):
        return du, au, "du %s au %s" % (du, au)
    mois = args.get("mois") or ""
    du, au = _mois_bornes(mois)
    return du, au, mois


def _ddmmyy(iso):
    return (iso[8:10] + iso[5:7] + iso[2:4]) if iso else ""


def _piece(numero):
    chiffres = "".join(c for c in (numero or "") if c.isdigit())
    return chiffres[-7:] if chiffres else ""


def _referentiels(line_rows, comp):
    acc_ids = list({l["account_id"][0] for l in line_rows if l["account_id"]})
    part_ids = list({l["partner_id"][0] for l in line_rows if l["partner_id"]})
    ana_ids = set()
    for l in line_rows:
        for k in (l.get("analytic_distribution") or {}):
            for part in str(k).split(","):
                if part.strip().isdigit():
                    ana_ids.add(int(part))
    # account.account.code est company-dependent : sans le contexte de la société
    # exportée, les comptes des autres sociétés ressortent sans code et toutes
    # leurs lignes sont écartées (fichier vide pour Haims/Châtel).
    comptes = {a["id"]: a for a in _q("account.account", "read", acc_ids,
                                      fields=["code", "name"],
                                      context={"allowed_company_ids": [comp]})} if acc_ids else {}
    partenaires = {p["id"]: p for p in _q("res.partner", "read", part_ids,
                                          fields=["ref", "name"])} if part_ids else {}
    # sections Sage uniquement : le plan « Project » (id 1 — Demande de transport,
    # Interne, Service sur site) est de l'analytique opérationnelle des modules
    # projet/transport et ne doit jamais partir vers Sage.
    analytiques = {a["id"]: a["name"]
                   for a in _q("account.analytic.account", "read", list(ana_ids),
                               fields=["name", "plan_id"])
                   if a["plan_id"] and a["plan_id"][0] != PLAN_PROJECT} if ana_ids else {}
    return comptes, partenaires, analytiques


PLAN_PROJECT = 1


def _ana_libelle(line, analytiques):
    """Sections Sage de la ligne. Les clés composées (« 13,2 » = section Sage +
    compte du plan Project) sont décomposées pour garder la section — l'action
    historique les faisait échouer et exportait un analytique vide."""
    dist = line.get("analytic_distribution") or {}
    ids, vus = [], set()
    for k in dist:
        for part in str(k).split(","):
            part = part.strip()
            if part.isdigit() and int(part) not in vus:
                vus.add(int(part))
                ids.append(int(part))
    return " | ".join(n for n in (analytiques.get(i, "") for i in ids) if n)


def _sections_pct(line, analytiques):
    """{id section Sage: %} de la ligne (clés composées décomposées : chaque
    section d'une clé reçoit le % entier de la clé, comme dans Odoo)."""
    out = {}
    for k, pct in (line.get("analytic_distribution") or {}).items():
        for part in str(k).split(","):
            part = part.strip()
            if part.isdigit() and int(part) in analytiques:
                out[int(part)] = out.get(int(part), 0.0) + (pct or 0.0)
    return out


def _lignes_a(base, analytiques, sections, tot_debit, tot_credit):
    """Lignes analytiques « A » : une par section Sage, montants au prorata des %.
    Une seule section = montants du groupe tels quels (comportement historique) ;
    plusieurs sections = ventilation, la dernière absorbe l'écart d'arrondi.
    base(debit, credit, analytique) rend la ligne sans le type d'écriture final."""
    ids = sorted(sections)
    lignes, cum_d, cum_c = [], 0.0, 0.0
    for i, sid in enumerate(ids):
        sd, sc = sections[sid]
        if i == len(ids) - 1:
            sd, sc = tot_debit - cum_d, tot_credit - cum_c
        else:
            sd, sc = round(sd, 2), round(sc, 2)
            cum_d += sd
            cum_c += sc
        if sd > 0 and sc > 0:
            legs = [(sd, 0), (0, sc)]
        elif sd or sc:
            legs = [(sd, sc)]
        else:
            continue
        for d, c in legs:
            lignes.append(base(d, c, analytiques[sid]) + "A")
    return lignes


def _export_ventes(journal, du, au, base_url, clients_vus, comp, move_ids=None, sortis=None, inclure=False):
    """Format action 1459 : écritures groupées par (compte, analytique).
    move_ids : restreint aux pièces données (export des écritures rétroactives)."""
    dom = [("journal_id", "=", journal["id"]), ("state", "=", "posted"),
           ("date", ">=", du), ("date", "<=", au)]
    if move_ids is not None:
        dom.append(("id", "in", move_ids))
    if not inclure:
        dom.append(("x_sage_envoye_le", "=", False))   # garde-fou : jamais deux fois la même pièce
    moves = _q("account.move", "search_read", dom,
               fields=["name", "date", "invoice_date_due"], limit=0)  # ordre par défaut d'Odoo, comme l'action 1459
    if not moves:
        return None
    mids = [m["id"] for m in moves]
    if sortis is not None:
        sortis.update(mids)
    lines = _q("account.move.line", "search_read", [("move_id", "in", mids)],
               fields=["move_id", "account_id", "debit", "credit", "partner_id",
                       "ref", "analytic_distribution"], limit=0, order="id asc")
    comptes, partenaires, analytiques = _referentiels(lines, comp)
    par_move = {}
    for l in lines:
        par_move.setdefault(l["move_id"][0], []).append(l)

    out = [ENTETE]
    for m in moves:
        numero = m["name"] or ""
        piece = _piece(numero)
        d_fac, d_ech = _ddmmyy(m["date"]), _ddmmyy(m["invoice_date_due"])
        groupes = {}
        for l in par_move.get(m["id"], []):
            debit, credit = l["debit"] or 0, l["credit"] or 0
            if debit == 0 and credit == 0:
                continue
            compte = comptes.get(l["account_id"] and l["account_id"][0]) or {}
            code_compte = compte.get("code") or ""
            if not code_compte:
                continue
            ana = _ana_libelle(l, analytiques)
            cle = (code_compte, ana)
            if cle not in groupes:
                part = partenaires.get(l["partner_id"] and l["partner_id"][0]) or {}
                if code_compte.startswith("411"):
                    code_client = part.get("ref") or ""
                    url = "%s/report/pdf/account.report_invoice/%s" % (base_url, m["id"])
                    if l["partner_id"]:
                        clients_vus.add(l["partner_id"][0])
                else:
                    code_client, url = "", ""
                groupes[cle] = {"code_client": code_client, "ref_ligne": l["ref"] or "",
                                "nom": part.get("name") or "", "url": url,
                                "debit": 0, "credit": 0, "sections": {}}
            groupes[cle]["debit"] += debit
            groupes[cle]["credit"] += credit
            for sid, pct in _sections_pct(l, analytiques).items():
                s = groupes[cle]["sections"].setdefault(sid, [0.0, 0.0])
                s[0] += debit * pct / 100.0
                s[1] += credit * pct / 100.0
        for (code_compte, ana), g in groupes.items():
            libelle = "%s %s" % (numero, g["nom"])
            if g["debit"] > 0 and g["credit"] > 0:
                montants = [(g["debit"], 0), (0, g["credit"])]
            else:
                montants = [(g["debit"], g["credit"])]
            def base(d, c, a, g=g, code_compte=code_compte, libelle=libelle):
                return "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;" % (
                    piece, numero, journal["code"] or "", d_fac,
                    g["code_client"], g["ref_ligne"], g["nom"],
                    code_compte, libelle, d_ech, d, c, g["url"], a)
            for debit, credit in montants:
                out.append(base(debit, credit, ana) + "G")
            if ana and code_compte.startswith("7"):
                out.extend(_lignes_a(base, analytiques, g["sections"],
                                     round(g["debit"], 2), round(g["credit"], 2)))
    return "\n".join(out)


def _export_caisse(journal, du, au, clients_vus, comp, move_ids=None, sortis=None, inclure=False):
    """Format action 1671 : ligne à ligne (tickets comptoir)."""
    dom = [("journal_id", "=", journal["id"]), ("parent_state", "=", "posted"),
           ("date", ">=", du), ("date", "<=", au)]
    if move_ids is not None:
        dom.append(("move_id", "in", move_ids))
    if not inclure:
        dom.append(("move_id.x_sage_envoye_le", "=", False))
    lines = _q("account.move.line", "search_read", dom,
               fields=["move_id", "date", "account_id", "debit", "credit", "partner_id",
                       "name", "analytic_distribution"], limit=0,
               order="date asc, move_id asc, id asc")
    if not lines:
        return None
    mids = list({l["move_id"][0] for l in lines})
    if sortis is not None:
        sortis.update(mids)
    moves = {m["id"]: m for m in _q("account.move", "read", mids,
                                    fields=["name", "invoice_date_due", "partner_id"])}
    comptes, partenaires, analytiques = _referentiels(lines, comp)
    extra = {m["partner_id"][0] for m in moves.values() if m["partner_id"]} - set(partenaires)
    if extra:
        for p in _q("res.partner", "read", list(extra), fields=["ref", "name"]):
            partenaires[p["id"]] = p
    soeurs = {}
    for l in lines:
        soeurs.setdefault(l["move_id"][0], []).append(l)

    out = [ENTETE]
    for l in lines:
        m = moves[l["move_id"][0]]
        numero = m["name"] or ""
        piece = _piece(numero)
        d_fac, d_ech = _ddmmyy(l["date"]), _ddmmyy(m["invoice_date_due"])
        compte = comptes.get(l["account_id"] and l["account_id"][0]) or {}
        code_compte = compte.get("code") or ""
        ana = _ana_libelle(l, analytiques)
        part = partenaires.get(l["partner_id"] and l["partner_id"][0]) or {}
        if code_compte.startswith("411"):
            code_client = part.get("ref") or ""
            nom = (part.get("name") or "").replace(";", ",")
            if l["partner_id"]:
                clients_vus.add(l["partner_id"][0])
        else:
            code_client, nom = "", ""
        libelle = (l["name"] or "").replace(";", ",")
        if not libelle:
            repli = part or (partenaires.get(m["partner_id"] and m["partner_id"][0]) or {})
            if not repli:
                for sib in soeurs.get(l["move_id"][0], []):
                    if sib["partner_id"]:
                        repli = partenaires.get(sib["partner_id"][0]) or {}
                        break
            libelle = (repli.get("name") or "").replace(";", ",")
        debit, credit = l["debit"] or 0, l["credit"] or 0

        def base(d, c, a, code_client=code_client, nom=nom,
                 code_compte=code_compte, libelle=libelle, numero=numero,
                 piece=piece, d_fac=d_fac, d_ech=d_ech):
            return "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;;1;%s;" % (
                piece, numero, journal["code"] or "", d_fac, code_client, numero,
                nom, code_compte, libelle, d_ech, d, c, a)
        out.append(base(debit, credit, ana) + "G")
        if ana and code_compte.startswith("7"):
            sections = {sid: [debit * pct / 100.0, credit * pct / 100.0]
                        for sid, pct in _sections_pct(l, analytiques).items()}
            out.extend(_lignes_a(base, analytiques, sections,
                                 round(debit, 2), round(credit, 2)))
    return "\n".join(out)


def _nouveaux_clients(clients_vus, marquer):
    """Clients des écritures exportées jamais transmis à Sage (fiches mères)."""
    if not clients_vus:
        return None, 0
    ps = _q("res.partner", "read", list(clients_vus),
            fields=["ref", "name", "street", "street2", "zip", "city", "vat",
                    "company_registry", "email", "phone", "x_sage_envoye_le", "parent_id"])
    nouveaux = [p for p in ps if p["ref"] and not p["x_sage_envoye_le"] and not p["parent_id"]]
    if not nouveaux:
        return None, 0
    out = ["Code Client;Intitulé Client;Adresse;Code Postal;Ville;Siret;"
           "N° TVA intracommunautaire;Email;Téléphone"]
    for p in sorted(nouveaux, key=lambda x: x["ref"]):
        adresse = " ".join(x for x in (p["street"], p["street2"]) if x)
        out.append(";".join((v or "").replace(";", ",") for v in (
            p["ref"], p["name"], adresse, p["zip"], p["city"],
            p["company_registry"], p["vat"], p["email"], p["phone"])))
    if marquer:
        _q("res.partner", "write", [p["id"] for p in nouveaux],
           {"x_sage_envoye_le": date.today().isoformat()})
    return "\n".join(out), len(nouveaux)


def _journaux(comp):
    """Journaux à exporter : ventes/banque/caisse + journaux de session PoS
    (ex. « Cloture CAISSE » Châtel, type OD) — ces derniers au format caisse."""
    # pour l'instant le cabinet n'importe que les VENTES et la CAISSE
    js = _q("account.journal", "search_read",
            [("company_id", "=", comp), ("type", "in", ["sale", "cash"])],
            fields=["name", "code", "type"], order="type, id",
            context={"lang": "fr_FR"})
    pos = _q("pos.config", "search_read", [("company_id", "=", comp)],
             fields=["journal_id"])
    pos_ids = {p["journal_id"][0] for p in pos if p["journal_id"]}
    deja = {j["id"] for j in js}
    manquants = [i for i in pos_ids if i not in deja]
    if manquants:
        js += _q("account.journal", "read", manquants, fields=["name", "code", "type"],
                 context={"lang": "fr_FR"})
    for j in js:
        j["format_caisse"] = j["type"] == "cash" or j["id"] in pos_ids
        if j["id"] in pos_ids:
            j["explication"] = "Ventes comptoir du point de vente (tickets, TVA, REP) — le fichier « caisse » historique"
        elif j["type"] == "cash":
            j["explication"] = "Mouvements d'espèces : encaissements en liquide, remises en banque"
        elif j["type"] == "sale":
            j["explication"] = "Factures et avoirs clients (hors comptoir)"
        else:
            j["explication"] = "Relevés bancaires"
    # journaux « à encaisser » (CB / chèques, compte 5112*) : des banques au sens
    # Odoo, mais exportés vers Sage comme le faisait l'action historique 1459
    # (ex. « CB à encaisser » / « Chèque à encaisser » de Châtel). Les vraies
    # banques (512*) restent hors export.
    banques = _q("account.journal", "search_read",
                 [("company_id", "=", comp), ("type", "=", "bank")],
                 fields=["name", "code", "type", "default_account_id"], order="id",
                 context={"lang": "fr_FR"})
    acc_ids = [b["default_account_id"][0] for b in banques if b["default_account_id"]]
    codes = {a["id"]: a["code"] or "" for a in _q(
        "account.account", "read", acc_ids, fields=["code"],
        context={"allowed_company_ids": [comp]})} if acc_ids else {}
    for b in banques:
        aid = b["default_account_id"] and b["default_account_id"][0]
        if codes.get(aid, "").startswith("5112"):
            b["format_caisse"] = False
            b["explication"] = "Encaissements différés (CB / chèques à encaisser) — format ventes, comme l'export historique"
            js.append(b)
    return js


def _apercu(comp, du, au, journaux):
    """Une requête : pièces / lignes / total débit par journal + nouveaux clients."""
    lines = _q("account.move.line", "search_read",
               [("company_id", "=", comp), ("parent_state", "=", "posted"),
                 ("date", ">=", du), ("date", "<=", au),
                 ("journal_id", "in", [j["id"] for j in journaux])],
               fields=["journal_id", "move_id", "debit", "account_id", "partner_id"],
               limit=0)
    agg, clients = {}, set()
    deja = set(_q("account.move", "search", [("id", "in", list({l["move_id"][0] for l in lines})),
                                                ("x_sage_envoye_le", "!=", False)])) if lines else set()
    acc_ids = list({l["account_id"][0] for l in lines if l["account_id"]})
    codes = {}
    for i in range(0, len(acc_ids), 800):
        for a in _q("account.account", "read", acc_ids[i:i + 800], fields=["code"],
                    context={"allowed_company_ids": [comp]}):
            codes[a["id"]] = a["code"] or ""
    for l in lines:
        jid = l["journal_id"][0]
        a = agg.setdefault(jid, {"nlignes": 0, "debit": 0.0, "pieces": set(), "deja": set()})
        if l["move_id"][0] in deja:
            a["deja"].add(l["move_id"][0])
        a["nlignes"] += 1
        a["debit"] += l["debit"] or 0
        a["pieces"].add(l["move_id"][0])
        if l["partner_id"] and codes.get(l["account_id"] and l["account_id"][0], "").startswith("411"):
            clients.add(l["partner_id"][0])
    nouveaux = []
    if clients:
        ps = _q("res.partner", "read", list(clients),
                fields=["ref", "name", "x_sage_envoye_le", "parent_id"])
        nouveaux = sorted((p["ref"], p["name"]) for p in ps
                          if p["ref"] and not p["x_sage_envoye_le"] and not p["parent_id"])
    return agg, nouveaux


def _controle_analytique(comp, du, au, journaux):
    """Contrôle avant export (MAQUIGNON) : lignes de produits sur comptes 7*
    sans section analytique Sage (plans hors « Project »). Renvoie une liste
    [(pièce, compte, montant)] agrégée par pièce + compte."""
    if comp != 1 or not journaux:
        return []
    lines = _q("account.move.line", "search_read",
               [("company_id", "=", comp), ("parent_state", "=", "posted"),
                 ("date", ">=", du), ("date", "<=", au),
                 ("journal_id", "in", [j["id"] for j in journaux]),
                 ("display_type", "=", "product")],
               fields=["move_name", "account_id", "analytic_distribution",
                       "debit", "credit"], limit=0)
    acc_ids = list({l["account_id"][0] for l in lines if l["account_id"]})
    codes = {}
    for i in range(0, len(acc_ids), 800):
        for a in _q("account.account", "read", acc_ids[i:i + 800], fields=["code"],
                    context={"allowed_company_ids": [comp]}):
            codes[a["id"]] = a["code"] or ""
    sage_ids = {a["id"] for a in _q("account.analytic.account", "search_read",
                                    [("plan_id", "!=", PLAN_PROJECT)], fields=["id"], limit=0)}
    manq = {}
    for l in lines:
        code = codes.get(l["account_id"] and l["account_id"][0], "")
        if not code.startswith("7"):
            continue
        ids = {int(x) for k in (l.get("analytic_distribution") or {})
               for x in str(k).split(",") if x.strip().isdigit()}
        if ids & sage_ids:
            continue
        cle = (l["move_name"] or "?", code)
        manq[cle] = manq.get(cle, 0.0) + (l["credit"] or 0) - (l["debit"] or 0)
    return sorted((p, c, m) for (p, c), m in manq.items())


def _dfr(iso):
    """2026-08-31 -> 31/08/2026 ; « 2026-08-31 14:22 » -> 31/08/2026 14:22."""
    if not iso or len(iso) < 10:
        return iso or ""
    return "%s/%s/%s%s" % (iso[8:10], iso[5:7], iso[0:4], iso[10:])


def _maintenant_paris():
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _histo_add(comp, libelle_journal, du, au):
    """Journalise chaque téléchargement (fichier .txt ou ZIP) — 60 derniers."""
    import json
    key = "maquignon.export_compta_histo_%s" % comp
    try:
        h = json.loads(_q("ir.config_parameter", "get_param", key) or "[]")
    except ValueError:
        h = []
    h.insert(0, {"j": libelle_journal, "du": du, "au": au, "fait": _maintenant_paris()})
    _q("ir.config_parameter", "set_param", key, json.dumps(h[:60], ensure_ascii=False))


def _dernier_maj(comp, du, au):
    """Avance le repère « dernier export » (préremplissage du lendemain + alerte
    rétroactive). Horodatage UTC pour comparaison avec create_date d'Odoo."""
    from datetime import datetime
    key = "maquignon.export_compta_dernier_%s" % comp
    cur = _q("ir.config_parameter", "get_param", key) or ""
    cur_au = cur.split("|")[1] if cur.count("|") == 2 else ""
    if au > cur_au:
        _q("ir.config_parameter", "set_param", key,
           "%s|%s|%s" % (du, au, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))


def _pieces_retro(comp, journaux):
    """Pièces datées dans la période déjà exportée mais saisies après le dernier
    export. Renvoie (d_au, d_fait, [moves]) ou (None, None, [])."""
    dernier = _q("ir.config_parameter", "get_param",
                 "maquignon.export_compta_dernier_%s" % comp) or ""
    if dernier.count("|") != 2:
        return None, None, []
    d_du, d_au, d_fait = dernier.split("|")
    if not (d_au and d_fait):
        return None, None, []
    moves = _q("account.move", "search_read",
               [("company_id", "=", comp), ("state", "=", "posted"),
                ("journal_id", "in", [j["id"] for j in journaux]),
                ("date", "<=", d_au), ("create_date", ">", d_fait)],
               fields=["name", "date", "journal_id", "amount_total"], limit=200,
               context={"lang": "fr_FR"}, order="date asc, name asc")
    return d_au, d_fait, moves


TYPES = {"sale": "Ventes", "bank": "Banque", "cash": "Caisse"}

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Export comptable Sage</title><style>
:root{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f1f5f9;}
*{box-sizing:border-box;}
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);margin:0;padding:22px 16px 40px;color:var(--ink);}
.wrap{max-width:980px;margin:0 auto;}
.head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:14px;}
h1{font-size:22px;margin:0;letter-spacing:-.2px;}
p.sub{color:var(--mut);font-size:13px;margin:4px 0 0;max-width:640px;line-height:1.45;}
.tools{display:flex;gap:8px;flex-wrap:wrap;}
.tools a{font-size:12.5px;font-weight:700;color:var(--ink);background:#fff;border:1.5px solid var(--line);border-radius:9px;padding:8px 12px;text-decoration:none;}
.tools a:hover{border-color:#94a3b8;}
.card{background:#fff;border-radius:14px;box-shadow:0 1px 5px rgba(15,23,42,.08);padding:18px 20px;margin-bottom:14px;}
form.bar{display:flex;gap:14px;flex-wrap:wrap;align-items:end;}
form.bar label{display:block;font-weight:700;font-size:12px;color:var(--mut);margin-bottom:4px;text-transform:uppercase;letter-spacing:.4px;}
select,input[type=date],input[type=text]{padding:9px 11px;border:1.5px solid #cbd5e1;border-radius:9px;font-size:14px;font-weight:600;color:var(--ink);background:#fff;}
select{min-width:240px;}
.status{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin-top:14px;}
.stat{border:1.5px solid var(--line);border-radius:11px;padding:10px 13px;}
.stat .k{font-size:11.5px;font-weight:700;color:var(--mut);text-transform:uppercase;letter-spacing:.4px;}
.stat .v{font-size:17px;font-weight:800;margin-top:2px;}
.stat .s{font-size:12px;color:var(--mut);margin-top:2px;}
.stat.lock{background:var(--ink);color:#fff;border-color:var(--ink);}
.stat.lock .k,.stat.lock .s{color:#cbd5e1;}
h2{font-size:15px;margin:0 0 12px;display:flex;align-items:center;gap:10px;}
h2 .n{display:inline-flex;width:26px;height:26px;border-radius:50%;background:var(--ink);color:#fff;font-size:13px;align-items:center;justify-content:center;font-weight:800;}
h2 small{font-weight:500;color:var(--mut);font-size:12.5px;}
table{border-collapse:collapse;width:100%;font-size:13.5px;}
th{background:#f8fafc;color:#334155;padding:8px 10px;text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1.5px solid var(--line);}
td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:top;}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;}
tr:last-child td{border-bottom:none;}
.jname{font-weight:800;}.jexp{font-size:11.5px;color:var(--mut);font-weight:400;margin-top:1px;}
.tag{display:inline-block;border-radius:6px;padding:1px 7px;font-size:11px;font-weight:800;}
.tag.ok{background:#ecfdf5;color:#065f46;}.tag.warn{background:#fee2e2;color:#991b1b;}.tag.mut{background:#f1f5f9;color:#475569;}
button,a.btn{border:none;border-radius:9px;background:var(--ink);color:#fff;font-weight:800;font-size:13.5px;padding:10px 16px;cursor:pointer;text-decoration:none;display:inline-block;line-height:1.2;}
button:hover,a.btn:hover{filter:brightness(1.25);}
a.btn.sec,button.sec{background:#fff;color:var(--ink);border:1.5px solid #cbd5e1;}
a.btn.sec:hover,button.sec:hover{filter:none;border-color:#64748b;}
button.big{font-size:15px;padding:13px 20px;}
.alert{border-radius:11px;padding:11px 14px;margin:0 0 10px;font-size:13.5px;border:1.5px solid;display:flex;gap:10px;align-items:flex-start;line-height:1.45;}
.alert .i{font-size:18px;line-height:1;margin-top:1px;}
.alert .t{font-weight:800;}
.alert .d{font-size:12px;font-weight:400;margin-top:4px;color:inherit;opacity:.85;}
.alert.ok{background:#ecfdf5;border-color:#a7f3d0;color:#065f46;}
.alert.info{background:#fefce8;border-color:#fde68a;color:#713f12;}
.alert.bad{background:#fef2f2;border-color:#fecaca;color:#7f1d1d;}
.alert a{color:inherit;font-weight:800;}
.alert:last-child{margin-bottom:0;}
.actions{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:14px;padding-top:14px;border-top:1.5px solid var(--line);}
.chk{display:flex;gap:8px;align-items:center;font-size:13px;font-weight:600;color:#334155;}
.lockrow{display:flex;gap:12px;align-items:center;flex-wrap:wrap;}
.hint{font-size:12px;color:var(--mut);font-weight:400;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
@media(max-width:720px){.grid2{grid-template-columns:1fr;}}
details summary{cursor:pointer;font-weight:800;font-size:13.5px;color:#334155;list-style:none;}
details summary::-webkit-details-marker{display:none;}
details summary:before{content:'▸ ';}details[open] summary:before{content:'▾ ';}
.empty{color:var(--mut);font-size:14px;padding:10px 0;}
</style></head><body><div class="wrap">
<div class="head"><div><h1>📤 Export comptable Sage</h1>
<p class="sub">Fichiers d'écritures au format d'import du cabinet + fichier des nouveaux clients à créer dans Sage. Un dossier Sage par société.</p></div>
<div class="tools"><a href="rappro?token=__TOKEN__">🏦 Rapprochement bancaire Sage</a></div></div>
<div class="card">
<form class="bar" method="get" action="">
<input type="hidden" name="token" value="__TOKEN__">
<div><label>Société</label><select name="societe" onchange="this.form.submit()">__SOCIETES__</select></div>
<div><label>Du</label><input type="date" name="du" value="__DU__" onchange="if(this.form.au.value)this.form.submit()"></div>
<div><label>Au</label><input type="date" name="au" value="__AU__" onchange="if(this.form.du.value)this.form.submit()"></div>
</form>
__STATUS__
</div>
__CORPS__
</div></body></html>"""


def _alert(kind, icon, titre, detail="", extra=""):
    return ("<div class='alert %s'><span class='i'>%s</span><div><div class='t'>%s</div>%s%s</div></div>"
            % (kind, icon, titre, ("<div class='d'>%s</div>" % detail) if detail else "", extra))


@bp.route("/", methods=["GET"])
def page():
    _check_token()
    token = request.args.get("token", "")
    comps = _q("res.company", "search_read", [], fields=["name"], order="id")
    comp = int(request.args.get("societe") or comps[0]["id"])
    d = date.today()

    opts_soc = "".join('<option value="%s"%s>%s</option>' % (
        c["id"], " selected" if c["id"] == comp else "", c["name"]) for c in comps)

    # dernier export ZIP de la société : mémorisé pour reprendre au lendemain
    dernier = (_q("ir.config_parameter", "get_param",
                  "maquignon.export_compta_dernier_%s" % comp) or "")
    suggestion = ""
    stat_dernier = "<div class='stat'><div class='k'>Dernier export</div><div class='v'>aucun</div></div>"
    if dernier.count("|") == 2:
        d_du, d_au, d_fait = dernier.split("|")
        from datetime import datetime, timedelta
        try:
            suggestion = (datetime.strptime(d_au, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            suggestion = ""
        stat_dernier = ("<div class='stat'><div class='k'>📌 Dernier export</div><div class='v'>%s → %s</div>"
                        "<div class='s'>fait le %s</div></div>" % (_dfr(d_du), _dfr(d_au), _dfr(d_fait[:10])))
    # période affichée : du/au de l'URL, sinon lendemain du dernier export → aujourd'hui
    du, au, _lib = _periode({"du": request.args.get("du"), "au": request.args.get("au"),
                             "mois": d.strftime("%Y-%m")})
    if not request.args.get("du"):
        du = suggestion or du.replace(du[8:], "01")
        au = max(du, d.isoformat())
    libelle = "du %s au %s" % (_dfr(du), _dfr(au))
    periode_qs = "du=%s&au=%s" % (du, au)
    verrou = _q("res.company", "read", [comp], fields=["sale_lock_date"])[0]["sale_lock_date"]
    stat_verrou = ("<div class='stat lock'><div class='k'>🔒 Ventes verrouillées</div><div class='v'>jusqu'au %s</div>"
                   "<div class='s'>plus aucune écriture de vente possible avant cette date</div></div>"
                   % (_dfr(verrou) if verrou else "— aucun verrou"))
    stat_periode = ("<div class='stat'><div class='k'>📅 Période affichée</div><div class='v'>%s</div>"
                    "<div class='s'>pré-remplie au lendemain du dernier export</div></div>" % libelle)
    status = "<div class='status'>%s%s%s</div>" % (stat_dernier, stat_verrou, stat_periode)

    journaux = _journaux(comp)
    agg, nouveaux = _apercu(comp, du, au, journaux)
    inclure = request.args.get("inclure") == "1"
    lignes_html = ""
    total_deja = total_pieces = 0
    for j in journaux:
        a = agg.get(j["id"])
        if not a:
            continue
        n_deja = len(a["deja"]); total_deja += n_deja
        n_sort = len(a["pieces"]) if inclure else len(a["pieces"]) - n_deja
        total_pieces += n_sort
        url = "fichier?token=%s&journal=%s&%s%s" % (token, j["id"], periode_qs, "&inclure=1" if inclure else "")
        if n_deja and inclure:
            tag = "<div style='margin-top:3px;'><span class='tag warn'>⚠ %d déjà transférée(s) incluses</span></div>" % n_deja
        elif n_deja:
            tag = "<div style='margin-top:3px;'><span class='tag ok'>✓ %d déjà transférée(s) exclues</span></div>" % n_deja
        else:
            tag = ""
        btn = ("<a class='btn sec' href='%s'>⬇ .txt</a>" % url) if n_sort else "<span class='tag mut'>rien à sortir</span>"
        lignes_html += ("<tr><td><span class='tag mut'>%s</span></td><td><div class='jname'>%s</div><div class='jexp'>%s</div></td>"
                        "<td>%s</td><td class='num'><b>%d</b>%s</td>"
                        "<td class='num'>%s</td><td class='num'>%.2f €</td><td class='num'>%s</td></tr>" % (
                            j["code"] or "—", j["name"], j.get("explication", ""),
                            TYPES.get(j["type"], j["type"]), n_sort, tag, a["nlignes"], a["debit"], btn))

    corps = ""
    if not lignes_html:
        corps += ("<div class='card'><h2><span class='n'>1</span>Journaux de la période</h2>"
                  "<p class='empty'>Aucune écriture validée <b>%s</b> pour cette société.</p></div>" % libelle)
    else:
        # ── 1. Points à vérifier ──
        alertes = ""
        if total_deja:
            # case à cocher bien visible : recharge la page en mode « inclure » (ou normal)
            base_url_page = "?token=%s&societe=%s&%s" % (token, comp, periode_qs)
            case = ("<label style='display:flex;gap:10px;align-items:center;margin-top:10px;padding:9px 12px;border-radius:9px;"
                    "cursor:pointer;font-weight:800;font-size:14px;background:%s;border:2px solid %s;color:%s;'>"
                    "<input type='checkbox' style='width:20px;height:20px;cursor:pointer;'%s "
                    "onchange=\"location.href='%s' + (this.checked ? '&inclure=1' : '')\"> "
                    "Inclure les %d pièce(s) déjà transférée(s) dans les fichiers"
                    "<span style='font-weight:500;font-size:12.5px;'>— uniquement si le fichier précédent a été perdu ou jamais importé</span></label>"
                    % ("#fee2e2" if inclure else "#fff", "#dc2626" if inclure else "#a7f3d0", "#7f1d1d" if inclure else "#065f46",
                       " checked" if inclure else "", base_url_page, total_deja))
            if inclure:
                alertes += _alert("bad", "⚠", "Ré-export activé : %d pièce(s) déjà transférée(s) seront de nouveau dans les fichiers" % total_deja,
                                  "Risque de doublon dans Sage. Décochez la case pour revenir au mode normal.", case)
            else:
                alertes += _alert("ok", "🛡", "Garde-fou : %d pièce(s) déjà transférée(s) à Sage sont exclues des fichiers" % total_deja,
                                  "Seules les pièces jamais transférées sortiront.", case)
        if nouveaux:
            alertes += _alert("info", "👤", "%d nouveau(x) client(s) à créer dans Sage — inclus dans le ZIP (nouveaux_clients_*.txt)" % len(nouveaux),
                              " · ".join("<b>%s</b> %s" % (r, n) for r, n in nouveaux))
        r_au, r_fait, retro = _pieces_retro(comp, journaux)
        if retro:
            det = " · ".join("<b>%s</b> %s (%s, %.2f €)" % (
                r["name"], _dfr(r["date"]), r["journal_id"][1], r["amount_total"] or 0) for r in retro)
            alertes += _alert("bad", "⏪", "%d écriture(s) datée(s) dans une période déjà exportée (≤ %s) mais saisie(s) depuis" % (len(retro), _dfr(r_au)),
                              det + "<br>Elles ne sortiront pas avec la plage pré-remplie.",
                              "<div style='margin-top:8px;'><a class='btn' href='retro?token=%s&societe=%s'>⬇ Exporter ces écritures pour Sage</a> "
                              "<span class='hint'>même format — l'alerte s'efface une fois le fichier téléchargé</span></div>" % (token, comp))
        manq = _controle_analytique(comp, du, au, journaux)
        if manq:
            det = " · ".join("<b>%s</b> %s (%.2f €)" % (c, p, m) for p, c, m in manq[:20])
            if len(manq) > 20:
                det += " · … et %d autre(s)" % (len(manq) - 20)
            alertes += _alert("bad", "⚠️", "%d ligne(s) de vente sans section analytique" % len(manq),
                              det + "<br>Elles partiront dans Sage sans analytique : à compléter dans Odoo (ou à ignorer si voulu, ex. cession de matériel) puis recharger.")
        if not alertes:
            alertes = _alert("ok", "✅", "Rien à signaler pour cette période", "Aucun nouveau client, aucune écriture rétroactive, analytique complète.")
        corps += ("<div class='card'><h2><span class='n'>1</span>Vérifier <small>avant d'exporter</small></h2>%s</div>" % alertes)

        # ── 2. Exporter ──
        champs = ("<input type='hidden' name='du' value='%s'><input type='hidden' name='au' value='%s'>%s"
                  % (du, au, "<input type='hidden' name='inclure' value='1'>" if inclure else ""))
        corps += ("<div class='card'><h2><span class='n'>2</span>Exporter <small>%s · %d pièce(s) à sortir</small></h2>"
                  "<table><tr><th>Code</th><th>Journal</th><th>Type</th><th style='text-align:right'>Pièces</th>"
                  "<th style='text-align:right'>Lignes</th><th style='text-align:right'>Total débit</th><th></th></tr>%s</table>"
                  "<form method='post' action='export?token=%s' class='actions'>"
                  "<input type='hidden' name='societe' value='%s'>%s"
                  "<button type='submit' class='big'>📦 Télécharger le ZIP complet</button>"
                  "<label class='chk'><input type='checkbox' name='marquer' value='1' checked> Marquer les nouveaux clients comme transmis à Sage</label>"
                  "</form></div>" % (libelle, total_pieces, lignes_html, token, comp, champs))

        # ── 3. Verrouiller ──
        corps += ("<div class='card'><h2><span class='n'>3</span>Verrouiller les ventes <small>une fois les fichiers importés dans Sage</small></h2>"
                  "<form method='post' action='verrou?token=%s' class='lockrow' "
                  "onsubmit=\"return confirm('Verrouiller les ventes de cette société jusqu\\'au ' + this.au.value.split('-').reverse().join('/') + ' ?');\">"
                  "<input type='hidden' name='societe' value='%s'><input type='hidden' name='du' value='%s'>"
                  "<span style='background:#0f172a;color:#fff;border-radius:9px;padding:9px 13px;font-size:14px;'>"
                  "🔒 Verrouillé jusqu'au <b style='font-size:17px;'>%s</b></span>"
                  "<label style='display:flex;gap:8px;align-items:center;font-weight:700;'>Nouveau verrou jusqu'au "
                  "<input type='date' name='au' value='%s' min='%s' required></label>"
                  "<button type='submit' class='sec'>🔒 Verrouiller</button>"
                  "<span class='hint'>jamais reculé — bloque toute écriture de vente antérieure</span></form></div>"
                  % (token, comp, du, _dfr(verrou) if verrou else "aucun verrou", au, verrou or ""))

    # ── Outils ──
    import json as _j2
    try:
        histo = _j2.loads(_q("ir.config_parameter", "get_param",
                             "maquignon.export_compta_histo_%s" % comp) or "[]")
    except ValueError:
        histo = []
    histo_html = "<p class='empty'>Aucun export enregistré.</p>"
    if histo:
        lg = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                     % (_dfr(h.get("fait", "")), h.get("j", ""), _dfr(h.get("du", "")), _dfr(h.get("au", "")))
                     for h in histo[:25])
        histo_html = ("<table style='margin-top:8px;'><tr><th>Fait le</th><th>Journal</th><th>Du</th><th>Au</th></tr>%s</table>" % lg)
    corps += ("<div class='grid2'>"
              "<div class='card'><h2>🧾 Exporter une seule facture <small>oubliée ou saisie après l'export</small></h2>"
              "<form method='get' action='facture' style='display:flex;gap:8px;align-items:center;flex-wrap:wrap;'>"
              "<input type='hidden' name='token' value='%s'><input type='hidden' name='societe' value='%s'>"
              "<input type='text' name='numero' placeholder='FAC/26-27/0600' required style='min-width:180px;'>"
              "<button type='submit'>⬇ .txt</button></form>"
              "<p class='hint' style='margin:10px 0 0;'>Même format que le journal. La facture est marquée « Transféré Sage » dans Odoo ; "
              "si elle l'est déjà, la page demande confirmation.</p></div>"
              "<div class='card'><details%s><summary>🕘 Historique des exports (%d)</summary>%s</details></div>"
              "</div>" % (token, comp, "" if histo else " open", len(histo), histo_html))

    html = (PAGE.replace("__SOCIETES__", opts_soc)
                .replace("__DU__", du).replace("__AU__", au)
                .replace("__TOKEN__", token).replace("__STATUS__", status).replace("__CORPS__", corps))
    return Response(html, mimetype="text/html")


def _fichier_journal(j, du, au, base_url, clients_vus, comp, move_ids=None, sortis=None, inclure=False):
    if j.get("format_caisse") or j["type"] == "cash":
        return _export_caisse(j, du, au, clients_vus, comp, move_ids, sortis, inclure), "export_tickets_comptoir"
    return _export_ventes(j, du, au, base_url, clients_vus, comp, move_ids, sortis, inclure), "export_journal"


def _marquer_transferees(sortis):
    """Horodate les pièces exportées (account.move.x_sage_envoye_le) : la liste
    des factures Odoo affiche « Transféré Sage » et un filtre « non transférées ».
    Une pièce déjà marquée garde sa première date."""
    if not sortis:
        return
    from datetime import datetime as _dt
    ids = _q("account.move", "search", [("id", "in", list(sortis)), ("x_sage_envoye_le", "=", False)])
    if ids:
        _q("account.move", "write", ids, {"x_sage_envoye_le": _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")})
    return len(ids)


@bp.route("/fichier", methods=["GET"])
def fichier():
    _check_token()
    jid = int(request.args["journal"])
    du, au, _lib = _periode(request.args)
    j = _q("account.journal", "read", [jid], fields=["name", "code", "type", "company_id"],
           context={"lang": "fr_FR"})[0]
    pos = _q("pos.config", "search_read", [("journal_id", "=", jid)], fields=["id"])
    j["format_caisse"] = j["type"] == "cash" or bool(pos)
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    sortis = set()
    inclure = request.args.get("inclure") == "1"
    contenu, prefixe = _fichier_journal(j, du, au, base_url, set(), j["company_id"][0], sortis=sortis, inclure=inclure)
    if contenu is None:
        return Response("Aucune écriture (ou toutes déjà transférées à Sage — voir « Les inclure quand même » sur la page).",
                        mimetype="text/plain; charset=utf-8", status=404)
    _marquer_transferees(sortis)
    _histo_add(j["company_id"][0], "%s — %s" % (j["code"] or "", j["name"]), du, au)
    _dernier_maj(j["company_id"][0], du, au)
    slug = j["company_id"][1].replace(" ", "_").replace("/", "_")
    nom = "%s_%s_%s_du_%s_au_%s.txt" % (prefixe, slug, j["name"].replace(" ", "_"),
                                        du.replace("-", ""), au.replace("-", ""))
    return Response(contenu.encode("cp1252", errors="replace"),
                    mimetype="text/plain; charset=windows-1252",
                    headers={"Content-Disposition": "attachment; filename=%s" % nom})


@bp.route("/retro", methods=["GET"])
def retro():
    """Exporte les écritures rétroactives (datées dans la période déjà exportée
    mais saisies depuis) au format Sage, puis rafraîchit l'horodatage du repère
    pour effacer l'alerte. Un fichier par journal, ZIP si plusieurs."""
    _check_token()
    comp = int(request.args["societe"])
    journaux = _journaux(comp)
    d_au, d_fait, moves = _pieces_retro(comp, journaux)
    if not moves:
        return Response("Aucune écriture rétroactive.", mimetype="text/plain; charset=utf-8", status=404)
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    d_min = min(m["date"] for m in moves)
    par_journal = {}
    for m in moves:
        par_journal.setdefault(m["journal_id"][0], []).append(m["id"])
    comp_nom = _q("res.company", "read", [comp], fields=["name"])[0]["name"]
    slug = comp_nom.replace(" ", "_").replace("/", "_")
    fichiers = []
    sortis_retro = set()
    for j in journaux:
        if j["id"] not in par_journal:
            continue
        contenu, prefixe = _fichier_journal(j, d_min, d_au, base_url, set(), comp,
                                            move_ids=par_journal[j["id"]], sortis=sortis_retro)
        if contenu:
            nom = "retro_%s_%s_%s_jusquau_%s.txt" % (prefixe.replace("export_", ""), slug,
                                                     j["name"].replace(" ", "_"), d_au.replace("-", ""))
            fichiers.append((nom, contenu))
    if not fichiers:
        return Response("Aucune écriture rétroactive.", mimetype="text/plain; charset=utf-8", status=404)
    # repère rafraîchi (mêmes bornes, horodatage neuf) -> l'alerte s'efface
    from datetime import datetime as _dt
    dernier = _q("ir.config_parameter", "get_param", "maquignon.export_compta_dernier_%s" % comp) or ""
    d_du = dernier.split("|")[0] if dernier.count("|") == 2 else d_min
    _q("ir.config_parameter", "set_param", "maquignon.export_compta_dernier_%s" % comp,
       "%s|%s|%s" % (d_du, d_au, _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    _marquer_transferees(sortis_retro)
    _histo_add(comp, "⏪ Écritures rétroactives (%d pièce(s))" % len(moves), d_min, d_au)
    if len(fichiers) == 1:
        nom, contenu = fichiers[0]
        return Response(contenu.encode("cp1252", errors="replace"),
                        mimetype="text/plain; charset=windows-1252",
                        headers={"Content-Disposition": "attachment; filename=%s" % nom})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, contenu in fichiers:
            z.writestr(nom, contenu.encode("cp1252", errors="replace"))
    return Response(buf.getvalue(), mimetype="application/zip",
                    headers={"Content-Disposition": "attachment; filename=retro_%s_jusquau_%s.zip"
                             % (slug, d_au.replace("-", ""))})


@bp.route("/facture", methods=["GET"])
def facture():
    """Exporte UNE facture / un avoir (n° Odoo) au format de son journal, la
    marque transférée et l'ajoute à l'historique. Utile pour une pièce oubliée
    ou saisie après l'export de la période."""
    _check_token()
    numero = (request.args.get("numero") or "").strip()
    comp = int(request.args.get("societe") or 0)
    if not numero:
        return Response("Indiquez un numéro de facture.", mimetype="text/plain; charset=utf-8", status=400)
    dom = [("name", "=ilike", numero), ("state", "=", "posted")]
    if comp:
        dom.append(("company_id", "=", comp))
    mv = _q("account.move", "search_read", dom, fields=["name", "date", "journal_id", "company_id",
                                                       "x_sage_envoye_le", "amount_total"], limit=2)
    if not mv:
        return Response("Facture « %s » introuvable (ou non validée)." % numero,
                        mimetype="text/plain; charset=utf-8", status=404)
    if len(mv) > 1:
        return Response("Plusieurs pièces portent ce numéro : précisez la société.",
                        mimetype="text/plain; charset=utf-8", status=409)
    mv = mv[0]
    if mv["x_sage_envoye_le"] and request.args.get("force") != "1":
        from urllib.parse import quote as _quote
        html = ("<html><body style='font-family:Segoe UI,sans-serif;padding:30px;max-width:640px;'>"
                "<h2>🛡 %s a déjà été transférée à Sage</h2>"
                "<p>Transférée le <b>%s</b> (heure UTC). La ré-exporter créerait un <b>doublon</b> dans Sage.</p>"
                "<p><a href='javascript:history.back()' style='display:inline-block;padding:10px 16px;background:#0f172a;color:#fff;"
                "border-radius:8px;text-decoration:none;font-weight:700;'>← Retour</a> &nbsp; "
                "<a href='facture?token=%s&societe=%s&numero=%s&force=1' style='display:inline-block;padding:10px 16px;"
                "background:#fee2e2;color:#7f1d1d;border:1.5px solid #fca5a5;border-radius:8px;text-decoration:none;font-weight:700;'>"
                "Exporter quand même</a> <span style='font-size:12px;color:#64748b;'>(fichier perdu ou jamais importé)</span></p>"
                "</body></html>" % (mv["name"], mv["x_sage_envoye_le"][:16], request.args.get("token", ""),
                                    comp, _quote(numero)))
        return Response(html, mimetype="text/html", status=409)
    j = _q("account.journal", "read", [mv["journal_id"][0]], fields=["name", "code", "type", "company_id"],
           context={"lang": "fr_FR"})[0]
    pos = _q("pos.config", "search_read", [("journal_id", "=", j["id"])], fields=["id"])
    j["format_caisse"] = j["type"] == "cash" or bool(pos)
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    sortis = set()
    contenu, prefixe = _fichier_journal(j, mv["date"], mv["date"], base_url, set(),
                                        mv["company_id"][0], move_ids=[mv["id"]], sortis=sortis, inclure=True)
    if contenu is None:
        return Response("Aucune écriture exportable pour %s." % mv["name"],
                        mimetype="text/plain; charset=utf-8", status=404)
    _marquer_transferees(sortis)
    _histo_add(mv["company_id"][0], "🧾 Facture seule %s" % mv["name"], mv["date"], mv["date"])
    slug = mv["company_id"][1].replace(" ", "_").replace("/", "_")
    nom = "%s_%s_%s.txt" % (prefixe, slug, mv["name"].replace("/", "-"))
    return Response(contenu.encode("cp1252", errors="replace"),
                    mimetype="text/plain; charset=windows-1252",
                    headers={"Content-Disposition": "attachment; filename=%s" % nom})


@bp.route("/verrou", methods=["POST"])
def verrou():
    _check_token()
    comp = int(request.form["societe"])
    au = (request.form.get("au") or "").strip()
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", au):
        abort(400)
    actuel = _q("res.company", "read", [comp], fields=["sale_lock_date"])[0]["sale_lock_date"]
    if not actuel or au > actuel:
        # verrou des VENTES uniquement (pas le verrou global : les relevés
        # bancaires tardifs doivent rester importables) — jamais reculé
        _q("res.company", "write", [comp], {"sale_lock_date": au})
    from flask import redirect
    return redirect("?token=%s&societe=%s&du=%s&au=%s" % (
        request.args.get("token", ""), comp, request.form.get("du", ""), au))


@bp.route("/export", methods=["POST"])
def export():
    _check_token()
    comp = int(request.form["societe"])
    du, au, _lib = _periode(request.form)
    marquer = request.form.get("marquer") == "1"
    comp_nom = _q("res.company", "read", [comp], fields=["name"])[0]["name"]
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    slug = comp_nom.replace(" ", "_").replace("/", "_")
    suffixe = "du_%s_au_%s" % (du.replace("-", ""), au.replace("-", ""))
    clients_vus = set()
    sortis = set()
    inclure = request.form.get("inclure") == "1"
    buf = io.BytesIO()
    n_fichiers = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for j in _journaux(comp):
            contenu, prefixe = _fichier_journal(j, du, au, base_url, clients_vus, comp, sortis=sortis, inclure=inclure)
            if contenu is None:
                continue
            nom = "%s_%s_%s_%s.txt" % (prefixe, slug, j["name"].replace(" ", "_"), suffixe)
            z.writestr(nom, contenu.encode("cp1252", errors="replace"))
            n_fichiers += 1
        contenu_nc, n_nouveaux = _nouveaux_clients(clients_vus, marquer)
        if contenu_nc:
            z.writestr("nouveaux_clients_%s_%s.txt" % (slug, suffixe),
                       contenu_nc.encode("cp1252", errors="replace"))
    if n_fichiers == 0:
        return Response("Aucune écriture sur la période pour cette société (ou toutes déjà transférées à Sage).",
                        mimetype="text/plain; charset=utf-8", status=404)
    _marquer_transferees(sortis)
    _histo_add(comp, "📦 ZIP complet", du, au)
    _dernier_maj(comp, du, au)
    buf.seek(0)
    return Response(buf.read(), mimetype="application/zip",
                    headers={"Content-Disposition":
                             "attachment; filename=export_compta_%s_%s.zip" % (slug, suffixe)})


# ─── IMPORT DU RAPPROCHEMENT BANCAIRE SAGE (Maquignon & Haims) ───────────────
# Charlotte lettre dans Sage ; l'état « Rapprochement bancaire » imprimé vers
# Excel est déposé ici. Chaque encaissement pointé est rapproché des paiements
# « En paiement » d'Odoo (montant exact ou combinaison — remises de chèques),
# ou d'une facture ouverte (création du paiement). L'application crée
# l'écriture 512/511900 à la date de l'écriture pointée et lettre le compte
# d'attente → paiement « Payé », facture « Payée ». Décaissements ignorés
# (fournisseurs, hors périmètre). Sociétés : Maquignon, Châtel'Granulats,
# Haims. Distri Béton : rapprochement Odoo.
import json as _json
from itertools import combinations as _combi


def _rappro_parse(fichier):
    """Lit l'état Sage « Rapprochement bancaire » (impression vers Excel)."""
    import openpyxl
    wb = openpyxl.load_workbook(fichier, data_only=True)
    ws = wb.active
    lignes, date_rappro, compte = [], "", ""
    for row in ws.iter_rows(values_only=True):
        cells = list(row)
        if any(c and "Date de rapprochement" in str(c) for c in cells):
            for c in cells:
                if c and str(c)[:4].isdigit() and "-" in str(c):
                    date_rappro = str(c)[:10]
        if cells[0] and str(cells[0]).startswith("512"):
            compte = str(cells[0]).strip()
            debit = float(cells[13] or cells[14] or 0)
            credit = float(cells[16] or cells[17] or 0)
            lignes.append({"compte": compte, "date": str(cells[2])[:10],
                           "piece": str(cells[4] or ""), "lib": str(cells[6] or "").strip(),
                           "debit": round(debit, 2), "credit": round(credit, 2)})
    return lignes, date_rappro


def _norm_rappro(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper()
    return "".join(c for c in s if c.isalnum())


def _rappro_journal(comp, compte):
    """Journal Odoo dont le compte par défaut correspond au compte Sage."""
    js = _q("account.journal", "search_read",
            [("company_id", "=", comp), ("type", "=", "bank")],
            fields=["name", "code", "default_account_id"])
    cible = "".join(c for c in compte if c.isdigit())
    for j in js:
        code = "".join(c for c in (j["default_account_id"][1] if j["default_account_id"] else "") if c.isdigit())
        if code and (code.startswith(cible) or cible.startswith(code[:6])):
            return j
    return js[0] if js else None


def _rappro_analyse(comp, lignes, journal_id=None):
    """Propositions de lettrage pour les encaissements (débits 512)."""
    dom = [("company_id", "=", comp), ("state", "=", "in_process"),
           ("payment_type", "=", "inbound"), ("move_id", "!=", False)]
    if journal_id:
        dom.append(("journal_id", "=", journal_id))
    pays = _q("account.payment", "search_read", dom,
              fields=["name", "partner_id", "amount", "date", "move_id"], limit=0)
    invs = _q("account.move", "search_read",
              [("company_id", "=", comp), ("move_type", "=", "out_invoice"),
               ("state", "=", "posted"),
               ("payment_state", "in", ["not_paid", "partial"])],
              fields=["name", "partner_id", "amount_residual"], limit=0)
    props = []
    for l in lignes:
        if not l["debit"]:
            continue
        m, nlib = l["debit"], _norm_rappro(l["lib"])
        prop = {"ligne": l, "type": "inconnu", "detail": [], "ids": []}
        exacts = [p for p in pays if abs(p["amount"] - m) < 0.01]
        if len(exacts) == 1:
            p = exacts[0]
            prop.update(type="paiements", ids=[p["id"]],
                        detail=["%s — %s (%.2f €)" % (p["name"], p["partner_id"][1] if p["partner_id"] else "?", p["amount"])])
        elif len(exacts) > 1:
            nommes = [p for p in exacts if p["partner_id"] and (_norm_rappro(p["partner_id"][1]) in nlib or nlib in _norm_rappro(p["partner_id"][1]))]
            p = (nommes or exacts)[0]
            prop.update(type="paiements", ids=[p["id"]],
                        detail=["%s — %s (%.2f €)" % (p["name"], p["partner_id"][1] if p["partner_id"] else "?", p["amount"])])
        else:
            # combinaison : UNIQUEMENT pour les remises groupees (cheques, effets)
            import re as _re
            est_remise = bool(_re.search(r"remise|ch[eè]q|effet|lcr", l["lib"], _re.I))
            mts = [round(p["amount"], 2) for p in pays] if est_remise else []
            trouve = None
            for r in range(2, min(7, len(mts) + 1)):
                for c in _combi(range(len(mts)), r):
                    if abs(sum(mts[i] for i in c) - m) < 0.01:
                        trouve = c
                        break
                if trouve:
                    break
            if trouve:
                prop.update(type="paiements", ids=[pays[i]["id"] for i in trouve],
                            detail=["%s — %s (%.2f €)" % (pays[i]["name"], pays[i]["partner_id"][1] if pays[i]["partner_id"] else "?", pays[i]["amount"]) for i in trouve])
            else:
                cands = [i for i in invs if abs(i["amount_residual"] - m) < 0.01
                         and i["partner_id"] and (_norm_rappro(i["partner_id"][1]) in nlib or nlib in _norm_rappro(i["partner_id"][1]))]
                if len(cands) == 1:
                    i = cands[0]
                    prop.update(type="facture", ids=[i["id"]],
                                detail=["%s — %s (reste %.2f €)" % (i["name"], i["partner_id"][1], i["amount_residual"])])
        props.append(prop)
    ignores = [l for l in lignes if l["credit"]]
    return props, ignores


def _erreur_propre(s):
    """Traduit les erreurs techniques en messages lisibles par la comptable."""
    s = str(s)
    if "cannot marshal None" in s:
        return ("la réconciliation n'a pas abouti (écart de montant probable, "
                "quelques centimes ?) — à vérifier sur la pièce dans Odoo")
    if "Fault" in s or "Traceback" in s:
        lignes = [l.strip() for l in s.replace("\\n", "\n").split("\n") if l.strip()]
        for l in reversed(lignes):
            if "File \"" not in l and not l.startswith(("^", "~", "raise ")):
                return l.split(":", 1)[-1].strip().rstrip("'>\"") or "erreur Odoo"
    return s[-160:]


def _compte_ecart(comp, sens):
    """Compte d'écart de règlement : charges (658*) ou produits (758*)."""
    pref = "658" if sens == "charge" else "758"
    a = _q("account.account", "search",
           [("code", "=like", pref + "%"), ("company_ids", "in", [comp])],
           limit=1, context={"allowed_company_ids": [comp]})
    return a[0] if a else None


def _infos_journal(jid):
    """(compte d'attente, compte banque) d'un journal — None si non configuré."""
    j = _q("account.journal", "read", [jid], fields=["name", "default_account_id"])[0]
    pml = _q("account.payment.method.line", "search_read",
             [("journal_id", "=", jid), ("payment_type", "=", "inbound"),
              ("payment_account_id", "!=", False)],
             fields=["payment_account_id"], limit=1)
    if not pml:
        return None, None, j["name"]
    return pml[0]["payment_account_id"][0], j["default_account_id"][0], j["name"]


def _rappro_applique(comp, journal, props, avance=None):
    """Crée l'écriture 512/511 et lettre — la primitive validée sur la base de test.
    Chaque proposition peut porter son propre journal (journal_id), sinon celui
    passé en paramètre (cas de l'état de rapprochement, un seul journal)."""
    jcache = {}

    def infos(jid):
        if jid not in jcache:
            jcache[jid] = _infos_journal(jid)
        return jcache[jid]

    faits, erreurs = 0, []
    for prop in props:
        if avance is not None:
            avance["n"] = avance.get("n", 0) + 1
        l = prop["ligne"]
        jid = prop.get("journal_id") or journal["id"]
        compte_attente, compte_banque, jnom = infos(jid)
        if prop["type"] in ("remise", "remise_attente", "remise_partielle"):
            # v3 : remise de chèques / CB Sage — un paiement par client, puis rapprochement
            # avec la vraie ligne de relevé (ou dépôt par lot en attente de la ligne)
            try:
                pml_lot = None
                if prop["type"] == "remise_attente":
                    pml_lot = _q("account.payment.method.line", "search",
                                 [("journal_id", "=", jid), ("payment_type", "=", "inbound"),
                                  ("payment_method_id.code", "=", "batch_payment")], limit=1)
                    pml_lot = pml_lot[0] if pml_lot else None
                pay_ids = list(prop.get("pay_ids") or [])
                for lo in prop["lots"]:
                    ctx = {"active_model": "account.move", "active_ids": lo["ids"]}
                    vals = {"journal_id": jid, "payment_date": l["date"], "group_payment": True,
                            "amount": lo["amount"],
                            "communication": ("Remise %s — %s" % (prop["ligne"]["piece"], lo["client"]))[:60]}
                    if pml_lot:
                        vals["payment_method_line_id"] = pml_lot
                    wid = _q("account.payment.register", "create", [vals], context=ctx)
                    wid = wid[0] if isinstance(wid, list) else wid
                    try:
                        _q("account.payment.register", "action_create_payments", [wid], context=ctx)
                    except Exception:
                        pass
                    nouveaux = _q("account.payment", "search",
                                  [("company_id", "=", comp), ("journal_id", "=", jid),
                                   ("state", "=", "in_process"),
                                   ("reconciled_invoice_ids", "in", lo["ids"])],
                                  limit=10, order="id desc")
                    if not nouveaux:
                        raise Exception("paiement non créé pour %s" % lo["client"])
                    pay_ids += nouveaux[:1]
                if prop["type"] == "remise_attente":
                    meth = _q("account.payment.method", "search", [("code", "=", "batch_payment"), ("payment_type", "=", "inbound")], limit=1)
                    bvals = {"journal_id": jid, "date": l["date"], "batch_type": "inbound",
                             "payment_ids": [(6, 0, pay_ids)]}
                    if meth:
                        bvals["payment_method_id"] = meth[0]
                    _q("account.batch.payment", "create", [bvals])
                    faits += 1
                    continue
                if prop["type"] == "remise_partielle":
                    faits += 1   # paiements créés ; le rapprochement se termine dans le widget
                    continue
                moves = [p_["move_id"][0] for p_ in _q("account.payment", "read", pay_ids, fields=["move_id"]) if p_["move_id"]]
                l_att_rows = _q("account.move.line", "search_read",
                                [("move_id", "in", moves), ("account_id", "=", compte_attente), ("reconciled", "=", False)],
                                fields=["debit"])
                l_att = [r["id"] for r in l_att_rows]
                l_stmt, tot_stmt = [], 0.0
                for sm in prop.get("stmt_moves") or []:
                    for ml in _q("account.move.line", "search_read",
                                 [("move_id", "=", sm), ("reconciled", "=", False)],
                                 fields=["account_id", "credit"]):
                        if ml["account_id"] and ml["account_id"][0] != compte_banque and ml["credit"] > 0:
                            if ml["account_id"][0] != compte_attente:
                                _q("account.move.line", "write", [ml["id"]], {"account_id": compte_attente})
                            l_stmt.append(ml["id"])
                            tot_stmt += ml["credit"]
                if not l_att or not l_stmt:
                    raise Exception("lignes à réconcilier introuvables")
                ids = l_att + l_stmt
                ecart = round(sum(r["debit"] for r in l_att_rows) - tot_stmt, 2)
                if abs(ecart) >= 0.005 and not prop.get("cb") and abs(ecart) > 0.05:
                    raise Exception("écart de %.2f € entre paiements et relevé — à finir dans le widget" % ecart)
                if abs(ecart) >= 0.005:
                    # commission CB (ou petit écart) : frais bancaires 62782000 si présent, sinon compte d'écart
                    cpt = _q("account.account", "search", [("code", "=", "62782000"), ("company_ids", "in", [comp])],
                             limit=1, context={"allowed_company_ids": [comp]})
                    cpt = cpt[0] if cpt else _compte_ecart(comp, "charge" if ecart > 0 else "produit")
                    if not cpt:
                        raise Exception("écart de %.2f € et aucun compte de frais/écart" % ecart)
                    m_ec = _q("account.move", "create", [{
                        "journal_id": jid, "date": l["date"],
                        "ref": "Commission / écart remise Sage n°%s" % prop["ligne"]["piece"],
                        "line_ids": [
                            (0, 0, {"account_id": cpt if ecart > 0 else compte_attente,
                                    "debit": abs(ecart), "credit": 0.0, "name": "Commission remise n°%s" % prop["ligne"]["piece"]}),
                            (0, 0, {"account_id": compte_attente if ecart > 0 else cpt,
                                    "debit": 0.0, "credit": abs(ecart), "name": "Commission remise n°%s" % prop["ligne"]["piece"]}),
                        ]}], context={"allowed_company_ids": [comp]})
                    m_ec = m_ec[0] if isinstance(m_ec, list) else m_ec
                    _q("account.move", "action_post", [m_ec])
                    ids += _q("account.move.line", "search", [("move_id", "=", m_ec), ("account_id", "=", compte_attente)])
                try:
                    _q("account.move.line", "reconcile", ids)
                except Exception:
                    verif = _q("account.move.line", "read", ids, fields=["reconciled"])
                    if not all(v["reconciled"] for v in verif):
                        raise
                faits += 1
            except Exception as exc:
                erreurs.append("%s : %s" % (l["lib"][:50], _erreur_propre(exc)))
            continue
        if prop["type"] == "releve":
            # v2 : la banque connectée a déjà l'écriture (ligne de relevé) —
            # on crée le paiement manquant puis on réconcilie l'attente du/des
            # paiement(s) avec la contrepartie du relevé. Zéro écriture créée.
            try:
                pay_ids = list(prop.get("pay_ids") or [])
                if prop.get("ids"):
                    ctx = {"active_model": "account.move", "active_ids": prop["ids"]}
                    wid = _q("account.payment.register", "create",
                             [{"journal_id": jid, "payment_date": l["date"],
                               "group_payment": True, "communication": l["lib"][:60]}],
                             context=ctx)
                    wid = wid[0] if isinstance(wid, list) else wid
                    try:
                        _q("account.payment.register", "action_create_payments", [wid], context=ctx)
                    except Exception:
                        pass
                    nouveaux = _q("account.payment", "search",
                                  [("company_id", "=", comp), ("journal_id", "=", jid),
                                   ("state", "=", "in_process"),
                                   ("reconciled_invoice_ids", "in", prop["ids"])],
                                  limit=50, order="id desc")
                    pay_ids += nouveaux
                moves = [p["move_id"][0] for p in _q("account.payment", "read", pay_ids, fields=["move_id"]) if p["move_id"]]
                l_att_rows = _q("account.move.line", "search_read",
                                [("move_id", "in", moves), ("account_id", "=", compte_attente), ("reconciled", "=", False)],
                                fields=["debit"])
                l_att = [r["id"] for r in l_att_rows]
                l_stmt, tot_stmt = [], 0.0
                for sm in prop.get("stmt_moves") or []:
                    for ml in _q("account.move.line", "search_read",
                                 [("move_id", "=", sm), ("reconciled", "=", False)],
                                 fields=["account_id", "credit"]):
                        if ml["account_id"] and ml["account_id"][0] != compte_banque and ml["credit"] > 0:
                            if ml["account_id"][0] != compte_attente:
                                _q("account.move.line", "write", [ml["id"]], {"account_id": compte_attente})
                            l_stmt.append(ml["id"])
                            tot_stmt += ml["credit"]
                if not l_att or not l_stmt:
                    erreurs.append("%s : lignes à réconcilier introuvables" % l["lib"][:40])
                    continue
                ids = l_att + l_stmt
                # écart de quelques centimes entre facture(s) et virement réel
                # (lettrage toléré par Sage) : passé en écart de règlement
                ecart = round(sum(r["debit"] for r in l_att_rows) - tot_stmt, 2)
                if 0 < abs(ecart) <= 0.05:
                    cpt = _compte_ecart(comp, "charge" if ecart > 0 else "produit")
                    if cpt:
                        m_ec = _q("account.move", "create", [{
                            "journal_id": jid, "date": l["date"],
                            "ref": "Écart de règlement Sage — %s" % l["lib"][:50],
                            "line_ids": [
                                (0, 0, {"account_id": cpt if ecart > 0 else compte_attente,
                                        "debit": abs(ecart), "credit": 0.0,
                                        "name": "Écart de règlement (%.2f €)" % ecart}),
                                (0, 0, {"account_id": compte_attente if ecart > 0 else cpt,
                                        "debit": 0.0, "credit": abs(ecart),
                                        "name": "Écart de règlement (%.2f €)" % ecart}),
                            ]}], context={"allowed_company_ids": [comp]})
                        m_ec = m_ec[0] if isinstance(m_ec, list) else m_ec
                        _q("account.move", "action_post", [m_ec])
                        ids += _q("account.move.line", "search",
                                  [("move_id", "=", m_ec), ("account_id", "=", compte_attente)])
                try:
                    _q("account.move.line", "reconcile", ids)
                except Exception:
                    verif = _q("account.move.line", "read", ids, fields=["reconciled"])
                    if not all(v["reconciled"] for v in verif):
                        raise
                faits += 1
            except Exception as exc:
                erreurs.append("%s : %s" % (l["lib"][:40], _erreur_propre(exc)))
            continue
        if not compte_attente:
            erreurs.append("journal %s : compte d'attente non configuré" % jnom)
            continue
        try:
            pay_ids = list(prop["ids"])
            if prop["type"] == "facture":
                ctx = {"active_model": "account.move", "active_ids": prop["ids"]}
                wid = _q("account.payment.register", "create",
                         [{"journal_id": jid, "amount": l["debit"], "payment_date": l["date"]}],
                         context=ctx)
                wid = wid[0] if isinstance(wid, list) else wid
                try:
                    _q("account.payment.register", "action_create_payments", [wid], context=ctx)
                except Exception:
                    pass  # l'action renvoyée peut contenir des None non sérialisables
                pay_ids = _q("account.payment", "search",
                             [("company_id", "=", comp), ("journal_id", "=", jid),
                              ("amount", "=", l["debit"]), ("date", "=", l["date"])],
                             limit=1, order="id desc")
                if not pay_ids:
                    erreurs.append("%s %.2f € : le paiement n'a pas pu être créé" % (l["lib"][:30], l["debit"]))
                    continue
            # lignes d'attente des paiements
            moves = [p["move_id"][0] for p in _q("account.payment", "read", pay_ids, fields=["move_id"]) if p["move_id"]]
            l_att = _q("account.move.line", "search",
                       [("move_id", "in", moves), ("account_id", "=", compte_attente), ("reconciled", "=", False)])
            if not l_att:
                erreurs.append("%s %.2f € : lignes d'attente introuvables" % (l["lib"][:30], l["debit"]))
                continue
            mid = _q("account.move", "create", [{
                "journal_id": jid, "date": l["date"],
                "ref": "Rapprochement Sage — %s" % (l["lib"][:60] or l["piece"]),
                "line_ids": [
                    (0, 0, {"account_id": compte_banque, "debit": l["debit"], "credit": 0.0,
                            "name": "Rapprochement Sage %s" % l["piece"]}),
                    (0, 0, {"account_id": compte_attente, "debit": 0.0, "credit": l["debit"],
                            "name": l["lib"][:60] or "Rapprochement Sage"}),
                ]}])
            mid = mid[0] if isinstance(mid, list) else mid
            _q("account.move", "action_post", [mid])
            l_rap = _q("account.move.line", "search", [("move_id", "=", mid), ("account_id", "=", compte_attente)])
            try:
                _q("account.move.line", "reconcile", l_att + l_rap)
            except Exception:
                # le contrôleur XML-RPC d'Odoo SaaS ne sait pas sérialiser le
                # None renvoyé par reconcile() : le lettrage a bien eu lieu
                # côté serveur — on vérifie l'état réel des lignes.
                verif = _q("account.move.line", "read", l_att + l_rap, fields=["reconciled"])
                if not all(v["reconciled"] for v in verif):
                    raise
            faits += 1
        except Exception as exc:
            erreurs.append("%s %.2f € : %s" % (l["lib"][:30], l["debit"], _erreur_propre(exc)))
    return faits, erreurs


# ─── GRAND-LIVRE DES TIERS (Sage) : lettrage par lettres ─────────────────────
# Fichier bien plus riche que l'état de rapprochement : chaque groupe portant
# la même lettre relie la ou les factures (n° Odoo dans le libellé des ventes)
# à leur(s) règlement(s) datés, journal par journal. À-nouveaux (RAN) inclus.
def _gl_detecte(fichier):
    """True si le fichier est un « Grand-livre des tiers » (sinon état 512)."""
    import openpyxl
    wb = openpyxl.load_workbook(fichier, read_only=True, data_only=True)
    ws = wb.active
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i > 8:
            break
        if any(c and "Grand-livre des tiers" in str(c) for c in row):
            return True
    return False


def _gl_parse(fichier):
    """Par client : écritures {date, journal, piece, lib, lettre, debit, credit}."""
    import openpyxl
    wb = openpyxl.load_workbook(fichier, data_only=True)
    ws = wb.active
    clients, cur = [], None
    for row in ws.iter_rows(values_only=True):
        c = list(row) + [None] * (19 - len(row))
        c0 = c[0]
        if c[5] == "Total du tiers" or (c0 and "Sage" in str(c0)) or c0 == "Date":
            continue
        est_date = hasattr(c0, "year")
        if c0 and not est_date and not c[1] and c[3]:
            cur = {"code": str(c0).strip(), "nom": str(c[3]).strip(), "ecritures": []}
            clients.append(cur)
            continue
        if cur is None or not est_date:
            continue
        cur["ecritures"].append({
            "date": str(c0)[:10], "journal": str(c[1] or "").strip(),
            "piece": str(c[2] or "").strip(), "lib": str(c[5] or "").strip(),
            "lettre": str(c[8] or "").strip(),
            "debit": round(float(c[12] or 0), 2), "credit": round(float(c[15] or 0), 2)})
    return [cl for cl in clients if cl["ecritures"]]


def _gl_analyse(comp, clients):
    """Groupes (client, lettre) équilibrés → propositions par facture Odoo."""
    import re as _re
    from collections import defaultdict
    js = _q("account.journal", "search_read",
            [("company_id", "=", comp), ("type", "=", "bank")], fields=["name", "code"])
    # journaux réellement câblés sur le compte d'attente (les journaux « CB /
    # chèques à encaisser » de Châtel restent sur leur circuit Odoo propre)
    cables = set()
    for j in js:
        pml = _q("account.payment.method.line", "search",
                 [("journal_id", "=", j["id"]), ("payment_type", "=", "inbound"),
                  ("payment_account_id", "!=", False)], limit=1)
        if pml:
            cables.add(j["id"])

    def journal_pour(code):
        code = (code or "").upper()
        for j in js:
            if code and (code == (j["code"] or "").upper() or code in (j["name"] or "").upper()):
                return j["id"]
        return js[0]["id"] if js else 0

    def journal_nom(jid2):
        for j in js:
            if j["id"] == jid2:
                return j["name"]
        return "?"

    noms = set()
    for cl in clients:
        for e in cl["ecritures"]:
            m = _re.search(r"(FAC/[0-9]{4}/[0-9]+|FAC/[0-9]{2}-[0-9]{2}/[0-9]+)", e["lib"])
            e["fac"] = m.group(1) if m else ""
            if e["fac"]:
                noms.add(e["fac"])
    invs = {}
    noms = sorted(noms)
    for i in range(0, len(noms), 400):
        for r in _q("account.move", "search_read",
                    [("company_id", "=", comp), ("name", "in", noms[i:i + 400])],
                    fields=["name", "payment_state", "amount_residual", "state"]):
            invs[r["name"]] = r
    # paiements « en paiement » existants : facture -> paiement à lettrer
    pay_par_inv = {}
    for p in _q("account.payment", "search_read",
                [("company_id", "=", comp), ("state", "=", "in_process"),
                 ("payment_type", "=", "inbound"), ("move_id", "!=", False)],
                fields=["name", "amount", "reconciled_invoice_ids"], limit=0):
        for iid in (p.get("reconciled_invoice_ids") or []):
            pay_par_inv.setdefault(iid, p)
    # v2 : lignes de relevé non rapprochées (banques connectées) — la vraie
    # écriture de banque est déjà dans Odoo, on la réconcilie au lieu d'en créer
    stmt = _q("account.bank.statement.line", "search_read",
              [("company_id", "=", comp), ("is_reconciled", "=", False), ("amount", ">", 0)],
              fields=["date", "amount", "journal_id", "move_id", "payment_ref"], limit=0)
    stmt_uses = set()

    def stmt_pour(jid, montant, dstr):
        import datetime as _dt
        try:
            dref = _dt.date.fromisoformat(dstr[:10])
        except Exception:
            return None
        cands = []
        for s2 in stmt:
            if s2["id"] in stmt_uses or s2["journal_id"][0] != jid:
                continue
            if abs(s2["amount"] - montant) > 0.005:
                continue
            ecart = abs((_dt.date.fromisoformat(str(s2["date"])[:10]) - dref).days)
            if ecart <= 5:
                cands.append((ecart, s2))
        if not cands:
            return None
        return sorted(cands, key=lambda c: c[0])[0][1]

    props, anomalies, deja = [], [], 0
    # ── v3 : remises de chèques / CB — dans Sage, n° de pièce du journal banque = n° de remise ──
    import datetime as _dt
    RE_CHQ = _re.compile(r"remise\s*ch|ch[eè]que|chq", _re.I)
    RE_CB = _re.compile(r"^\s*CB\b", _re.I)

    def brut_de(ref):
        mb = _re.search(r"BRUT\s+([\d\s]+,\d{2})", ref or "")
        try:
            return round(float(mb.group(1).replace(" ", "").replace(",", ".")), 2) if mb else None
        except Exception:
            return None

    # tous les règlements sur journaux banque, lettrés ou non, par (journal Odoo, pièce Sage)
    remises = defaultdict(list)   # -> [(client, règlement, écritures de sa lettre ou [])]
    for cl in clients:
        gl_l = defaultdict(list)
        for e in cl["ecritures"]:
            if e["lettre"]:
                gl_l[e["lettre"]].append(e)
        for e in cl["ecritures"]:
            if e["credit"] > 0 and e["journal"]:
                jid2 = journal_pour(e["journal"])
                if jid2 in cables:
                    remises[(jid2, e["piece"])].append((cl, e, gl_l.get(e["lettre"], []) if e["lettre"] else []))
    invs_pris = set()   # factures déjà couvertes par une remise
    regs_pris = set()   # règlements consommés (id() des dicts)
    today = _dt.date.today()
    # lignes de relevé déjà lettrées : si la remise y correspond, elle a été traitée autrement dans Odoo
    stmt_lettre = _q("account.bank.statement.line", "search_read",
                     [("company_id", "=", comp), ("is_reconciled", "=", True), ("amount", ">", 0),
                      ("date", ">=", (today - _dt.timedelta(days=400)).strftime("%Y-%m-%d"))],
                     fields=["date", "amount", "journal_id", "payment_ref"], limit=0)
    for (jid2, piece), items in sorted(remises.items(), key=lambda kv: kv[1][0][1]["date"]):
        total = round(sum(e["credit"] for _, e, _ in items), 2)
        try:
            dref = _dt.date.fromisoformat(items[0][1]["date"][:10])
        except Exception:
            continue
        cheque_like = any(RE_CHQ.search(e["lib"]) or RE_CB.search(e["lib"]) for _, e, _ in items)
        est_cb = all(RE_CB.search(e["lib"]) for _, e, _ in items)
        s_ok, par_brut = None, False
        for s2 in stmt:
            if s2["id"] in stmt_uses or s2["journal_id"][0] != jid2:
                continue
            try:
                ecart_j = abs((_dt.date.fromisoformat(str(s2["date"])[:10]) - dref).days)
            except Exception:
                continue
            if ecart_j > 15:
                continue
            b2 = brut_de(s2["payment_ref"])
            if b2 is not None and abs(b2 - total) < 0.005:
                s_ok, par_brut = s2, True
                break
            if abs(s2["amount"] - total) < 0.005 and (cheque_like or len(items) > 1):
                s_ok = s2
                break
        if s_ok is None:
            deja_lettre = None
            for s2 in stmt_lettre:
                if s2["journal_id"][0] != jid2:
                    continue
                try:
                    ecart_j = abs((_dt.date.fromisoformat(str(s2["date"])[:10]) - dref).days)
                except Exception:
                    continue
                b2 = brut_de(s2["payment_ref"])
                if ecart_j <= 15 and (abs(s2["amount"] - total) < 0.005 or (b2 is not None and abs(b2 - total) < 0.005)):
                    deja_lettre = s2
                    break
            if deja_lettre is not None:
                ouverts, en_paiement = [], False
                for cl, e, es in items:
                    for f in es:
                        i2 = invs.get(f["fac"]) if f["fac"] else None
                        if i2 and i2["state"] == "posted" and i2["payment_state"] in ("not_paid", "partial"):
                            ouverts.append("%s %s" % (cl["nom"][:20], f["fac"]))
                        if i2 and i2["payment_state"] == "in_payment":
                            en_paiement = True
                if en_paiement and not ouverts:
                    pass   # paiement Odoo existant à lettrer : logique classique (« lettrer le paiement existant »)
                else:
                    if ouverts:
                        anomalies.append("remise %s n°%s du %s (%.2f €) : la ligne de relevé du %s est DÉJÀ lettrée dans Odoo alors que %s reste(nt) ouverte(s) — à vérifier dans Odoo"
                                         % (journal_nom(jid2), piece, items[0][1]["date"][:10], total, str(deja_lettre["date"])[:10], ", ".join(ouverts)[:120]))
                    else:
                        deja += len(items)
                    for cl, e, es in items:
                        regs_pris.add(id(e))
                        for f in es:
                            i2 = invs.get(f["fac"]) if f["fac"] else None
                            if i2:
                                invs_pris.add(i2["id"])
                    continue
        if s_ok is None and not cheque_like:
            continue   # virement isolé : logique classique
        if par_brut:
            est_cb = True
        # composition par (client, lettre) : plusieurs chèques d'une même lettre s'additionnent
        par_lettre = {}
        for cl, e, es in items:
            key = (cl["code"], e["lettre"] or ("~%d" % id(e)))
            par_lettre.setdefault(key, {"cl": cl, "regs": [], "es": es})["regs"].append(e)
        lots, pay_exist, detail, deja_rem, sans_lettre = [], [], [], 0, 0.0
        for key, g in par_lettre.items():
            cl, regs_g, es = g["cl"], g["regs"], g["es"]
            credit_g = round(sum(e["credit"] for e in regs_g), 2)
            typ = "CB" if (est_cb or any(RE_CB.search(e["lib"]) for e in regs_g)) else ("chèque" if any(RE_CHQ.search(e["lib"]) for e in regs_g) else "règlement")
            if not es:
                sans_lettre += credit_g
                detail.append("%s %.2f € — %s : non lettré dans Sage, à traiter dans le widget" % (typ, credit_g, cl["nom"][:28]))
                continue
            facs2 = [f for f in es if f["fac"] and f["debit"] > 0]
            etats2 = [invs.get(f["fac"]) for f in facs2]
            ouv = [i for i in etats2 if i and i["state"] == "posted" and i["payment_state"] in ("not_paid", "partial") and i["id"] not in invs_pris]
            enc = [i for i in etats2 if i and i["payment_state"] == "in_payment" and i["id"] in pay_par_inv]
            for i in enc:
                pid = pay_par_inv[i["id"]]["id"]
                if pid not in pay_exist:
                    pay_exist.append(pid)
                    detail.append("%s %.2f € — %s : paiement %s déjà saisi, sera rapproché" % (typ, credit_g, cl["nom"][:28], pay_par_inv[i["id"]]["name"]))
            for e in regs_g:
                regs_pris.add(id(e))
            if not ouv:
                if not enc:
                    deja_rem += 1
                    sans_lettre += credit_g if not any(i and i["payment_state"] in ("paid", "reversed") for i in etats2) else 0.0
                continue
            residu = round(sum(i["amount_residual"] for i in ouv), 2)
            montant = round(min(credit_g, residu), 2)
            if montant <= 0:
                deja_rem += 1
                continue
            lots.append({"ids": [i["id"] for i in ouv], "amount": montant, "client": cl["nom"][:30], "lettre": key[1]})
            for i in ouv:
                invs_pris.add(i["id"])
            autres = [f for f in es if f["credit"] > 0 and f not in regs_g and not (RE_CHQ.search(f["lib"]) or RE_CB.search(f["lib"]))]
            detail.append("%s %.2f € — %s%s" % (typ, credit_g, cl["nom"][:28],
                          (" (+ %s à lettrer dans Odoo)" % ", ".join("%s %.2f €" % (f["lib"][:18], f["credit"]) for f in autres)) if autres else ""))
        if not lots and not pay_exist:
            deja += deja_rem
            continue
        somme = round(sum(lo["amount"] for lo in lots), 2)
        montant_exist = round(sum(pay_par_inv[i]["amount"] for i in pay_par_inv if pay_par_inv[i]["id"] in pay_exist), 2) if pay_exist else 0.0
        couvert = round(somme + montant_exist, 2)
        base = {"ligne": {"date": items[0][1]["date"][:10], "piece": str(piece), "credit": 0.0, "debit": somme,
                          "lib": "Remise %s n°%s du %s — %d règlement(s), %.2f €" % ("CB" if est_cb else "chèques", piece, items[0][1]["date"][:10], len(items), total)},
                "journal_id": jid2, "lots": lots, "ids": [i for lo in lots for i in lo["ids"]], "pay_ids": pay_exist,
                "total": total, "cb": bool(est_cb)}
        if s_ok is not None:
            stmt_uses.add(s_ok["id"])
            net = round(s_ok["amount"], 2)
            det = ["relevé %s : %s (%.2f €)" % (str(s_ok["date"])[:10], (s_ok["payment_ref"] or "")[:45], net)]
            reste = round(total - couvert, 2)
            if est_cb and abs(total - net) >= 0.005:
                det.append("commission bancaire %.2f € passée en frais bancaires" % round(total - net, 2))
            if abs(reste) < 0.05:
                base.update({"type": "remise", "stmt_moves": [s_ok["move_id"][0]], "net": net, "detail": det + detail})
            else:
                det.append("⚠ %.2f € de cette remise non expliqués (non lettrés dans Sage ou déjà réglés autrement) : paiements créés, rapprochement à finir dans le widget" % reste)
                base.update({"type": "remise_partielle", "stmt_moves": [s_ok["move_id"][0]], "net": net, "detail": det + detail})
        else:
            if (today - dref).days > 45:
                anomalies.append("remise %s n°%s du %s (%.2f €) : introuvable sur le relevé Odoo (±15 j) — à vérifier"
                                 % (journal_nom(jid2), piece, items[0][1]["date"][:10], total))
                for lo in lots:
                    for i in lo["ids"]:
                        invs_pris.discard(i)
                for cl, e, es in items:
                    regs_pris.discard(id(e))
                continue
            base.update({"type": "remise_attente",
                         "detail": ["pas encore sur le relevé Odoo : paiements créés et regroupés en « Dépôt par lot » n°%s — le rapprochement se fera à l'arrivée de la ligne" % piece] + detail})
        props.append(base)
    for cl in clients:
        groupes = defaultdict(list)
        for e in cl["ecritures"]:
            if e["lettre"]:
                groupes[e["lettre"]].append(e)
        for lettre, es in sorted(groupes.items()):
            sd = round(sum(e["debit"] for e in es), 2)
            sc = round(sum(e["credit"] for e in es), 2)
            facs = [e for e in es if e["fac"] and e["debit"] > 0
                    and not (invs.get(e["fac"]) and invs[e["fac"]]["id"] in invs_pris)]
            regs = [e for e in es if e["credit"] > 0 and id(e) not in regs_pris]
            if not facs or not regs:
                continue
            if abs(sd - sc) > 0.01:
                anomalies.append("%s lettre %s : débits %.2f ≠ crédits %.2f (lettrage partiel ?)"
                                 % (cl["code"], lettre, sd, sc))
                continue
            date_reg = max(e["date"] for e in regs)
            jids_regs = {journal_pour(e["journal"]) for e in regs}
            if any(j2 not in cables for j2 in jids_regs):
                hors = ", ".join(sorted({journal_nom(j2) for j2 in jids_regs if j2 not in cables}))
                anomalies.append("%s lettre %s : règlement via « %s » — suivi par le circuit CB/chèques d'Odoo, non traité ici"
                                 % (cl["code"], lettre, hors))
                continue
            jid = journal_pour(regs[-1]["journal"])
            # ── v2 : le groupe entier se réconcilie-t-il avec des lignes de relevé ? ──
            etats = [invs.get(e["fac"]) for e in facs]
            if all(i and i["state"] == "posted" for i in etats) \
               and not any(i["payment_state"] in ("paid", "reversed") for i in etats):
                matches = []
                for e in regs:
                    s2 = stmt_pour(journal_pour(e["journal"]), e["credit"], e["date"])
                    if s2 is None:
                        matches = None
                        break
                    matches.append(s2)
                ouverts_ok = all(
                    i["payment_state"] != "not_paid" or abs(i["amount_residual"] - e2["debit"]) < 0.01
                    for i, e2 in zip(etats, facs))
                a_payer = [i["id"] for i in etats if i["payment_state"] in ("not_paid", "partial")]
                pay_ids = sorted({pay_par_inv[i["id"]]["id"] for i in etats
                                  if i["payment_state"] == "in_payment" and i["id"] in pay_par_inv})
                complet = all(i["payment_state"] != "in_payment" or i["id"] in pay_par_inv
                              for i in etats) and (a_payer or pay_ids)
                if matches and ouverts_ok and complet:
                    for s2 in matches:
                        stmt_uses.add(s2["id"])
                    total = round(sum(e2["debit"] for e2 in facs), 2)
                    libs = ", ".join(e2["fac"] for e2 in facs)
                    props.append({
                        "ligne": {"date": date_reg, "piece": lettre, "credit": 0.0,
                                  "lib": "%s — %s (lettre %s)" % (libs[:40], cl["nom"][:24], lettre),
                                  "debit": total},
                        "type": "releve", "ids": a_payer, "pay_ids": pay_ids,
                        "stmt_moves": [s2["move_id"][0] for s2 in matches],
                        "journal_id": jid,
                        "detail": ["relevé %s : %s (%.2f €)" % (str(s2["date"])[:10],
                                   (s2["payment_ref"] or "")[:45], s2["amount"]) for s2 in matches]})
                    continue
            for e in facs:
                inv = invs.get(e["fac"])
                if not inv or inv["state"] != "posted":
                    anomalies.append("%s : facture %s introuvable dans Odoo" % (cl["code"], e["fac"]))
                    continue
                if inv["payment_state"] in ("paid", "reversed"):
                    deja += 1
                    continue
                lib = "%s — %s (lettre %s)" % (e["fac"], cl["nom"][:30], lettre)
                pay = pay_par_inv.get(inv["id"])
                if inv["payment_state"] == "in_payment" and pay:
                    props.append({"ligne": {"date": date_reg, "lib": lib, "piece": lettre,
                                            "debit": round(pay["amount"], 2), "credit": 0.0},
                                  "type": "paiements", "ids": [pay["id"]], "journal_id": jid,
                                  "detail": ["paiement %s (%.2f €) réglé le %s"
                                             % (pay["name"], pay["amount"], date_reg)]})
                elif inv["payment_state"] in ("not_paid", "partial"):
                    montant = min(e["debit"], round(inv["amount_residual"], 2))
                    if montant <= 0:
                        deja += 1
                        continue
                    props.append({"ligne": {"date": date_reg, "lib": lib, "piece": lettre,
                                            "debit": montant, "credit": 0.0},
                                  "type": "facture", "ids": [inv["id"]], "journal_id": jid,
                                  "detail": ["aucun paiement saisi dans Odoo — cocher pour créer le paiement de %.2f € au %s et lettrer"
                                             % (montant, date_reg)]})
                else:
                    deja += 1
    return props, anomalies, deja


RAPPRO_PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Import rapprochement Sage</title><style>
body{font-family:system-ui,sans-serif;background:#f1f5f9;margin:0;padding:24px;color:#0f172a;}
.card{background:#fff;border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,.09);max-width:900px;margin:0 auto;padding:24px;}
h1{font-size:20px;margin:0 0 4px;}p.sub{color:#64748b;font-size:13px;margin:0 0 16px;}
label{display:block;font-weight:700;font-size:12.5px;color:#334155;margin:10px 0 4px;}
select,input[type=file]{padding:8px;border:1.5px solid #cbd5e1;border-radius:9px;font-size:14px;}
button{border:none;border-radius:9px;background:#0f172a;color:#fff;font-weight:800;font-size:13px;padding:10px 16px;cursor:pointer;margin-top:14px;}
button:hover{filter:brightness(1.2);}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px;}
th{background:#0f172a;color:#fff;padding:6px 8px;text-align:left;font-size:11.5px;}
td{border-bottom:1px solid #e2e8f0;padding:6px 8px;vertical-align:top;}
.ok{color:#166534;font-weight:700;}.crt{color:#1d4ed8;font-weight:700;}.ko{color:#b91c1c;font-weight:700;}
.note{background:#fefce8;border:1.5px solid #fde68a;border-radius:10px;padding:9px 12px;font-size:12.5px;margin:12px 0;}
a.retour{font-size:12.5px;}
#att{display:none;position:fixed;inset:0;background:rgba(241,245,249,.85);z-index:50;
     align-items:center;justify-content:center;flex-direction:column;gap:14px;}
#att .rond{width:46px;height:46px;border:5px solid #cbd5e1;border-top-color:#0f172a;
     border-radius:50%;animation:tourne 0.9s linear infinite;}
#att .txt{font-weight:800;color:#0f172a;font-size:15px;}
@keyframes tourne{to{transform:rotate(360deg);}}
</style></head><body>
<div id="att"><div class="rond"></div><div class="txt" id="attTxt">Analyse du fichier…</div></div>
<script>
document.addEventListener('submit', function(ev){
  var f = ev.target;
  var b = f.querySelector('button[type=submit]');
  var texte = (f.action || '').indexOf('applique') >= 0 ? 'Application du lettrage…' : 'Analyse du fichier…';
  document.getElementById('attTxt').textContent = texte;
  document.getElementById('att').style.display = 'flex';
  if(b){ b.disabled = true; }
}, true);
</script>
<div class="card">
<h1>🏦 Import du rapprochement bancaire Sage</h1>
<p class="sub">Déposez l'état « Rapprochement bancaire » de Sage (imprimé vers Excel). Les
encaissements pointés passent les paiements et factures Odoo à « Payé », à la date du pointage.
Sociétés concernées : SARL Maquignon, Châtel'Granulats et Carrière d'Haims (Distri Béton
reste rapprochée dans Odoo).</p>
__CORPS__
<p style="margin-top:16px;"><a class="retour" href="./?token=__TOKEN__">← Retour à l'export Sage</a></p>
</div></body></html>"""


@bp.route("/rappro", methods=["GET"])
def rappro_page():
    _check_token()
    token = request.args.get("token", "")
    corps = ("""<form method="post" action="rappro/analyse?token=%s" enctype="multipart/form-data">
<label>Société</label><select name="societe">
<option value="1">SARL MAQUIGNON</option><option value="3">CHATEL'GRANULATS</option><option value="4">CARRIERE D'HAIMS</option></select>
<label>Fichier Sage (.xlsx) — état de rapprochement bancaire OU grand-livre des tiers avec lettrage (le type est détecté automatiquement)</label><input type="file" name="fichier" accept=".xlsx" required/>
<br/><button type="submit">🔎 Analyser</button></form>""" % token)
    return Response(RAPPRO_PAGE.replace("__CORPS__", corps).replace("__TOKEN__", token),
                    mimetype="text/html")


@bp.route("/rappro/analyse", methods=["POST"])
def rappro_analyse():
    _check_token()
    token = request.args.get("token", "")
    comp = int(request.form["societe"])
    buf = io.BytesIO(request.files["fichier"].read())
    if _gl_detecte(buf):
        # ── Grand-livre des tiers : lettrage par lettres ──
        buf.seek(0)
        clients = _gl_parse(buf)
        props, anomalies, deja = _gl_analyse(comp, clients)
        rows = ""
        for i, pr in enumerate(props):
            l = pr["ligne"]
            if pr["type"] == "releve":
                statut = "<span class='ok'>✓ rapprocher avec le relevé bancaire</span>"
                coche = "checked"
            elif pr["type"] == "remise":
                statut = "<span class='ok'>✓ remise groupée : %d paiement(s) créé(s) et rapprochés avec le relevé</span>" % len(pr["lots"])
                coche = "checked"
            elif pr["type"] == "remise_attente":
                statut = "<span style='color:#1d4ed8;font-weight:700;'>📦 remise pas encore en banque : %d paiement(s) + dépôt par lot</span>" % len(pr["lots"])
                coche = "checked"
            elif pr["type"] == "remise_partielle":
                statut = "<span style='color:#b45309;font-weight:700;'>◐ remise partiellement expliquée : %d paiement(s) créé(s), rapprochement à finir dans le widget</span>" % len(pr["lots"])
                coche = "checked"
            elif pr["type"] == "paiements":
                statut = "<span class='ok'>✓ lettrer le paiement existant</span>"
                coche = "checked"
            else:
                # lettré dans Sage mais AUCUN paiement saisi dans Odoo : oubli
                # de saisie probable -> alerte, décochée par défaut
                statut = ("<span style='color:#b45309;font-weight:700;'>⚠ paiement absent d'Odoo (oubli de saisie ?)</span>"
                          "<br/><span style='color:#0f172a;font-weight:700;'>☐ cochez la case à gauche pour confirmer la création du paiement</span>")
                coche = ""
            rows += ("<tr><td><input type='checkbox' name='sel' value='%d' %s/></td>"
                     "<td>%s</td><td>%s</td><td style='text-align:right;'>%.2f €</td>"
                     "<td>%s<div style='font-size:11.5px;color:#64748b;'>%s</div></td></tr>"
                     % (i, coche, l["date"], l["lib"][:60], l["debit"], statut, "<br/>".join(pr["detail"])))
        note_ano = ""
        if anomalies:
            note_ano = ("<div class='note'>⚠ Hors lettrage automatique :<br/>%s</div>"
                        % "<br/>".join(anomalies[:30]))
        js = _q("account.journal", "search", [("company_id", "=", comp), ("type", "=", "bank")], limit=1)
        if not props:
            corps = ("<div class='note'>Grand-livre lu : <b>%d</b> clients · <b>%d</b> facture(s) déjà à jour "
                     "dans Odoo · rien de nouveau à lettrer.</div>%s" % (len(clients), deja, note_ano))
        else:
            n_alertes = sum(1 for p in props if p["type"] == "facture")
            note_al = (" · <b style='color:#b45309;'>%d alerte(s) : lettré dans Sage sans paiement saisi dans Odoo</b>" % n_alertes) if n_alertes else ""
            corps = ("""<div class="note">Grand-livre des tiers lu : <b>%d</b> clients ·
<b>%d</b> facture(s) à passer « Payé » · %d déjà à jour dans Odoo%s.</div>%s
<form method="post" action="applique?token=%s">
<input type="hidden" name="societe" value="%d"/>
<input type="hidden" name="journal" value="%d"/>
<input type="hidden" name="props" value='%s'/>
<input type="hidden" name="stats" value='%s'/>
<div style="margin:6px 0;font-size:13px;"><a href="#" onclick="document.querySelectorAll('input[name=sel]:not(:disabled)').forEach(function(c){c.checked=true;});majN();return false;">☑ Tout cocher</a> · <a href="#" onclick="document.querySelectorAll('input[name=sel]').forEach(function(c){c.checked=false;});majN();return false;">☐ Tout décocher</a></div>
<table><tr><th></th><th>Réglée le</th><th>Facture — client</th><th>Montant</th><th>Action</th></tr>%s</table>
<button type="submit" id="btn-appliquer">✅ Appliquer le lettrage (%d)</button>
<script>function majN(){var n=document.querySelectorAll('input[name=sel]:checked').length;var b=document.getElementById('btn-appliquer');if(b){b.textContent='✅ Appliquer le lettrage ('+n+' coché'+(n>1?'s':'')+')';b.disabled=(n===0);}}
document.querySelectorAll('input[name=sel]').forEach(function(c){c.addEventListener('change',majN);});majN();</script></form>"""
                     % (len(clients), len(props), deja, note_al, note_ano, token, comp,
                        js[0] if js else 0, _json.dumps(props).replace("'", "&#39;"),
                        _json.dumps({"deja": deja, "ano": len(anomalies)}),
                        rows, len(props)))
        return Response(RAPPRO_PAGE.replace("__CORPS__", corps).replace("__TOKEN__", token),
                        mimetype="text/html")
    buf.seek(0)
    lignes, date_rappro = _rappro_parse(buf)
    if not lignes:
        return Response(RAPPRO_PAGE.replace("__CORPS__", "<p class='ko'>Aucune écriture 512 trouvée dans ce fichier — est-ce bien l'état « Rapprochement bancaire » imprimé vers Excel ?</p>").replace("__TOKEN__", token), mimetype="text/html")
    journal = _rappro_journal(comp, lignes[0]["compte"])
    props, ignores = _rappro_analyse(comp, lignes, journal_id=journal["id"] if journal else None)
    rows = ""
    for i, pr in enumerate(props):
        l = pr["ligne"]
        if pr["type"] == "paiements":
            statut = "<span class='ok'>✓ %s paiement(s) reconnu(s)</span>" % len(pr["ids"])
        elif pr["type"] == "facture":
            statut = "<span class='crt'>➕ créer le paiement sur la facture</span>"
        else:
            statut = "<span class='ko'>? non reconnu — à traiter dans Odoo</span>"
        det = "<br/>".join(pr["detail"]) or "—"
        coche = "checked" if pr["type"] != "inconnu" else "disabled"
        rows += ("<tr><td><input type='checkbox' name='sel' value='%d' %s/></td>"
                 "<td>%s</td><td>%s</td><td style='text-align:right;'>%.2f €</td>"
                 "<td>%s<div style='font-size:11.5px;color:#64748b;'>%s</div></td></tr>"
                 % (i, coche, l["date"], l["lib"][:48], l["debit"], statut, det))
    n_auto = sum(1 for p in props if p["type"] != "inconnu")
    corps = ("""<div class="note">Journal identifié : <b>%s</b> · rapprochement du <b>%s</b> ·
%d encaissement(s) — <b>%d</b> lettrable(s) automatiquement · %d décaissement(s) ignoré(s) (fournisseurs).</div>
<form method="post" action="applique?token=%s">
<input type="hidden" name="societe" value="%d"/>
<input type="hidden" name="journal" value="%d"/>
<input type="hidden" name="props" value='%s'/>
<input type="hidden" name="stats" value='%s'/>
<table><tr><th></th><th>Date</th><th>Libellé Sage</th><th>Montant</th><th>Proposition</th></tr>%s</table>
<button type="submit">✅ Appliquer le lettrage (%d)</button></form>"""
             % (journal["name"] if journal else "?", date_rappro or "?", len(props), n_auto,
                len(ignores), token, comp, journal["id"] if journal else 0,
                _json.dumps(props).replace("'", "&#39;"),
                _json.dumps({"inconnu": len(props) - n_auto, "ignores": len(ignores)}),
                rows, n_auto))
    return Response(RAPPRO_PAGE.replace("__CORPS__", corps).replace("__TOKEN__", token),
                    mimetype="text/html")


def _rappro_job_path(job):
    import tempfile
    return os.path.join(tempfile.gettempdir(), "rappro_%s.json" % re.sub(r"[^a-f0-9]", "", job)[:32])


def _rappro_job_save(job, data):
    with io.open(_rappro_job_path(job), "w", encoding="utf-8") as f:
        f.write(_json.dumps(data))


def _rappro_job_load(job):
    try:
        with io.open(_rappro_job_path(job), encoding="utf-8") as f:
            return _json.loads(f.read())
    except Exception:
        return None


def _rappro_run(job, comp, journal, retenus, props, stats):
    """Tâche de fond : lettrage puis récapitulatif HTML, état écrit dans un fichier lu par /rappro/etat."""
    avance = {"n": 0, "total": len(retenus)}
    import threading as _th

    def tick():
        while not avance.get("fini"):
            _rappro_job_save(job, {"etat": "en_cours", "n": avance.get("n", 0), "total": avance["total"]})
            _th.Event().wait(2)
    _th.Thread(target=tick, daemon=True).start()
    try:
        faits, erreurs = _rappro_applique(comp, journal, retenus, avance=avance)
        corps = _rappro_recap(retenus, props, stats, faits, erreurs)
        avance["fini"] = True
        _rappro_job_save(job, {"etat": "fini", "corps": corps})
    except Exception as e:  # noqa: BLE001
        avance["fini"] = True
        _rappro_job_save(job, {"etat": "erreur", "corps": "<p class='ko'>❌ Erreur pendant le lettrage : %s</p>"
                               "<p>Les lignes déjà traitées sont conservées : relancez l'analyse, elles apparaîtront « déjà à jour ».</p>" % str(e)[:400]})


@bp.route("/rappro/applique", methods=["POST"])
def rappro_applique():
    _check_token()
    token = request.args.get("token", "")
    comp = int(request.form["societe"])
    props = _json.loads(request.form["props"])
    sel = {int(i) for i in request.form.getlist("sel")}
    retenus = [p for i, p in enumerate(props) if i in sel and p["type"] != "inconnu"]
    journal = _q("account.journal", "read", [int(request.form["journal"])],
                 fields=["name", "code", "default_account_id"])[0]
    try:
        stats = _json.loads(request.form.get("stats") or "{}")
    except Exception:
        stats = {}
    import uuid
    job = uuid.uuid4().hex
    _rappro_job_save(job, {"etat": "en_cours", "n": 0, "total": len(retenus)})
    _threading.Thread(target=_rappro_run, args=(job, comp, journal, retenus, props, stats), daemon=True).start()
    return Response('<meta http-equiv="refresh" content="0;url=etat?token=%s&job=%s">' % (token, job), mimetype="text/html")


@bp.route("/rappro/etat", methods=["GET"])
def rappro_etat():
    _check_token()
    token = request.args.get("token", "")
    job = request.args.get("job", "")
    d = _rappro_job_load(job)
    if not d:
        corps = "<p class='ko'>Tâche introuvable (serveur redémarré ?). Relancez l'analyse : ce qui a été lettré apparaîtra « déjà à jour ».</p>"
        return Response(RAPPRO_PAGE.replace("__CORPS__", corps).replace("__TOKEN__", token), mimetype="text/html")
    if d.get("etat") == "en_cours":
        pct = int(100 * d.get("n", 0) / d["total"]) if d.get("total") else 0
        corps = ("<meta http-equiv='refresh' content='4'>"
                 "<p>⏳ <b>Lettrage en cours…</b> %d / %d groupe(s) traité(s)</p>"
                 "<div style='background:#e5e7eb;border-radius:8px;height:16px;overflow:hidden;max-width:520px;'>"
                 "<div style='background:#16a34a;height:16px;width:%d%%;'></div></div>"
                 "<p class='note'>Cette page se rafraîchit toute seule. Vous pouvez la laisser ouverte ou revenir plus tard avec ce lien.</p>"
                 % (d.get("n", 0), d.get("total", 0), pct))
        return Response(RAPPRO_PAGE.replace("__CORPS__", corps).replace("__TOKEN__", token), mimetype="text/html")
    return Response(RAPPRO_PAGE.replace("__CORPS__", d.get("corps", "")).replace("__TOKEN__", token), mimetype="text/html")


def _rappro_recap(retenus, props, stats, faits, erreurs):
    n_lettres = sum(1 for p in retenus if p["type"] == "paiements")
    n_releves = sum(1 for p in retenus if p["type"] == "releve")
    n_crees = sum(1 for p in retenus if p["type"] == "facture")
    n_remises = sum(1 for p in retenus if p["type"] == "remise")
    n_rem_att = sum(1 for p in retenus if p["type"] == "remise_attente")
    n_rem_part = sum(1 for p in retenus if p["type"] == "remise_partielle")
    ecartes = len(props) - len(retenus)
    lignes_recap = ["<b>%d</b> appliqué(s) — factures passées « Payé »" % faits]
    if n_lettres:
        lignes_recap.append("dont %d lettrage(s) de paiements déjà saisis" % n_lettres)
    if n_releves:
        lignes_recap.append("dont %d groupe(s) rapprochés avec les relevés bancaires" % n_releves)
    if n_remises:
        lignes_recap.append("dont %d remise(s) de chèques / CB rapprochée(s) avec le relevé" % n_remises)
    if n_rem_part:
        lignes_recap.append("dont %d remise(s) partiellement expliquée(s) — paiements créés, à finir dans le widget de rapprochement" % n_rem_part)
    if n_rem_att:
        lignes_recap.append("dont %d remise(s) en attente de relevé (dépôt par lot créé — à rapprocher dans le widget à l'arrivée de la ligne)" % n_rem_att)
    if n_crees:
        lignes_recap.append("<span style='color:#b45309;'>⚠ dont %d paiement(s) créé(s) faute de saisie dans Odoo (oubli à vérifier)</span>" % n_crees)
    if stats.get("deja"):
        lignes_recap.append("%d facture(s) déjà à jour dans Odoo (rien à faire)" % stats["deja"])
    if ecartes:
        lignes_recap.append("%d proposition(s) laissée(s) de côté (non cochées ou non reconnues)" % ecartes)
    if stats.get("inconnu"):
        lignes_recap.append("%d ligne(s) non reconnue(s) — à traiter dans Odoo" % stats["inconnu"])
    if stats.get("ignores"):
        lignes_recap.append("%d décaissement(s) ignoré(s) (fournisseurs)" % stats["ignores"])
    if stats.get("ano"):
        lignes_recap.append("%d groupe(s) hors lettrage automatique (à vérifier dans Sage)" % stats["ano"])
    if erreurs:
        lignes_recap.append("<span class='ko'>%d erreur(s) — détail ci-dessous</span>" % len(erreurs))
    corps = ("<p class='ok'>✅ Lettrage appliqué.</p><div class='note'>📋 Récapitulatif :<br/>• "
             + "<br/>• ".join(lignes_recap) + "</div>")
    if erreurs:
        corps += "<div class='note'>⚠ À traiter manuellement :<br/>%s</div>" % "<br/>".join(erreurs)
    return corps
