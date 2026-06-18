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
import xmlrpc.client
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify

from mistralai import Mistral

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
    """Crée ou met à jour la section correspondant à ce bon (match par numéro de bon)."""
    existing = x(models, uid, "sale.order.line", "search_read",
                 [("order_id", "=", order_id), ("display_type", "=", "line_section")],
                 fields=["id", "name"])
    # Déjà identique → rien à faire
    if any((s.get("name") or "") == section_name for s in existing):
        return "unchanged"
    # Chercher une section existante pour ce même numéro de bon (première partie avant "|")
    bon_prefix = section_name.split("|")[0].strip()
    matching = [s for s in existing
                if (s.get("name") or "").split("|")[0].strip() == bon_prefix]
    if matching:
        x(models, uid, "sale.order.line", "write", [matching[0]["id"]], {"name": section_name})
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


def _parse_section_date(name: str) -> datetime:
    """Extrait la date d'un libellé 'Bon n°... | DD/MM/YYYY | ...' pour le tri."""
    try:
        parts = name.split("|")
        if len(parts) >= 2:
            return datetime.strptime(parts[1].strip(), "%d/%m/%Y")
    except Exception:
        pass
    return datetime.max  # sections sans date lisible vont à la fin


@app.route("/sort-sections", methods=["POST"])
@require_secret
def sort_sections():
    """
    Trie les sections 'Bon n°...' d'une commande par date chronologique.
    Payload Odoo : {"_id": <order_id>} ou {"order_id": <order_id>}
    Les lignes produit situées avant la première section 'Bon n°' restent en tête.
    """
    try:
        data = request.get_json(force=True)
        app.logger.info(f"sort-sections reçu: {data}")
        order_id = data.get("_id") or data.get("id") or data.get("order_id")
        if not order_id:
            return jsonify({"error": "id requis"}), 400
        order_id = int(order_id)

        uid, models = odoo_connect()

        # 1. Toutes les lignes triées par séquence actuelle
        all_lines = x(models, uid, "sale.order.line", "search_read",
                      [("order_id", "=", order_id)],
                      fields=["id", "sequence", "display_type", "name"],
                      order="sequence asc, id asc")

        # 2. Construire les groupes : lignes pré-section + blocs [section + ses produits]
        pre_lines = []
        groups = []          # liste de (section_line, [product_lines])
        current_section = None
        current_products = []

        for line in all_lines:
            is_bon = (
                line.get("display_type") == "line_section"
                and (line.get("name") or "").startswith("Bon n°")
            )
            if is_bon:
                if current_section is not None:
                    groups.append((current_section, current_products))
                else:
                    pre_lines = list(current_products)
                current_section = line
                current_products = []
            else:
                current_products.append(line)

        if current_section is not None:
            groups.append((current_section, current_products))
        elif current_products:
            pre_lines.extend(current_products)

        if not groups:
            return jsonify({"status": "skipped", "reason": "aucune section Bon n° trouvée"})

        # 3. Trier les blocs par date extraite du libellé de section
        groups.sort(key=lambda g: _parse_section_date(g[0].get("name") or ""))

        # 4. Réassigner les séquences : pré-lignes d'abord, puis sections triées
        seq = 10
        updates = []

        for line in pre_lines:
            updates.append((line["id"], seq))
            seq += 10

        for section_line, product_lines in groups:
            updates.append((section_line["id"], seq))
            seq += 10
            for pl in product_lines:
                updates.append((pl["id"], seq))
                seq += 10

        # 5. Écriture en base
        for line_id, new_seq in updates:
            x(models, uid, "sale.order.line", "write", [line_id], {"sequence": new_seq})

        app.logger.info(f"sort-sections OK: {len(groups)} sections triées sur commande {order_id}")
        return jsonify({
            "status": "ok",
            "order_id": order_id,
            "sections_triees": len(groups),
            "ordre": [section.get("name") for section, _ in groups],
        })

    except Exception as e:
        app.logger.error(f"Erreur sort-sections: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
