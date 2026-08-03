"""
Webhook OCR - Bon de pesée → Worksheet FSM Odoo
Hébergement : Render.com (free tier)
OCR : Mistral Vision (mistral-large-latest)
Retour : XML-RPC Odoo write() sur la worksheet

Sécurité : si WEBHOOK_SECRET est défini, chaque requête doit fournir le token
(via le header "X-Webhook-Secret" ou le paramètre d'URL "?token=...").
"""

import os
import io
import json
import time
import base64
import socket
import re
import html as _htmllib
import hmac
import hashlib
import xmlrpc.client
from datetime import datetime, date
from functools import wraps
from urllib.parse import quote
from flask import Flask, request, jsonify

app = Flask(__name__)

# Évite qu'un appel XML-RPC ou Mistral ne bloque indéfiniment le worker Render.
socket.setdefaulttimeout(45)

# ─── CONFIG (variables d'environnement sur Render) ───────────────────────────
MISTRAL_API_KEY  = os.environ.get("MISTRAL_API_KEY")
ODOO_URL         = os.environ.get("ODOO_URL")          # ex: https://maquignon.odoo.com
ODOO_DB          = os.environ.get("ODOO_DB")            # ex: maquignon
ODOO_USER        = os.environ.get("ODOO_USER")          # email du compte technique
ODOO_PASSWORD    = os.environ.get("ODOO_PASSWORD")      # ⚠️ utiliser une CLÉ API dédiée, pas le mdp principal
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "") # token de sécurité (recommandé)
# Modèle réel de la worksheet FSM (NE PAS suffixer "_line").
ODOO_WORKSHEET_MODEL = os.environ.get("ODOO_WORKSHEET_MODEL", "x_project_task_worksheet_template_1")

# ─── MAPPING champs OCR → noms techniques Odoo ───────────────────────────────
FIELD_MAP = {
    "numero_bon"    : "x_studio_numero_bon",
    "client"        : "x_studio_client_pesee",
    "transporteur"  : "x_studio_transporteur",
    "produit"       : "x_studio_produit_pesee",
    "chantier"      : "x_studio_chantier_pesee",
    "vehicule"      : "x_studio_vehicule",
    "pesee1_poids"  : "x_studio_pesee1_poids",
    "pesee1_ticket" : "x_studio_pesee1_ticket",
    "pesee2_poids"  : "x_studio_pesee2_poids",
    "pesee2_ticket" : "x_studio_pesee2_ticket",
    "poids_net"     : "x_studio_poids_net",
    "date_bon"      : "x_studio_date_bon",
}

# ─── PROMPT MISTRAL ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un système d'extraction de données sur des documents de transport français.
Tu reçois une photo ou scan et tu dois IDENTIFIER le type de document puis extraire les valeurs dans un JSON strict.

TYPES DE DOCUMENTS RECONNUS :
A) BON DE PESÉE / BON DE LIVRAISON carrière : contient "Bon de pesée", "Pesée n°1/2", "Poids net"
B) LETTRE DE VOITURE : contient "LETTRE DE VOITURE", "LVN", "CHARGEMENT", "DÉCHARGEMENT", "MARCHANDISES"

RÈGLES COMMUNES :
1. POIDS : Toujours en kg entier. Si tonnes → multiplier par 1000 (ex: 29,320 T → 29320)
2. DATE : Format JJ/MM/AAAA. Si absent, prendre la date de la première pesée.
3. Si valeur absente ou illisible → null
4. Retourne UNIQUEMENT le JSON, sans markdown.

MAPPING SELON TYPE :

Pour BON DE PESÉE :
- numero_bon → "Bon N°", "BON N°", "Numéro de bon", "No", "n°"
- client → "Client" (nom, pas le code)
- transporteur → "Transporteur"
- produit → "Produit", "Article", "Libellé"
- chantier → "Chantier", "Destination", "Lieu livr."
- vehicule → "Véhicule", "Immat Tracteur", plaque d'immatriculation
- pesee1_poids → "Pesée n°1", "Poids brut", "BRUT", "Poids Entrée"
- pesee2_poids → "Pesée n°2", "Tare", "TARE", "Poids Sortie"
- poids_net → "Poids net", "NET", "Net", "Matieres"
- date_bon → date isolée en tête, sinon date pesée 1

Pour LETTRE DE VOITURE :
- numero_bon → "N° LVN", "n° LVN", numéro en haut du document
- client → "CHARGEMENT" (lieu/société de chargement)
- transporteur → "CONDUCTEUR" (nom du conducteur)
- produit → "NATURE" (nature de la marchandise)
- chantier → "DÉCHARGEMENT" (lieu/société de déchargement)
- vehicule → "VEHICULE" (immatriculation)
- pesee1_poids → null (pas de pesée 1)
- pesee2_poids → null (pas de pesée 2)
- poids_net → "POIDS" (en kg, convertir si tonnes)
- date_bon → "DATE" en haut du document
"""

EXTRACTION_PROMPT = """Identifie le type de document et extrais les données dans ce format JSON exact :
{
  "type_document": "bon_pesee" ou "lettre_voiture",
  "numero_bon": "...",
  "client": "...",
  "transporteur": "...",
  "produit": "...",
  "chantier": "...",
  "vehicule": "...",
  "pesee1_poids": 0,
  "pesee1_ticket": "...",
  "pesee2_poids": 0,
  "pesee2_ticket": "...",
  "poids_net": 0,
  "date_bon": "..."
}

RAPPEL : poids_net, pesee1_poids, pesee2_poids TOUJOURS en kg entier (multiplier par 1000 si tonnes)."""


# ─── SÉCURITÉ ─────────────────────────────────────────────────────────────────
def require_secret(view):
    """Décorateur : si WEBHOOK_SECRET est défini, exige un token valide
    (header X-Webhook-Secret ou ?token=...). Sinon, laisse passer (rétrocompat)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if WEBHOOK_SECRET:
            token = request.headers.get("X-Webhook-Secret") or request.args.get("token")
            if token != WEBHOOK_SECRET:
                app.logger.warning("Webhook refusé : token invalide ou absent")
                return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)
    return wrapper


# ─── CONNEXION ODOO (une seule par requête) ──────────────────────────────────
def odoo_connect():
    """Authentifie une seule fois et renvoie (uid, models)."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ValueError("Authentification Odoo échouée")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    return uid, models


def x(models, uid, model, method, *params, **kw):
    """Raccourci execute_kw."""
    return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, list(params), kw)


# ─── IMAGE / OCR ──────────────────────────────────────────────────────────────
def resize_image(image_base64: str, max_size: int = 1024) -> str:
    """Redimensionne l'image en base64 à max_size px max."""
    from PIL import Image
    img_bytes = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_with_mistral(image_base64, mime_type="image/jpeg"):
    """Appel Mistral Vision avec retry automatique sur rate limit (429)."""
    image_base64 = resize_image(image_base64)
    from mistralai import Mistral  # import paresseux : accélère le boot du service
    client = Mistral(api_key=MISTRAL_API_KEY)
    last_error = None
    for attempt in range(4):
        if attempt > 0:
            wait = attempt * 3
            app.logger.info("Rate limit - retry %d/3 dans %ds" % (attempt, wait))
            time.sleep(wait)
        try:
            response = client.chat.complete(
                model="mistral-large-latest",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime_type, image_base64)}},
                        {"type": "text", "text": EXTRACTION_PROMPT}
                    ]}
                ],
                max_tokens=512,
                temperature=0.0,
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            last_error = e
            if "429" not in str(e) and "rate" not in str(e).lower():
                raise
    raise last_error


# ─── OPÉRATIONS ODOO (reçoivent la connexion (models, uid)) ───────────────────
def odoo_fetch_image(models, uid, worksheet_id: int, model: str) -> str:
    """Récupère l'image base64 depuis Odoo."""
    result = x(models, uid, model, "read", [worksheet_id], fields=["x_studio_photo_bon"])
    if not result or not result[0].get("x_studio_photo_bon"):
        raise ValueError(f"Pas d'image sur le record {worksheet_id}")
    return result[0]["x_studio_photo_bon"]  # déjà en base64


def odoo_enrich_extracted(models, uid, worksheet_id: int, model: str, extracted: dict) -> dict:
    """Remplace date_bon et vehicule par les valeurs Odoo fiables."""
    ws = x(models, uid, model, "read", [worksheet_id],
           fields=["x_studio_date", "x_studio_immat_tracteur"])
    if not ws:
        return extracted
    ws = ws[0]

    # 1. Date → depuis x_studio_date (format Odoo: "2026-05-07" → "07/05/2026")
    odoo_date = ws.get("x_studio_date")
    if odoo_date:
        try:
            parts = str(odoo_date).split("-")
            if len(parts) == 3:
                extracted["date_bon"] = "%s/%s/%s" % (parts[2], parts[1], parts[0])
        except Exception:
            pass

    # 2. Véhicule → extraire immat depuis x_studio_immat_tracteur (Many2one → [id, "nom"])
    immat_raw = ws.get("x_studio_immat_tracteur")
    if immat_raw:
        if isinstance(immat_raw, (list, tuple)) and len(immat_raw) > 1:
            immat_str = str(immat_raw[1])
        else:
            immat_str = str(immat_raw)
        plate = re.search(r'[A-Z]{2}[-s ]?[0-9]{3}[-s ]?[A-Z]{2}', immat_str.upper())
        if plate:
            extracted["vehicule"] = plate.group(0).replace(" ", "-")
        else:
            for w in reversed(immat_str.split()):
                if re.match(r'^[A-Z0-9]{4,10}$', w.upper()):
                    extracted["vehicule"] = w.upper()
                    break
    return extracted


def odoo_write(models, uid, worksheet_id: int, model: str, extracted: dict):
    """Écrit les champs extraits sur la worksheet Odoo."""
    vals = {}
    for ocr_key, odoo_field in FIELD_MAP.items():
        val = extracted.get(ocr_key)
        if val is not None:
            vals[odoo_field] = val
    vals["x_studio_ocr_statut"] = "✅ OCR terminé — Poids net : {} kg".format(extracted.get("poids_net", "?"))
    return x(models, uid, model, "write", [worksheet_id], vals)


def odoo_write_statut(worksheet_id: int, model: str, statut: str, conn=None):
    """Écrit uniquement le statut OCR (best-effort, jamais bloquant)."""
    try:
        uid, models = conn if conn else odoo_connect()
        x(models, uid, model, "write", [worksheet_id], {"x_studio_ocr_statut": statut})
    except Exception as e:
        app.logger.warning(f"Statut OCR non écrit: {e}")


def _section_name(extracted_or_ws, from_ws=False):
    """Construit le libellé de section depuis l'OCR ou depuis la worksheet Odoo."""
    g = extracted_or_ws.get
    if from_ws:
        num, date = g("x_studio_numero_bon") or "", g("x_studio_date_bon") or ""
        client, veh = g("x_studio_client_pesee") or "", g("x_studio_vehicule") or ""
        poids = g("x_studio_poids_net") or 0
    else:
        num, date = g("numero_bon") or "", g("date_bon") or ""
        client, veh = g("client") or "", g("vehicule") or ""
        poids = g("poids_net") or 0
    poids_t = round(poids / 1000, 3) if poids else 0
    return f"Bon n°{num} | {date} | {client} | {veh} | {poids_t} T"


def odoo_upsert_section(models, uid, order_id: int, section_name: str):
    """Crée la section, ou MET À JOUR la section 'Bon n°...' existante (idempotent → pas de doublon)."""
    existing = x(models, uid, "sale.order.line", "search_read",
                 [("order_id", "=", order_id), ("display_type", "=", "line_section")],
                 fields=["id", "name"])
    bon_sections = [s for s in existing if (s.get("name") or "").startswith("Bon n°")]
    if any((s.get("name") or "") == section_name for s in existing):
        return "unchanged"
    if bon_sections:
        x(models, uid, "sale.order.line", "write", [bon_sections[0]["id"]], {"name": section_name})
        # supprime d'éventuels doublons de sections "Bon n°"
        dups = [s["id"] for s in bon_sections[1:]]
        if dups:
            x(models, uid, "sale.order.line", "unlink", dups)
        return "updated"
    x(models, uid, "sale.order.line", "create",
      {"order_id": order_id, "display_type": "line_section", "name": section_name})
    return "created"


def odoo_order_id_from_worksheet(models, uid, worksheet_id: int, model: str):
    """Remonte worksheet → tâche → ligne de commande → order_id."""
    ws = x(models, uid, model, "read", [worksheet_id], fields=["x_project_task_id"])
    if not ws or not ws[0].get("x_project_task_id"):
        return None
    task_id = ws[0]["x_project_task_id"][0]
    task = x(models, uid, "project.task", "read", [task_id], fields=["sale_line_id"])
    if not task or not task[0].get("sale_line_id"):
        return None
    sale_line_id = task[0]["sale_line_id"][0]
    line = x(models, uid, "sale.order.line", "read", [sale_line_id], fields=["order_id"])
    if not line or not line[0].get("order_id"):
        return None
    return line[0]["order_id"][0]


# ─── ENDPOINT PRINCIPAL ───────────────────────────────────────────────────────
@app.route("/ocr-pesee", methods=["POST"])
@require_secret
def ocr_pesee():
    """
    Payload (webhook natif Odoo) : {"_id": <id>, "_model": "x_project_task_worksheet_template_1"}
    """
    worksheet_id = None
    model = ODOO_WORKSHEET_MODEL
    try:
        data = request.get_json(force=True)
        app.logger.info(f"Webhook reçu: {data}")
        worksheet_id = data.get("_id") or data.get("id") or data.get("worksheet_id")
        model = data.get("_model") or data.get("model") or ODOO_WORKSHEET_MODEL
        if not worksheet_id:
            return jsonify({"error": "id requis"}), 400
        worksheet_id = int(worksheet_id)

        uid, models = odoo_connect()

        # 0. Statut "en cours"
        odoo_write_statut(worksheet_id, model, "⏳ OCR en cours...", conn=(uid, models))

        # 1. Image → 2. OCR Mistral
        image_base64 = odoo_fetch_image(models, uid, worksheet_id, model)
        extracted = extract_with_mistral(image_base64)

        # 2b. Enrichissement (date + immat fiables depuis Odoo)
        extracted = odoo_enrich_extracted(models, uid, worksheet_id, model, extracted)
        app.logger.info(f"OCR extrait: {extracted}")

        # 3. Écriture des champs
        odoo_write(models, uid, worksheet_id, model, extracted)

        # 4. Section sur la commande (idempotent)
        order_id = odoo_order_id_from_worksheet(models, uid, worksheet_id, model)
        section_status = None
        if order_id:
            section_status = odoo_upsert_section(models, uid, order_id, _section_name(extracted))

        return jsonify({"status": "ok", "extracted": extracted,
                        "worksheet_id": worksheet_id, "section": section_status})

    except Exception as e:
        app.logger.error(f"Erreur webhook: {e}")
        if worksheet_id:
            odoo_write_statut(worksheet_id, model, f"❌ OCR erreur: {str(e)[:100]}")
        code = 422 if isinstance(e, json.JSONDecodeError) else 500
        return jsonify({"error": str(e)}), code


@app.route("/add-section", methods=["POST"])
@require_secret
def add_section():
    """
    Déclenché à l'ajout d'une ligne produit sur une commande.
    Payload Odoo : {"_id": <line_id>, "_model": "sale.order.line"}
    Remonte commande → tâche → feuille OCR remplie → insère/maj la section.
    """
    try:
        data = request.get_json(force=True)
        app.logger.info(f"add-section reçu: {data}")
        line_id = data.get("_id") or data.get("id")
        if not line_id:
            return jsonify({"error": "id requis"}), 400
        line_id = int(line_id)

        uid, models = odoo_connect()
        line = x(models, uid, "sale.order.line", "read", [line_id],
                 fields=["order_id", "display_type"])
        if not line:
            return jsonify({"error": "Ligne introuvable"}), 404
        line = line[0]
        if line.get("display_type"):
            return jsonify({"status": "skipped", "reason": "already section/note"})
        order_id = line["order_id"][0]

        tasks = x(models, uid, "project.task", "search_read",
                  [("sale_line_id.order_id", "=", order_id)], fields=["id"], limit=1)
        if not tasks:
            return jsonify({"status": "skipped", "reason": "pas de tâche liée"})
        task_id = tasks[0]["id"]

        worksheets = x(models, uid, ODOO_WORKSHEET_MODEL, "search_read",
                       [("x_project_task_id", "=", task_id), ("x_studio_poids_net", ">", 0)],
                       fields=["x_studio_numero_bon", "x_studio_date_bon", "x_studio_client_pesee",
                               "x_studio_vehicule", "x_studio_poids_net"], limit=1)
        if not worksheets:
            return jsonify({"status": "skipped", "reason": "pas de feuille OCR remplie"})

        section_name = _section_name(worksheets[0], from_ws=True)
        status = odoo_upsert_section(models, uid, order_id, section_name)
        return jsonify({"status": "ok", "section": section_name, "action": status})

    except Exception as e:
        app.logger.error(f"Erreur add-section: {e}")
        return jsonify({"error": str(e)}), 500


# ─── MA TOURNÉE (chauffeurs, sans connexion Odoo) ────────────────────────────
# Le chauffeur ouvre une URL sur son téléphone perso, voit uniquement sa
# tournée et prend ses photos. L'app écrit dans la feuille de travail avec le
# compte technique (identifiants stockés côté serveur, jamais exposés).
TOURNEE_PROJECT = "Demande de transport"
TOURNEE_WS_MODEL = "x_project_task_worksheet_template_1"
TOURNEE_PHOTO = {
    "charge": ("x_studio_photo",     "📥 Chargement"),
    "livr":   ("x_studio_photo_1",   "🏁 Livraison"),
    "bon":    ("x_studio_photo_bon", "📎 Bon de pesée"),
}
_JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_MOIS = ["", "janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.",
         "août", "sept.", "oct.", "nov.", "déc."]


def _tournee_secret():
    return (WEBHOOK_SECRET or "maquignon-tournee-fallback").encode()


def _tournee_sign(task_id, kind):
    """Jeton HMAC autorisant l'upload (tâche, type) — non falsifiable sans le secret."""
    return hmac.new(_tournee_secret(), f"{task_id}:{kind}".encode(),
                    hashlib.sha256).hexdigest()[:20]


def _driver_sign(cid):
    """Signature HMAC d'un chauffeur — garantit qu'un chauffeur ne voit que SA tournée."""
    return hmac.new(_tournee_secret(), f"driver:{cid}".encode(),
                    hashlib.sha256).hexdigest()[:20]


def _esc(s):
    return (str(s if s is not None else "")).replace("&", "&amp;").replace(
        "<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _desc_text(raw):
    """Convertit la description HTML d'une tâche en texte propre (retours à la ligne
    préservés, métadonnées Odoo retirées). Retourne '' si vide."""
    if not raw:
        return ""
    s = str(raw)
    # frontières de blocs -> sauts de ligne
    s = re.sub(r"(?i)<\s*br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</\s*(div|p|li|tr|h[1-6])\s*>", "\n", s)
    s = re.sub(r"(?i)<\s*li[^>]*>", "• ", s)
    s = re.sub(r"<[^>]+>", "", s)          # retire les balises restantes
    s = _htmllib.unescape(s).replace("\xa0", " ")
    lines = [ln.strip() for ln in s.splitlines()]
    out = []
    for ln in lines:
        if ln or (out and out[-1]):        # évite les lignes vides consécutives
            out.append(ln)
    return "\n".join(out).strip()


_TOURNEE_HEAD = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<title>Ma tournée</title><style>
*{box-sizing:border-box;} body{margin:0;background:#f1f5f9;font-family:'Segoe UI',system-ui,sans-serif;color:#0f172a;}
.wrap{max-width:640px;margin:0 auto;padding:12px 12px 48px;}
h3{font-weight:800;font-size:21px;margin:8px 2px 14px;}
.drv{background:#01666B;color:#fff;border-radius:12px;padding:11px 15px;font-weight:800;font-size:17px;display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;}
.drv a{color:#cffafe;font-size:13px;text-decoration:none;font-weight:600;}
.day{font-weight:800;color:#334155;font-size:15px;margin:18px 2px 9px;border-bottom:2px solid #cbd5e1;padding-bottom:3px;}
.day.tod{color:#01666B;border-color:#01666B;}
.daynav{position:sticky;top:0;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:8px;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:8px;margin-bottom:12px;box-shadow:0 2px 6px rgba(0,0,0,.10);}
.daynav button{border:none;background:#01666B;color:#fff;font-size:20px;font-weight:800;border-radius:10px;min-width:52px;height:46px;cursor:pointer;}
.daynav button:disabled{background:#cbd5e1;}
.daylbl{font-weight:800;font-size:16px;color:#0f172a;text-align:center;flex:1;line-height:1.2;}
.daybanner{background:#01666B;color:#fff;font-weight:800;font-size:17px;border-radius:10px;padding:11px 12px;margin:0 0 12px;text-align:center;letter-spacing:.3px;}
.daybanner.tod{background:#E07020;}
.card{background:#fff;border:1px solid #e2e8f0;border-left:6px solid #01666B;border-radius:12px;padding:13px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.08);}
.time{display:inline-block;background:#EAF4F4;color:#01666B;font-weight:800;font-size:15px;border-radius:8px;padding:2px 10px;margin-bottom:6px;}
.cli{font-weight:800;font-size:16px;line-height:1.25;}
.addr{color:#475569;font-size:13.5px;margin:4px 0;}
.meta{color:#64748b;font-size:12.5px;margin:2px 0;}
.veh{display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:7px;padding:1px 8px;font-size:12px;font-weight:700;color:#334155;margin-top:6px;}
.cardhead{display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:2px;}
.tag{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;border-radius:8px;padding:0 7px;font-size:11px;font-weight:800;}
.addr b{color:#334155;}
.mini{text-decoration:none;font-size:15px;}
.ocr{background:#dcfce7;color:#166534;border-radius:8px;padding:4px 9px;font-size:12.5px;font-weight:700;margin-top:7px;display:inline-block;}
.note{background:#FEF9C3;border:1px solid #FDE68A;border-radius:8px;padding:7px 10px;font-size:14px;font-weight:600;color:#713f12;margin:7px 0;white-space:pre-wrap;line-height:1.35;}
.acts{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-top:11px;}
.acts2{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:8px;}
.ph{position:relative;text-align:center;border-radius:10px;padding:10px 4px;font-weight:800;font-size:13px;cursor:pointer;border:2px solid #01666B;color:#01666B;background:#fff;overflow:hidden;}
.ph.done{background:#dcfce7;border-color:#16a34a;color:#166534;}
.ph.busy{border-style:dashed;animation:phpulse 1s ease-in-out infinite;}
@keyframes phpulse{0%,100%{opacity:1;}50%{opacity:.45;}}
.ph.fail{background:#fee2e2;border-color:#b91c1c;color:#991b1b;}
.ph input{position:absolute;inset:0;opacity:0;}
.ph.scan{display:block;margin-top:11px;font-size:16px;padding:15px;background:#01666B;color:#fff;border-color:#01666B;}
.ph.scan.done{background:#dcfce7;color:#166534;border-color:#16a34a;}
.maps{display:block;text-align:center;text-decoration:none;background:#fff;color:#01666B;border:2px solid #01666B;border-radius:10px;padding:10px;font-weight:800;font-size:14px;margin-top:8px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.pick{display:block;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 12px;text-align:center;text-decoration:none;color:#0f172a;font-weight:800;font-size:16px;box-shadow:0 1px 3px rgba(0,0,0,.08);}
.empty{background:#fff;border-radius:12px;padding:26px 16px;text-align:center;color:#64748b;font-weight:600;}
.toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#0f172a;color:#fff;padding:10px 16px;border-radius:10px;font-weight:700;font-size:14px;opacity:0;transition:.2s;z-index:9;}
.toast.show{opacity:1;}
</style></head><body><div class="wrap">"""

_TOURNEE_JS = """<div id="toast" class="toast"></div><script>
function toast(m,ok){var t=document.getElementById('toast');t.textContent=m;t.style.background=ok?'#166534':'#b91c1c';t.className='toast show';setTimeout(function(){t.className='toast';},4500);}
function setTxt(lbl,t){lbl.firstChild.textContent=t;}
function shrink(file,cb){
  var url=URL.createObjectURL(file); var img=new Image();
  img.onload=function(){
    try{
      var w=img.width,h=img.height,r=Math.min(1,1600/Math.max(w,h));
      var cv=document.createElement('canvas'); cv.width=Math.round(w*r); cv.height=Math.round(h*r);
      cv.getContext('2d').drawImage(img,0,0,cv.width,cv.height);
      URL.revokeObjectURL(url); cb(cv.toDataURL('image/jpeg',0.82));
    }catch(e){ URL.revokeObjectURL(url); rawRead(file,cb); }
  };
  img.onerror=function(){ URL.revokeObjectURL(url); rawRead(file,cb); };
  img.src=url;
}
function rawRead(file,cb){var rd=new FileReader(); rd.onload=function(){cb(rd.result);}; rd.readAsDataURL(file);}
function sendUp(lbl,payload,attempt){
  var ctl=(typeof AbortController!=='undefined')?new AbortController():null;
  var to=ctl?setTimeout(function(){ctl.abort();},45000):null;
  fetch('/tournee/upload',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload),signal:ctl?ctl.signal:undefined})
  .then(function(x){return x.json();}).then(function(d){
    if(to){clearTimeout(to);}
    if(d.ok){
      lbl.classList.remove('busy'); lbl.classList.remove('fail'); lbl.classList.add('done');
      setTxt(lbl,'\u2713 Envoy\u00e9e \u2014 bien re\u00e7ue');
      toast('\u2705 Photo bien re\u00e7ue au bureau',true);
      if(navigator.vibrate){navigator.vibrate(200);}
    } else { upFail(lbl,payload,attempt,d.error||'?'); }
  }).catch(function(){ if(to){clearTimeout(to);} upFail(lbl,payload,attempt,'r\u00e9seau'); });
}
function upFail(lbl,payload,attempt,err){
  if(attempt<3){
    setTxt(lbl,'\u23f3 Nouvel essai '+(attempt+1)+'/3\u2026');
    setTimeout(function(){sendUp(lbl,payload,attempt+1);},1800*attempt);
    return;
  }
  lbl.classList.remove('busy'); lbl.classList.add('fail');
  setTxt(lbl,'\u274c \u00c9chec \u2014 touchez pour renvoyer');
  toast('\u274c Envoi impossible ('+err+') \u2014 r\u00e9essayez',false);
  if(navigator.vibrate){navigator.vibrate([120,90,120]);}
}
function up(inp,tid,kind,tok){
  var f=inp.files&&inp.files[0]; if(!f){return;}
  var lbl=inp.parentNode;
  lbl.classList.remove('fail'); lbl.classList.remove('done'); lbl.classList.add('busy');
  setTxt(lbl,'\u23f3 Envoi en cours\u2026');
  shrink(f,function(dataUrl){ sendUp(lbl,{task_id:tid,kind:kind,token:tok,image:dataUrl},1); });
  inp.value='';
}
(function(){
  var blocks = Array.prototype.slice.call(document.querySelectorAll('.dayblock'));
  if(!blocks.length){ return; }
  var idx = 0;
  for(var i=0;i<blocks.length;i++){ if(blocks[i].getAttribute('data-today')==='1'){ idx=i; break; } }
  var lbl=document.getElementById('daylbl'), prev=document.getElementById('prevday'), next=document.getElementById('nextday');
  function show(){
    for(var i=0;i<blocks.length;i++){ blocks[i].style.display = (i===idx)?'':'none'; }
    if(lbl){ lbl.textContent = blocks[idx].getAttribute('data-label'); }
    if(prev){ prev.disabled = (idx===0); }
    if(next){ next.disabled = (idx===blocks.length-1); }
    window.scrollTo(0,0);
  }
  if(prev){ prev.onclick=function(){ if(idx>0){ idx--; show(); } }; }
  if(next){ next.onclick=function(){ if(idx<blocks.length-1){ idx++; show(); } }; }
  show();
})();
</script></div></body></html>"""


def _tournee_page(inner):
    return _TOURNEE_HEAD + inner + _TOURNEE_JS


@app.route("/ma-tournee", methods=["GET"])
def ma_tournee():
    # Réservé aux chauffeurs PONCTUELS : lien personnel signé, un chauffeur ne
    # voit QUE sa tournée. Action unique : scanner le bon de pesée (→ OCR).
    try:
        c = request.args.get("c")
        s = request.args.get("s")
        if not c or not s or not hmac.compare_digest(s, _driver_sign(c)):
            return _tournee_page(
                '<h3>🚚 Ma tournée</h3>'
                '<div class="empty">⛔ Lien invalide ou incomplet.<br/>'
                'Demandez votre lien personnel au bureau.</div>'), 403

        cid = int(c)
        uid, models = odoo_connect()
        today = date.today()
        df = today.strftime("%Y-%m-%d 00:00:00")
        emp = x(models, uid, "hr.employee", "read", [cid], fields=["name"])
        dname = emp[0]["name"] if emp else "Chauffeur"
        tasks = x(models, uid, "project.task", "search_read",
                  [("project_id.name", "=", TOURNEE_PROJECT),
                   ("x_studio_chauffeur", "=", cid),
                   ("planned_date_begin", ">=", df)],
                  fields=["id", "name", "partner_id", "planned_date_begin", "date_deadline",
                          "x_studio_transport", "x_studio_adresse_de_chargement",
                          "x_studio_adresse_de_livraison_3", "x_studio_statut_de_locr",
                          "x_studio_bon_scanne", "tag_ids", "description"],
                  order="planned_date_begin")

        # noms des étiquettes (type de mission)
        tagmap = {}
        tagids = sorted({i for t in tasks for i in (t.get("tag_ids") or [])})
        if tagids:
            try:
                for tg in x(models, uid, "project.tags", "read", tagids, fields=["name"]):
                    tagmap[tg["id"]] = tg["name"]
            except Exception:
                tagmap = {}

        # statut des 3 photos par mission (feuille de travail)
        wsmap = {}
        tids = [t["id"] for t in tasks]
        if tids:
            for w in x(models, uid, TOURNEE_WS_MODEL, "search_read",
                       [("x_project_task_id", "in", tids)],
                       fields=["x_project_task_id", "x_studio_photo",
                               "x_studio_photo_1", "x_studio_photo_bon"]):
                wsmap[w["x_project_task_id"][0]] = w

        html = f'<div class="drv"><span>👤 {_esc(dname)}</span></div>'
        if not tasks:
            html += '<div class="empty">✅ Aucune mission à venir.<br/>Bonne journée !</div>'
            return _tournee_page(html)

        def _addr(icon, label, raw):
            if not raw:
                return ""
            a = " ".join(str(raw).split())
            q = _esc(a).replace(" ", "+")
            return (f'<div class="addr"><b>{icon} {label} :</b> {_esc(a)} '
                    f'<a class="mini" target="_blank" '
                    f'href="https://www.google.com/maps/search/?api=1&amp;query={q}">🗺️</a></div>')

        html += ('<div class="daynav">'
                 '<button id="prevday">◀</button>'
                 '<div id="daylbl" class="daylbl"></div>'
                 '<button id="nextday">▶</button></div>')
        cur_day = None
        for t in tasks:
            try:
                dt = datetime.strptime(t["planned_date_begin"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            d = dt.date()
            if d != cur_day:
                if cur_day is not None:
                    html += '</div>'  # ferme le bloc-jour précédent
                cur_day = d
                istoday = (d == today)
                lbl = f"{_JOURS[d.weekday()]} {d.day} {_MOIS[d.month]}"
                if istoday:
                    lbl += " — Aujourd'hui"
                html += (f'<div class="dayblock" data-label="{_esc(lbl)}" '
                         f'data-today="{"1" if istoday else "0"}">'
                         f'<div class="daybanner {"tod" if istoday else ""}">{_esc(lbl)}</div>')

            tr = dt.strftime("%H:%M")
            if t.get("date_deadline"):
                try:
                    tr += " → " + datetime.strptime(
                        t["date_deadline"], "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
                except Exception:
                    pass
            cli = t["partner_id"][1] if t.get("partner_id") else t["name"]
            veh = t["x_studio_transport"][1].replace("Transport ", "") if t.get("x_studio_transport") else ""
            tags = " ".join(f'<span class="tag">{_esc(tagmap[i])}</span>'
                            for i in (t.get("tag_ids") or []) if tagmap.get(i))
            ws = wsmap.get(t["id"], {})
            done_bon = bool(t.get("x_studio_bon_scanne")) or bool(ws.get("x_studio_photo_bon"))
            done_charge = bool(ws.get("x_studio_photo"))
            done_livr = bool(ws.get("x_studio_photo_1"))
            ocr = t.get("x_studio_statut_de_locr") or ""

            html += '<div class="card">'
            html += f'<div class="cardhead"><span class="time">🕐 {tr}</span> {tags}</div>'
            html += f'<div class="cli">{_esc(cli)}</div>'
            html += f'<div class="meta">{_esc(t["name"])}</div>'
            note = _desc_text(t.get("description"))
            if note:
                html += f'<div class="note">📝 {_esc(note)}</div>'
            html += _addr("📦", "Chargement", t.get("x_studio_adresse_de_chargement"))
            html += _addr("🏁", "Livraison", t.get("x_studio_adresse_de_livraison_3"))
            if veh:
                html += f'<span class="veh">🚛 {_esc(veh)}</span>'
            if ocr:
                html += f'<div class="ocr">{_esc(ocr)}</div>'
            lblbon = "✓ Bon scanné — reprendre" if done_bon else "📷 Scanner le bon de pesée"
            html += (f'<label class="ph scan {"done" if done_bon else ""}">{lblbon}'
                     f'<input type="file" accept="image/*" capture="environment" '
                     f'onchange="up(this,{t["id"]},\'bon\',\'{_tournee_sign(t["id"], "bon")}\')"/></label>')
            html += '<div class="acts2">'
            html += (f'<label class="ph {"done" if done_charge else ""}">'
                     f'{"✓ Photo chargt" if done_charge else "📥 Photo chargt"}'
                     f'<input type="file" accept="image/*" capture="environment" '
                     f'onchange="up(this,{t["id"]},\'charge\',\'{_tournee_sign(t["id"], "charge")}\')"/></label>')
            html += (f'<label class="ph {"done" if done_livr else ""}">'
                     f'{"✓ Photo livr." if done_livr else "📸 Photo livr."}'
                     f'<input type="file" accept="image/*" capture="environment" '
                     f'onchange="up(this,{t["id"]},\'livr\',\'{_tournee_sign(t["id"], "livr")}\')"/></label>')
            html += '</div>'
            html += '</div>'
        if cur_day is not None:
            html += '</div>'  # ferme le dernier bloc-jour
        return _tournee_page(html)
    except Exception as e:
        app.logger.error(f"Erreur ma-tournee: {e}")
        return _tournee_page(f'<div class="empty">Erreur : {_esc(str(e)[:120])}</div>'), 500


@app.route("/tournee/upload", methods=["POST"])
def tournee_upload():
    try:
        data = request.get_json(force=True)
        task_id = int(data.get("task_id"))
        kind = data.get("kind")
        token = data.get("token")
        image = data.get("image") or ""
        if kind not in TOURNEE_PHOTO:
            return jsonify({"ok": False, "error": "type invalide"}), 400
        if not token or not hmac.compare_digest(token, _tournee_sign(task_id, kind)):
            return jsonify({"ok": False, "error": "jeton invalide"}), 403
        if image.startswith("data:") and "," in image:
            image = image.split(",", 1)[1]
        if not image:
            return jsonify({"ok": False, "error": "image vide"}), 400
        image = resize_image(image)  # redimensionne + normalise en JPEG

        field = TOURNEE_PHOTO[kind][0]
        uid, models = odoo_connect()
        ws = x(models, uid, TOURNEE_WS_MODEL, "search",
               [("x_project_task_id", "=", task_id)], limit=1)
        ws_id = ws[0] if ws else x(models, uid, TOURNEE_WS_MODEL, "create",
                                   {"x_project_task_id": task_id})
        x(models, uid, TOURNEE_WS_MODEL, "write", [ws_id], {field: image})
        return jsonify({"ok": True, "worksheet_id": ws_id})
    except Exception as e:
        app.logger.error(f"Erreur tournee-upload: {e}")
        return jsonify({"ok": False, "error": str(e)[:150]}), 500


@app.route("/tournee/liens", methods=["GET"])
@require_secret
def tournee_liens():
    """Page ADMIN (bureau) : liste les liens personnels signés de chaque chauffeur.
    Protégée par le secret : /tournee/liens?token=<WEBHOOK_SECRET>."""
    uid, models = odoo_connect()
    tasks = x(models, uid, "project.task", "search_read",
              [("project_id.name", "=", TOURNEE_PROJECT),
               ("x_studio_chauffeur", "!=", False)],
              fields=["x_studio_chauffeur"], limit=5000)
    drivers = {}
    for t in tasks:
        ch = t.get("x_studio_chauffeur")
        if ch:
            drivers[ch[0]] = ch[1]
    # téléphones (pour pré-remplir WhatsApp) — best effort
    phones = {}
    if drivers:
        try:
            for e in x(models, uid, "hr.employee", "read", list(drivers.keys()),
                       fields=["mobile_phone", "work_phone"]):
                phones[e["id"]] = e.get("mobile_phone") or e.get("work_phone") or ""
        except Exception:
            phones = {}

    base = request.host_url.rstrip("/")
    html = (_TOURNEE_HEAD
            + "<style>.lkbtns{display:flex;gap:8px;margin-top:9px;}"
              ".lkb{flex:1;text-align:center;border:none;border-radius:10px;padding:12px;"
              "font-weight:800;font-size:15px;cursor:pointer;text-decoration:none;}"
              ".lkb.copy{background:#01666B;color:#fff;} .lkb.copy.ok{background:#16a34a;}"
              ".lkb.wa{background:#25D366;color:#fff;}</style>"
              "<h3>🔗 Liens chauffeurs</h3>"
              "<p class=\"meta\" style=\"margin-bottom:12px;\">Un lien personnel par chauffeur "
              "— ne pas partager entre chauffeurs.</p>")
    for cid, nm in sorted(drivers.items(), key=lambda a: (a[1] or "").upper()):
        link = f"{base}/ma-tournee?c={cid}&s={_driver_sign(cid)}"
        num = re.sub(r"\D", "", phones.get(cid, "") or "")
        if num.startswith("0"):
            num = "33" + num[1:]
        msg = quote(f"Bonjour {nm}, voici votre lien Ma tournée : {link}")
        wa = f"https://wa.me/{num}?text={msg}"
        html += (f'<div class="card"><div class="cli">{_esc(nm)}</div>'
                 f'<div class="meta" style="word-break:break-all;margin-top:4px;">{_esc(link)}</div>'
                 f'<div class="lkbtns">'
                 f'<button type="button" class="lkb copy" data-link="{_esc(link)}" onclick="cp(this)">📋 Copier</button>'
                 f'<a class="lkb wa" target="_blank" href="{_esc(wa)}">🟢 WhatsApp</a>'
                 f'</div></div>')
    html += ("<script>function cp(b){var t=b.getAttribute('data-link');"
             "function ok(){var o=b.textContent;b.textContent='✓ Copié';b.classList.add('ok');"
             "setTimeout(function(){b.textContent=o;b.classList.remove('ok');},1500);}"
             "if(navigator.clipboard&&navigator.clipboard.writeText){"
             "navigator.clipboard.writeText(t).then(ok).catch(fb);}else{fb();}"
             "function fb(){var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);"
             "a.select();try{document.execCommand('copy');}catch(e){}a.remove();ok();}}</script>"
             "</div></body></html>")
    return html


from lefevre_import import lefevre_bp  # noqa: E402
app.register_blueprint(lefevre_bp)


@app.route("/rotate-image", methods=["POST"])
@require_secret
def rotate_image():
    """Pivote une photo d'une feuille de travail (appelé par un bouton Odoo
    via webhook sortant). Payload webhook Odoo : {_model, _id} ; champ et
    angle passés en query string. Chaque appel = +90° horaire par défaut."""
    from PIL import Image

    data = request.get_json(force=True, silent=True) or {}
    model = data.get("_model") or data.get("model") or ""
    rec_id = int(data.get("_id") or data.get("id") or 0)
    field = request.args.get("field") or data.get("field") or ""
    try:
        angle = int(request.args.get("angle") or data.get("angle") or 90)
    except ValueError:
        angle = 90

    ALLOWED_FIELDS = {"x_studio_photo_bon", "x_studio_photo", "x_studio_photo_1"}
    ALLOWED_MODELS = {"x_project_task_worksheet_template_1"}
    if model not in ALLOWED_MODELS or not rec_id or field not in ALLOWED_FIELDS:
        return jsonify({"error": "bad params", "model": model, "id": rec_id, "field": field}), 400

    uid, models = odoo_connect()
    rec = x(models, uid, model, "read", [rec_id], fields=[field])
    b64 = rec and rec[0].get(field)
    if not b64:
        return jsonify({"error": "no image"}), 404

    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    fmt = (img.format or "JPEG").upper()
    img = img.rotate(-angle, expand=True)  # -90 = quart de tour horaire
    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=90)
    x(models, uid, model, "write", [rec_id], {field: base64.b64encode(buf.getvalue()).decode()})
    app.logger.info(f"rotate-image: {model}#{rec_id}.{field} +{angle}°")
    return jsonify({"ok": True, "field": field, "angle": angle})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ─── Tableau de bord « Fabrication — Commandes en cours » ────────────────────
# Les tableaux du tableur ont des réserves de lignes fixes ; on redimensionne le
# document sur le nombre réel de commandes (endpoint manuel + recalage nocturne).
import threading
import time as _time

import fab_dashboard


def _fab_dash_call_kw(models, uid):
    def call_kw(model, method, args, kwargs=None):
        return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, args, kwargs or {})
    return call_kw


@app.route("/rebuild-fab-dashboard", methods=["POST"])
@require_secret
def rebuild_fab_dashboard():
    # odoo_connect() renvoie (uid, models) : dépaqueté à l'envers, execute_kw
    # recevait l'entier uid comme proxy et plantait.
    uid, models = odoo_connect()
    counts = fab_dashboard.rebuild(_fab_dash_call_kw(models, uid))
    app.logger.info(f"fab-dashboard redimensionné: {counts}")
    return jsonify({"ok": True, "counts": counts})


# ─── EXPORT PAIE DES HEURES SALARIÉS ─────────────────────────────────────────
# /export-heures?mois=YYYY-MM&comp=all|<id société>&k=<clé>
# La clé est stockée dans Odoo (ir.config_parameter maquignon.heures_export_key),
# jamais dans le code ; la page /heures-admin génère le lien complet.
import export_heures


@app.route("/export-heures", methods=["GET"])
def export_heures_route():
    mois = (request.args.get("mois") or "").strip()
    comp = (request.args.get("comp") or "all").strip()
    key = (request.args.get("k") or "").strip()
    if not re.match(r"^\d{4}-\d{2}$", mois):
        return jsonify({"error": "mois attendu au format YYYY-MM"}), 400
    uid, models = odoo_connect()

    def call(model, method, *args, **kw):
        return models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, list(args), kw)

    ref = call("ir.config_parameter", "get_param", ["maquignon.heures_export_key"])
    if not ref or not hmac.compare_digest(key, str(ref)):
        return jsonify({"error": "clé invalide"}), 403
    data = export_heures.build(call, mois, comp)
    from flask import Response
    return Response(
        data,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=HEURES_{mois}.xlsx"},
    )


# ─── HEURES SALARIÉS : RELAIS RPC DES PAGES WEB ──────────────────────────────
# Les pages /mes-heures, /heures-admin, /planning-rh, /heures-horaires et
# /heures-liens sont des vues website Odoo consultées SANS compte Odoo (liens
# signés). Elles appelaient /web/dataset/call_kw, réservé aux utilisateurs
# connectés au backend : tout enregistrement échouait en « Session expired »
# dès que le navigateur n'était pas logué à Odoo — donc sur tous les téléphones
# des salariés. Ce relais exécute les mêmes actions serveur avec le compte
# technique ; la sécurité reste portée par les actions elles-mêmes (jeton
# personnel du salarié ou clé responsables vérifiés dans leur code), le relais
# n'y ajoute ni n'y retire rien.
HEURES_ACTIONS_AUTORISEES = {
    2012,  # enregistrer une journée (jeton salarié ou clé responsables)
    2013,  # créer une demande de congés (jeton salarié)
    2014,  # répondre à une demande de congés (clé responsables)
    2020,  # régénérer le lien d'un salarié (clé responsables)
    2021,  # horaires par défaut d'un salarié (clé responsables)
}
HEURES_ORIGINE = os.environ.get("HEURES_ORIGINE", ODOO_URL or "https://maquignon.odoo.com")


def _heures_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = HEURES_ORIGINE
    resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp


@app.route("/heures/rpc", methods=["POST", "OPTIONS"])
def heures_rpc():
    if request.method == "OPTIONS":
        return _heures_cors(app.make_response(("", 204)))

    donnees = request.get_json(silent=True) or {}
    action_id = donnees.get("action_id")
    ctx = donnees.get("ctx")
    if action_id not in HEURES_ACTIONS_AUTORISEES or not isinstance(ctx, dict):
        return _heures_cors(jsonify({"error": {"message": "action non autorisée"}}))

    try:
        uid, models = odoo_connect()
        resultat = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            "ir.actions.server", "run", [[int(action_id)]], {"context": ctx},
        )
        return _heures_cors(jsonify({"result": resultat if isinstance(resultat, dict) else {}}))
    except xmlrpc.client.Fault as exc:
        # Message de l'action (jeton invalide, clé erronée...) : renvoyé tel
        # quel, la page l'affiche à l'utilisateur.
        message = (exc.faultString or "Erreur Odoo").strip()
        return _heures_cors(jsonify({"error": {"message": message[-400:]}}))
    except Exception as exc:
        app.logger.warning(f"heures_rpc: {exc}")
        return _heures_cors(jsonify({"error": {"message": f"Service indisponible : {exc}"}}))


def _fab_dash_nightly():
    while True:
        now = datetime.utcnow()
        nxt = now.replace(hour=3, minute=40, second=0, microsecond=0)
        if nxt <= now:
            from datetime import timedelta
            nxt = nxt + timedelta(days=1)
        _time.sleep(max((nxt - now).total_seconds(), 60))
        try:
            uid, models = odoo_connect()
            counts = fab_dashboard.rebuild(_fab_dash_call_kw(models, uid))
            app.logger.info(f"fab-dashboard recalage nocturne: {counts}")
        except Exception as e:
            app.logger.warning(f"fab-dashboard recalage nocturne échoué: {e}")


if ODOO_URL and ODOO_PASSWORD:
    threading.Thread(target=_fab_dash_nightly, daemon=True).start()


# ─── PROTEC : planning chauffeur + Ma tournée + fiche de fin de travaux ──────
# Monté sous /protec — voir protec_planning/README.md
# (env vars : PROTEC_ODOO_USER, PROTEC_ODOO_PASSWORD, PROTEC_PLANNING_SECRET)
try:
    from protec_planning.app import bp as protec_bp
    app.register_blueprint(protec_bp, url_prefix="/protec")
except Exception as _e:
    app.logger.warning(f"Module protec_planning non chargé: {_e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
