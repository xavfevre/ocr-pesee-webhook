"""
Webhook OCR - Bon de pesée → Worksheet FSM Odoo
Hébergement : Render.com (free tier)
OCR : Mistral Vision (mistral-small-latest)
Retour : JSON-RPC Odoo write() sur la worksheet
"""

import os
import json
import base64
import re
import xmlrpc.client
from flask import Flask, request, jsonify
from mistralai import Mistral

app = Flask(__name__)

# ─── CONFIG (variables d'environnement sur Render) ───────────────────────────
MISTRAL_API_KEY  = os.environ.get("MISTRAL_API_KEY")
ODOO_URL         = os.environ.get("ODOO_URL")          # ex: https://maquignon.odoo.com
ODOO_DB          = os.environ.get("ODOO_DB")            # ex: maquignon
ODOO_USER        = os.environ.get("ODOO_USER")          # email du compte technique
ODOO_PASSWORD    = os.environ.get("ODOO_PASSWORD")      # mot de passe ou API key
WEBHOOK_SECRET   = os.environ.get("WEBHOOK_SECRET", "") # token de sécurité optionnel
ODOO_WORKSHEET_MODEL = os.environ.get("ODOO_WORKSHEET_MODEL", "x_project_task_worksheet_template_1_line")

# ─── MAPPING champs OCR → noms techniques Odoo (à adapter) ───────────────────
# Remplace par tes vrais noms x_studio_* de la worksheet
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
}

# ─── PROMPT MISTRAL ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un système d'extraction de données sur des bons de pesée français.
Tu reçois une photo d'un bon de pesée et tu dois extraire les valeurs dans un JSON strict.
Règles :
- Les poids sont en kg, retourne uniquement le nombre entier (ex: 15020, pas "15 020 kg")
- Si une valeur est absente ou illisible, retourne null
- Retourne UNIQUEMENT le JSON, sans markdown, sans texte autour
"""

EXTRACTION_PROMPT = """Extrais les données de ce bon de pesée dans ce format JSON exact :
{
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
  "poids_net": 0
}"""


def resize_image(image_base64: str, max_size: int = 1024) -> str:
    """Redimensionne l'image en base64 à max_size px max."""
    from PIL import Image
    import io as _io
    img_bytes = base64.b64decode(image_base64)
    img = Image.open(_io.BytesIO(img_bytes))
    img.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = _io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_with_mistral(image_base64: str, mime_type: str = "image/jpeg") -> dict:
    """Appel Mistral Vision et retourne le dict extrait."""
    image_base64 = resize_image(image_base64)
    client = Mistral(api_key=MISTRAL_API_KEY)

    response = client.chat.complete(
        model="pixtral-12b-2409",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT}
                ]
            }
        ],
        max_tokens=512,
        temperature=0.0,
    )

    raw = response.choices[0].message.content.strip()

    # Nettoyage au cas où Mistral renvoie des backticks
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    return json.loads(raw)


def odoo_write(worksheet_id: int, extracted: dict):
    """Écrit les champs extraits sur la worksheet Odoo via JSON-RPC."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ValueError("Authentification Odoo échouée")

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    # Construction du dict de valeurs avec le mapping
    vals = {}
    for ocr_key, odoo_field in FIELD_MAP.items():
        val = extracted.get(ocr_key)
        if val is not None:
            vals[odoo_field] = val

    if not vals:
        raise ValueError("Aucune valeur extraite à écrire")

    # Modèle de la worksheet FSM — à vérifier selon ta config
    # Peut être "worksheet.document" ou "project.task" selon implémentation
    model = ODOO_WORKSHEET_MODEL

    result = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, "write",
        [[worksheet_id], vals]
    )
    return result


# ─── ENDPOINT PRINCIPAL ───────────────────────────────────────────────────────
def odoo_fetch_image(worksheet_id: int, model: str) -> str:
    """Récupère l'image base64 depuis Odoo via XML-RPC."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        raise ValueError("Authentification Odoo échouée")
    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
    result = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        model, "read",
        [[worksheet_id]],
        {"fields": ["x_studio_photo_bon"]}
    )
    if not result or not result[0].get("x_studio_photo_bon"):
        raise ValueError(f"Pas d'image sur le record {worksheet_id}")
    return result[0]["x_studio_photo_bon"]  # déjà en base64


@app.route("/ocr-pesee", methods=["POST"])
def ocr_pesee():
    """
    Payload attendu (webhook natif Odoo ou manuel) :
    {
        "id": 42,                   // ID du record (webhook Odoo natif)
        "model": "x_project_...",   // nom du modèle (optionnel)
    }
    """
    try:
        data = request.get_json(force=True)
        app.logger.info(f"Webhook reçu: {data}")

        # Odoo native webhook envoie {"_id": ..., "_model": ...}
        worksheet_id = data.get("_id") or data.get("id") or data.get("worksheet_id")
        model = data.get("_model") or data.get("model") or ODOO_WORKSHEET_MODEL

        if not worksheet_id:
            return jsonify({"error": "id requis"}), 400

        # 1. Récupération de l'image depuis Odoo
        image_base64 = odoo_fetch_image(int(worksheet_id), model)
        app.logger.info(f"Image récupérée pour record {worksheet_id}")

        # 2. Extraction OCR via Mistral
        extracted = extract_with_mistral(image_base64)
        app.logger.info(f"OCR extrait: {extracted}")

        # 3. Écriture des champs dans Odoo
        odoo_write(int(worksheet_id), extracted)

        return jsonify({
            "status": "ok",
            "extracted": extracted,
            "worksheet_id": worksheet_id
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Mistral JSON parse error: {str(e)}"}), 422
    except Exception as e:
        app.logger.error(f"Erreur webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
