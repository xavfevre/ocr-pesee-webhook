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

_conn = {}


def _q(model, method, *params, **kw):
    if "uid" not in _conn:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        _conn["uid"] = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        _conn["models"] = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
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


def _ddmmyy(iso):
    return (iso[8:10] + iso[5:7] + iso[2:4]) if iso else ""


def _piece(numero):
    chiffres = "".join(c for c in (numero or "") if c.isdigit())
    return chiffres[-7:] if chiffres else ""


def _referentiels(line_rows):
    acc_ids = list({l["account_id"][0] for l in line_rows if l["account_id"]})
    part_ids = list({l["partner_id"][0] for l in line_rows if l["partner_id"]})
    ana_ids = set()
    for l in line_rows:
        for k in (l.get("analytic_distribution") or {}):
            if str(k).isdigit():
                ana_ids.add(int(k))
    comptes = {a["id"]: a for a in _q("account.account", "read", acc_ids,
                                      fields=["code", "name"])} if acc_ids else {}
    partenaires = {p["id"]: p for p in _q("res.partner", "read", part_ids,
                                          fields=["ref", "name"])} if part_ids else {}
    analytiques = {a["id"]: a["name"] for a in _q("account.analytic.account", "read",
                                                  list(ana_ids), fields=["name"])} if ana_ids else {}
    return comptes, partenaires, analytiques


def _ana_libelle(line, analytiques):
    """Fidèle à l'action historique : une clé composée (« 14,2 ») faisait
    échouer son try/except → analytique vide pour toute la ligne."""
    dist = line.get("analytic_distribution") or {}
    if any(not str(k).isdigit() for k in dist):
        return ""
    return " | ".join(n for n in (analytiques.get(int(k), "") for k in dist) if n)


def _export_ventes(journal, du, au, base_url, clients_vus):
    """Format action 1459 : écritures groupées par (compte, analytique)."""
    moves = _q("account.move", "search_read",
               [("journal_id", "=", journal["id"]), ("state", "=", "posted"),
                 ("date", ">=", du), ("date", "<=", au)],
               fields=["name", "date", "invoice_date_due"], limit=0)  # ordre par défaut d'Odoo, comme l'action 1459
    if not moves:
        return None
    mids = [m["id"] for m in moves]
    lines = _q("account.move.line", "search_read", [("move_id", "in", mids)],
               fields=["move_id", "account_id", "debit", "credit", "partner_id",
                       "ref", "analytic_distribution"], limit=0, order="id asc")
    comptes, partenaires, analytiques = _referentiels(lines)
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
                                "debit": 0, "credit": 0}
            groupes[cle]["debit"] += debit
            groupes[cle]["credit"] += credit
        for (code_compte, ana), g in groupes.items():
            libelle = "%s %s" % (numero, g["nom"])
            if g["debit"] > 0 and g["credit"] > 0:
                montants = [(g["debit"], 0), (0, g["credit"])]
            else:
                montants = [(g["debit"], g["credit"])]
            for debit, credit in montants:
                base = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;" % (
                    piece, numero, journal["code"] or "", d_fac,
                    g["code_client"], g["ref_ligne"], g["nom"],
                    code_compte, libelle, d_ech, debit, credit, g["url"], ana)
                out.append(base + "G")
                if ana and code_compte.startswith("7"):
                    out.append(base + "A")
    return "\n".join(out)


def _export_caisse(journal, du, au, clients_vus):
    """Format action 1671 : ligne à ligne (tickets comptoir)."""
    lines = _q("account.move.line", "search_read",
               [("journal_id", "=", journal["id"]), ("parent_state", "=", "posted"),
                 ("date", ">=", du), ("date", "<=", au)],
               fields=["move_id", "date", "account_id", "debit", "credit", "partner_id",
                       "name", "analytic_distribution"], limit=0,
               order="date asc, move_id asc, id asc")
    if not lines:
        return None
    mids = list({l["move_id"][0] for l in lines})
    moves = {m["id"]: m for m in _q("account.move", "read", mids,
                                    fields=["name", "invoice_date_due", "partner_id"])}
    comptes, partenaires, analytiques = _referentiels(lines)
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
        base = "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;;1;%s;" % (
            piece, numero, journal["code"] or "", d_fac, code_client, numero, nom,
            code_compte, libelle, d_ech, l["debit"] or 0, l["credit"] or 0, ana)
        out.append(base + "G")
        if ana and code_compte.startswith("7"):
            out.append(base + "A")
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
    js = _q("account.journal", "search_read",
            [("company_id", "=", comp), ("type", "in", ["sale", "cash", "bank"])],
            fields=["name", "code", "type"], order="type, id")
    pos = _q("pos.config", "search_read", [("company_id", "=", comp)],
             fields=["journal_id"])
    pos_ids = {p["journal_id"][0] for p in pos if p["journal_id"]}
    deja = {j["id"] for j in js}
    manquants = [i for i in pos_ids if i not in deja]
    if manquants:
        js += _q("account.journal", "read", manquants, fields=["name", "code", "type"])
    for j in js:
        j["format_caisse"] = j["type"] == "cash" or j["id"] in pos_ids
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
    acc_ids = list({l["account_id"][0] for l in lines if l["account_id"]})
    codes = {}
    for i in range(0, len(acc_ids), 800):
        for a in _q("account.account", "read", acc_ids[i:i + 800], fields=["code"]):
            codes[a["id"]] = a["code"] or ""
    for l in lines:
        jid = l["journal_id"][0]
        a = agg.setdefault(jid, {"nlignes": 0, "debit": 0.0, "pieces": set()})
        a["nlignes"] += 1
        a["debit"] += l["debit"] or 0
        a["pieces"].add(l["move_id"][0])
        if l["partner_id"] and codes.get(l["account_id"] and l["account_id"][0], "").startswith("411"):
            clients.add(l["partner_id"][0])
    n_nouveaux = 0
    if clients:
        ps = _q("res.partner", "read", list(clients),
                fields=["ref", "x_sage_envoye_le", "parent_id"])
        n_nouveaux = sum(1 for p in ps if p["ref"] and not p["x_sage_envoye_le"]
                         and not p["parent_id"])
    return agg, n_nouveaux


TYPES = {"sale": "Ventes", "bank": "Banque", "cash": "Caisse"}

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Export comptable Sage</title><style>
body{font-family:system-ui,sans-serif;background:#f1f5f9;margin:0;padding:24px;color:#0f172a;}
.card{background:#fff;border-radius:14px;box-shadow:0 1px 6px rgba(0,0,0,.09);max-width:760px;margin:0 auto;padding:24px;}
h1{font-size:20px;margin:0 0 4px;}p.sub{color:#64748b;font-size:13px;margin:0 0 16px;}
form.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:end;margin-bottom:16px;}
label{display:block;font-weight:700;font-size:12.5px;color:#334155;margin-bottom:3px;}
select{padding:8px;border:1.5px solid #cbd5e1;border-radius:9px;font-size:14px;}
button,a.btn{border:none;border-radius:9px;background:#0f172a;color:#fff;font-weight:800;font-size:13px;
padding:9px 14px;cursor:pointer;text-decoration:none;display:inline-block;}
button:hover,a.btn:hover{filter:brightness(1.2);}
a.btn.sec{background:#e2e8f0;color:#0f172a;}
table{border-collapse:collapse;width:100%;font-size:13.5px;}
th{background:#0f172a;color:#fff;padding:7px 9px;text-align:left;font-size:12px;}
td{border-bottom:1px solid #e2e8f0;padding:7px 9px;}
td.num{text-align:right;font-variant-numeric:tabular-nums;}
.nc{background:#fefce8;border:1.5px solid #fde68a;border-radius:10px;padding:10px 13px;margin:14px 0;font-size:13.5px;font-weight:600;color:#713f12;}
.chk{display:flex;gap:8px;align-items:center;font-size:13px;font-weight:600;color:#334155;margin:10px 0;}
</style></head><body><div class="card">
<h1>📤 Export comptable Sage</h1>
<p class="sub">Fichiers d'écritures au format d'import du cabinet (identiques aux exports
historiques) + fichier des nouveaux clients à créer dans Sage. Un dossier Sage par société.</p>
<form class="bar" method="get" action="">
<input type="hidden" name="token" value="__TOKEN__">
<div><label>Société</label><select name="societe" onchange="this.form.submit()">__SOCIETES__</select></div>
<div><label>Mois</label><select name="mois" onchange="this.form.submit()">__MOIS__</select></div>
</form>
__CORPS__
</div></body></html>"""


@bp.route("/", methods=["GET"])
def page():
    _check_token()
    token = request.args.get("token", "")
    comps = _q("res.company", "search_read", [], fields=["name"], order="id")
    comp = int(request.args.get("societe") or comps[0]["id"])
    d = date.today()
    mois_prec = f"{(d.year * 12 + d.month - 2) // 12:04d}-{(d.year * 12 + d.month - 2) % 12 + 1:02d}"
    mois = request.args.get("mois") or mois_prec
    du, au = _mois_bornes(mois)

    opts_soc = "".join('<option value="%s"%s>%s</option>' % (
        c["id"], " selected" if c["id"] == comp else "", c["name"]) for c in comps)
    opts_mois = ""
    for i in range(12):
        mm = d.year * 12 + d.month - 1 - i
        v = f"{mm // 12:04d}-{mm % 12 + 1:02d}"
        opts_mois += '<option value="%s"%s>%s</option>' % (v, " selected" if v == mois else "", v)

    journaux = _journaux(comp)
    agg, n_nouveaux = _apercu(comp, du, au, journaux)
    lignes_html = ""
    for j in journaux:
        a = agg.get(j["id"])
        if not a:
            continue
        url = "fichier?token=%s&journal=%s&mois=%s" % (token, j["id"], mois)
        lignes_html += ("<tr><td>%s</td><td>%s</td><td>%s</td><td class='num'>%s</td>"
                        "<td class='num'>%s</td><td class='num'>%.2f €</td>"
                        "<td><a class='btn sec' href='%s'>⬇ .txt</a></td></tr>" % (
                            j["code"] or "", j["name"], TYPES.get(j["type"], j["type"]),
                            len(a["pieces"]), a["nlignes"], a["debit"], url))
    if not lignes_html:
        corps = "<p><b>Aucune écriture validée sur %s pour cette société.</b></p>" % mois
    else:
        corps = ("<table><tr><th>Code</th><th>Journal</th><th>Type</th><th>Pièces</th>"
                 "<th>Lignes</th><th>Total débit</th><th></th></tr>%s</table>" % lignes_html)
        corps += ("<div class='nc'>👤 <b>%s</b> client(s) des écritures du mois jamais "
                  "transmis à Sage — inclus dans le ZIP (nouveaux_clients_*.txt).</div>" % n_nouveaux)
        corps += ("<form method='post' action='export?token=%s'>"
                  "<input type='hidden' name='societe' value='%s'>"
                  "<input type='hidden' name='mois' value='%s'>"
                  "<label class='chk'><input type='checkbox' name='marquer' value='1' checked> "
                  "Marquer les nouveaux clients comme transmis à Sage</label>"
                  "<button type='submit'>📦 Télécharger le ZIP complet (%s)</button>"
                  "</form>" % (token, comp, mois, mois))
    html = (PAGE.replace("__SOCIETES__", opts_soc).replace("__MOIS__", opts_mois)
                .replace("__TOKEN__", token).replace("__CORPS__", corps))
    return Response(html, mimetype="text/html")


def _fichier_journal(j, du, au, base_url, clients_vus):
    if j.get("format_caisse") or j["type"] == "cash":
        return _export_caisse(j, du, au, clients_vus), "export_tickets_comptoir"
    return _export_ventes(j, du, au, base_url, clients_vus), "export_journal"


@bp.route("/fichier", methods=["GET"])
def fichier():
    _check_token()
    jid = int(request.args["journal"])
    du, au = _mois_bornes(request.args["mois"])
    j = _q("account.journal", "read", [jid], fields=["name", "code", "type", "company_id"])[0]
    pos = _q("pos.config", "search_read", [("journal_id", "=", jid)], fields=["id"])
    j["format_caisse"] = j["type"] == "cash" or bool(pos)
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    contenu, prefixe = _fichier_journal(j, du, au, base_url, set())
    if contenu is None:
        return Response("Aucune écriture.", mimetype="text/plain; charset=utf-8", status=404)
    slug = j["company_id"][1].replace(" ", "_").replace("/", "_")
    nom = "%s_%s_%s_du_%s_au_%s.txt" % (prefixe, slug, j["name"].replace(" ", "_"),
                                        du.replace("-", ""), au.replace("-", ""))
    return Response(contenu.encode("cp1252", errors="replace"),
                    mimetype="text/plain; charset=windows-1252",
                    headers={"Content-Disposition": "attachment; filename=%s" % nom})


@bp.route("/export", methods=["POST"])
def export():
    _check_token()
    comp = int(request.form["societe"])
    du, au = _mois_bornes(request.form["mois"])
    marquer = request.form.get("marquer") == "1"
    comp_nom = _q("res.company", "read", [comp], fields=["name"])[0]["name"]
    base_url = _q("ir.config_parameter", "get_param", "web.base.url") or ""
    slug = comp_nom.replace(" ", "_").replace("/", "_")
    suffixe = "du_%s_au_%s" % (du.replace("-", ""), au.replace("-", ""))
    clients_vus = set()
    buf = io.BytesIO()
    n_fichiers = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for j in _journaux(comp):
            contenu, prefixe = _fichier_journal(j, du, au, base_url, clients_vus)
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
        return Response("Aucune écriture sur la période pour cette société.",
                        mimetype="text/plain; charset=utf-8", status=404)
    buf.seek(0)
    return Response(buf.read(), mimetype="application/zip",
                    headers={"Content-Disposition":
                             "attachment; filename=export_compta_%s_%s.zip" % (slug, suffixe)})
