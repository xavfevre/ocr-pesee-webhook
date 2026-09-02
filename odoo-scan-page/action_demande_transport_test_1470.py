# Action serveur Odoo 1470 — « demande transport test tache »
# Modèle : Sales Order — ARCHIVE avant suppression (02/09/2026)
# Remplacée par l'interface web /export-compta (Render).

current_company = env.company

# Rechercher le projet
project = env['project.project'].search([
    ('name', 'ilike', 'Demande de transport'),
    ('company_id', '=', current_company.id)
], limit=1)

if not project:
    raise UserError("Projet 'Demande de transport' introuvable.")

if not records:
    raise UserError("Aucune commande transmise à l'action serveur.")

created_tasks = []

for record in records:
    try:
        record.message_post(body="Débogage : traitement commande en cours...")

        # Infos client
        client = record.partner_id
        client_nom = client.name or "Non renseigné"
        client_telephone = client.phone or client.mobile or "Non renseigné"
        client_email = client.email or "Non renseigné"

        adresse_parts = []
        if client.street:
            adresse_parts.append(client.street)
        if client.street2:
            adresse_parts.append(client.street2)
        if client.zip or client.city:
            ville_info = f"{client.zip or ''} {client.city or ''}".strip()
            adresse_parts.append(ville_info)
        if client.country_id:
            adresse_parts.append(client.country_id.name)

        client_adresse = "\n".join(adresse_parts) or "Non renseignée"

        # Infos transport
        info_parts = []
        if record.x_studio_transport_urgence:
            info_parts.append(f"Urgence: {record.x_studio_transport_urgence}")
        if record.x_studio_transport_adresse:
            info_parts.append(f"Adresse: {record.x_studio_transport_adresse}")
        if record.x_studio_transport_commentaire:
            info_parts.append(f"Commentaires: {record.x_studio_transport_commentaire}")
        info_transport = "\n".join(info_parts) or "Informations standard"

        # Produits
        produits_liste = [
            f"• {line.name} - Qté: {line.product_uom_qty}"
            for line in record.order_line if line.name
        ]
        produits_text = "\n".join(produits_liste) or "Aucun produit trouvé"

        # Description complète
        description = f"""DEMANDE DE TRANSPORT - {record.name}

=== INFORMATIONS CLIENT ===
Nom: {client_nom}
Téléphone: {client_telephone}
Email: {client_email}

Adresse:
{client_adresse}

=== PRODUITS À TRANSPORTER ===
{produits_text}

=== INFORMATIONS TRANSPORT ===
{info_transport}

=== RÉFÉRENCE COMMANDE ===
Numéro de commande: {record.name}
"""

        # Créer la tâche
        task_values = {
            'name': f'Transport - {record.name} - {client_nom}',
            'description': description,
            'project_id': project.id,
            'partner_id': client.id,
            'company_id': current_company.id,
            'user_ids': [],
            'priority': '2' if record.x_studio_transport_urgence and 'urgent' in record.x_studio_transport_urgence.lower() else '1',
        }

        new_task = env['project.task'].create(task_values)
        created_tasks.append(new_task)

        record.message_post(
            body=f"Tâche de transport créée : <a href='/web#id={new_task.id}&model=project.task'>{new_task.name}</a>",
            subject="Tâche de transport créée"
        )

    except Exception as e:
        record.message_post(body=f"Erreur lors de la création de la tâche : {e}")

if not created_tasks:
    raise UserError("Aucune tâche n’a pu être créée. Voir les messages dans les commandes.")
else:
    raise UserError(f"{len(created_tasks)} tâche(s) créée(s) dans le projet '{project.name}' avec succès.")
