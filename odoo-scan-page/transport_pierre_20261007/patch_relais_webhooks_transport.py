# -*- coding: utf-8 -*-
"""Relais : route /odoo/transport/<quoi> pour les webhooks natifs Odoo des actions transport 2118 / 2119 / 2122
(plus de code Python facturé dans Odoo, Xavier 07/10/2026). La logique est dans transport_webhooks.py ; cette route
répond tout de suite (Odoo n'attend qu'une seconde) et traite dans un thread. ?host=<base de test> accepté.
  python patch_relais_webhooks_transport.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
p = os.path.join(R, 'app.py'); s = io.open(p, encoding='utf-8', newline='').read()


def rep(s, old, new, nom=''):
    assert s.count(old) == 1, 'ancre %s : %d' % (nom, s.count(old))
    return s.replace(old, new)


if '/odoo/transport/' in s:
    print('app.py : déjà patché'); sys.exit(0)

s = rep(s, '''def _hote_requete():
    donnees = request.get_json(silent=True) or {}
    return _hote_test(donnees.get("host")) or _hote_test(request.headers.get("Origin")) or _hote_test(request.headers.get("Referer"))''',
        '''def _hote_requete():
    donnees = request.get_json(silent=True) or {}
    return (_hote_test(request.args.get("host")) or _hote_test(donnees.get("host"))
            or _hote_test(request.headers.get("Origin")) or _hote_test(request.headers.get("Referer")))''', nom='hote')

ROUTE = '''# ─── WEBHOOKS ODOO « TRANSPORT DES COMMANDES PIERRE » ───────────────────────
# Actions serveur 2118 (bouton « Demander un tarif transport »), 2119 (automatisation 102 : achat transport confirmé)
# et 2122 (automatisation 103 : mode de transport du devis) converties en webhooks natifs le 07/10/2026 : plus aucune
# ligne de code Python facturée dans Odoo, la logique vit dans transport_webhooks.py. Odoo n'attend la réponse qu'une
# seconde (timeout=1 dans ir.actions.server) : la route répond tout de suite et le travail part dans un thread.
# ?host=testmaq….odoo.com (posé par transport_webhooks_setup.py sur une base de test) -> tout se passe sur cette base ;
# une copie de la production est de toute façon neutralisée par Odoo (webhook_url effacée).
TRANSPORT_WEBHOOKS = ("tarif", "achat-confirme", "mode-devis")


@app.route("/odoo/transport/<quoi>", methods=["POST"])
@require_secret
def odoo_transport_webhook(quoi):
    donnees = request.get_json(silent=True, force=True) or {}
    if quoi not in TRANSPORT_WEBHOOKS or not donnees.get("_id"):
        return jsonify({"error": "webhook inconnu ou _id absent"}), 400
    hote = _hote_requete()
    app.logger.info(f"webhook transport {quoi} reçu ({hote or 'production'}) : {donnees}")
    threading.Thread(target=_transport_webhook_traite, args=(quoi, donnees, hote), daemon=True).start()
    return jsonify({"status": "accepted", "quoi": quoi, "id": donnees["_id"], "base": hote or "production"})


def _transport_webhook_traite(quoi, donnees, hote):
    import transport_webhooks
    import web_actions
    call = None
    try:
        if hote:
            # connexion propre au thread (un proxy XML-RPC partagé n'est pas sûr entre threads)
            db = hote.split(".")[0]
            uid = xmlrpc.client.ServerProxy(f"https://{hote}/xmlrpc/2/common").authenticate(db, ODOO_USER, ODOO_PASSWORD, {})
            if not uid:
                raise ValueError(f"base de test {hote} : authentification refusée")
            models = xmlrpc.client.ServerProxy(f"https://{hote}/xmlrpc/2/object")

            def call(model, method, *params, **kw):
                return models.execute_kw(db, uid, ODOO_PASSWORD, model, method, list(params), kw)
        else:
            uid, models = odoo_connect()

            def call(model, method, *params, **kw):
                return x(models, uid, model, method, *params, **kw)
        res = transport_webhooks.transport_webhook(call, quoi, donnees)
        app.logger.info(f"webhook transport {quoi} #{donnees.get('_id')} ({hote or 'production'}) : {res}")
    except Exception as exc:  # noqa: BLE001
        app.logger.error(f"webhook transport {quoi} #{donnees.get('_id')} ({hote or 'production'}) : {exc}")
        if call is not None and donnees.get("_model"):
            web_actions._note(call, donnees["_model"], int(donnees["_id"]), f"❌ Transport (webhook {quoi}) : {str(exc)[-300:]}")


'''
s = rep(s, 'def _fab_dash_nightly():', ROUTE + 'def _fab_dash_nightly():', nom='route')
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('app.py : route /odoo/transport/<quoi> ajoutée, _hote_requete accepte ?host=')
