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
    "date_bon"      : "x_studio_date_bon",
}

# ─── PROMPT MISTRAL ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un système d'extraction de données sur des bons de pesée/livraison français.
Tu reçois une photo ou scan d'un bon et tu dois extraire les valeurs dans un JSON strict.

RÈGLES CRITIQUES :
1. POIDS : Toujours retourner en kg (entier). Si le bon indique des tonnes (T ou t), multiplie par 1000 (ex: 29,800 T → 29800). Si en kg, retourne tel quel.
2. NUMÉRO DE BON : cherche "Bon N°", "BON N°", "Numéro de bon", "No", "Numero", "n°", "BON DE LIVRAISON N°" etc.
3. CLIENT : cherche "Client", "CLIENT", "Client n°" (prends le nom pas le code)
4. TRANSPORTEUR : cherche "Transporteur", "Transport", "MAQUIGNON" si c'est la valeur
5. PRODUIT : cherche "Produit", "PRODUIT", "Article", "Libellé", "Description"
6. CHANTIER : cherche "Chantier", "CHANTIER", "Destination", "Lieu livr."
7. VÉHICULE : cherche "Véhicule", "Immat", "Tracteur", la plaque d'immatriculation
8. PESÉE 1 : cherche "Pesée n°1", "Poids Pesee1", "Poids brut", "BRUT", "Poids Entrée"
9. PESÉE 2 : cherche "Pesée n°2", "Poids Pesee2", "Tare", "TARE", "Poids Sortie"
10. POIDS NET : cherche "Poids net", "NET", "Net", "Matieres", "Quantité" en dernière instance
11. DATE : cherche une date isolée en tête de document. Sinon prends la date de la première pesée. Format JJ/MM/AAAA.
12. Si une valeur est absente ou illisible, retourne null.
13. Retourne UNIQUEMENT le JSON, sans markdown, sans texte autour.
"""

EXTRACTION_PROMPT = """Extrais les données de ce bon de pesée/livraison dans ce format JSON exact :
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
  "poids_net": 0,
  "date_bon": "..."
}

RAPPEL : poids_net, pesee1_poids, pesee2_poids TOUJOURS en kg entier (multiplier par 1000 si tonnes)."""


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

    # Statut OCR
    vals["x_studio_ocr_statut"] = "✅ OCR terminé — Poids net : {} kg".format(extracted.get("poids_net", "?"))

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


def odoo_add_section_commande(worksheet_id: int, extracted: dict):
    """Ajoute une ligne de section sur la commande liée à la tâche."""
    common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
    uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
    if not uid:
        return

    models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

    # 1. Récupérer la tâche liée à la feuille
    ws = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        ODOO_WORKSHEET_MODEL, "read",
        [[worksheet_id]], {"fields": ["x_project_task_id"]})
    if not ws or not ws[0].get("x_project_task_id"):
        app.logger.info("Pas de tâche liée à la feuille")
        return

    task_id = ws[0]["x_project_task_id"][0]

    # 2. Récupérer la commande via sale_line_id sur la tâche
    task = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        "project.task", "read",
        [[task_id]], {"fields": ["sale_line_id", "name"]})
    if not task or not task[0].get("sale_line_id"):
        app.logger.info("Pas de commande liée à la tâche")
        return

    sale_line_id = task[0]["sale_line_id"][0]

    # 3. Récupérer l'order_id depuis la ligne de commande
    line = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        "sale.order.line", "read",
        [[sale_line_id]], {"fields": ["order_id"]})
    if not line or not line[0].get("order_id"):
        return

    order_id = line[0]["order_id"][0]

    # 4. Construire le libellé de la section
    num = extracted.get("numero_bon") or ""
    date = extracted.get("date_bon") or ""
    client = extracted.get("client") or ""
    vehicule = extracted.get("vehicule") or ""
    poids = extracted.get("poids_net") or 0
    poids_t = round(poids / 1000, 3) if poids else 0

    section_name = f"Bon n°{num} | {date} | {client} | {vehicule} | {poids_t} T"

    # 5. Créer la ligne de section sur la commande
    models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
        "sale.order.line", "create",
        [{
            "order_id": order_id,
            "display_type": "line_section",
            "name": section_name,
        }])

    app.logger.info(f"Section créée sur commande {order_id}: {section_name}")


# ─── ENDPOINT PRINCIPAL ───────────────────────────────────────────────────────
def odoo_write_statut(worksheet_id: int, model: str, statut: str):
    """Écrit uniquement le statut OCR sur la worksheet."""
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        if uid:
            models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
            models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD,
                model, "write", [[worksheet_id], {"x_studio_ocr_statut": statut}])
    except:
        pass


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

        # 0. Statut "en cours"
        odoo_write_statut(int(worksheet_id), model, "⏳ OCR en cours...")

        # 1. Récupération de l'image depuis Odoo
        image_base64 = odoo_fetch_image(int(worksheet_id), model)
        app.logger.info(f"Image récupérée pour record {worksheet_id}")

        # 2. Extraction OCR via Mistral
        extracted = extract_with_mistral(image_base64)
        app.logger.info(f"OCR extrait: {extracted}")

        # 3. Écriture des champs dans Odoo
        odoo_write(int(worksheet_id), extracted)

        # 4. Section sur la commande
        odoo_add_section_commande(int(worksheet_id), extracted)

        return jsonify({
            "status": "ok",
            "extracted": extracted,
            "worksheet_id": worksheet_id
        })

    except json.JSONDecodeError as e:
        return jsonify({"error": f"Mistral JSON parse error: {str(e)}"}), 422
    except Exception as e:
        app.logger.error(f"Erreur webhook: {str(e)}")
        try:
            if worksheet_id:
                odoo_write_statut(int(worksheet_id), ODOO_WORKSHEET_MODEL, f"❌ OCR erreur: {str(e)[:100]}")
        except:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
