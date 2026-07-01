# E-mail de clôture → celine@maquignon.com

À chaque clôture de palette (scan/bouton emplacement), l'action serveur
« Relocaliser palette (emplacement) » envoie un e-mail.

## mail.template « Bon de colisage (cloture) »
- **model_id** : stock.package
- **email_to** : `celine@maquignon.com`
- **email_from** : `{{ object.company_id.email or "contact@maquignon.com" }}`
- **use_default_to** : False  (sinon email_to est ignoré → destinataire vide)
- **report_template_ids** : rapport `maquignon.report_bon_colisage` (PDF en PJ)
- **subject** (moteur inline_template, `{{ }}`) :
  `Palette clôturée : {{ object.name }}`
- **body_html** (moteur QWEB, `t-out` — PAS `{{ }}`) :

```html
<div style="font-family:Arial,sans-serif;font-size:14px;">
  <p>Bonjour,</p>
  <p>La palette <strong t-out="object.name">PACK</strong> vient d'être clôturée.</p>
  <ul>
    <li><strong>Client :</strong> <t t-out="object.x_studio_client or '-'">-</t></li>
    <li><strong>Emplacement :</strong> <t t-out="object.x_studio_zone or '-'">-</t></li>
    <li><strong>Cubage :</strong> <t t-out="round(object.x_studio_cubage or 0, 3)">0</t> m³</li>
    <li><strong>Tonnage :</strong> <t t-out="round(object.x_studio_tonnage or 0)">0</t> kg</li>
  </ul>
  <p>Le bon de colisage détaillé est en pièce jointe.</p>
</div>
```

## Déclenchement (dans l'action serveur de clôture)
```python
tmpl = env['mail.template'].search([('name','=','Bon de colisage (cloture)')], limit=1)
if tmpl:
    tmpl.send_mail(colis.id, force_send=True)
```
Enveloppé dans un try/except : un souci d'e-mail ne bloque jamais la clôture.

NB : sur la base de test (neutralisée) les e-mails sont créés mais pas envoyés.
Sur maquignon (production), l'e-mail part réellement.
