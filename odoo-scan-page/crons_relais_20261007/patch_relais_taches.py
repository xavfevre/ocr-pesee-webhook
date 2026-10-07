# -*- coding: utf-8 -*-
"""Relais : route /odoo/tache (webhook natif Odoo à la création d'une « tâche relais » x_relais_tache) et aide
_appel_thread(hote) partagée avec les webhooks transport. Logique des tâches dans taches_relais.py.
  python patch_relais_taches.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
p = os.path.join(R, 'app.py'); s = io.open(p, encoding='utf-8', newline='').read()


def rep(s, old, new, nom=''):
    assert s.count(old) == 1, 'ancre %s : %d' % (nom, s.count(old))
    return s.replace(old, new)


if '/odoo/tache' in s:
    print('app.py : déjà patché'); sys.exit(0)

# connexion par thread partagée
s = rep(s, '''def _transport_webhook_traite(quoi, donnees, hote):
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
        res = transport_webhooks.transport_webhook(call, quoi, donnees)''',
        '''def _appel_thread(hote):
    """Fonction call(model, method, *params, **kw) sur une connexion propre au thread (un proxy XML-RPC partagé n'est
    pas sûr entre threads) : production, ou base de test si hote est renseigné."""
    if hote:
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
    return call


def _transport_webhook_traite(quoi, donnees, hote):
    import transport_webhooks
    import web_actions
    call = None
    try:
        call = _appel_thread(hote)
        res = transport_webhooks.transport_webhook(call, quoi, donnees)''', nom='appel_thread')

ROUTE = '''# ─── TÂCHES PLANIFIÉES PORTÉES SUR LE RELAIS (x_relais_tache) ────────────────
# Les crons Odoo (parc auto, CACES, récup, fériés) n'ont plus de code : leur action crée un enregistrement
# x_relais_tache dont le nom est la clé de la tâche ; l'automatisation « à la création » appelle ce webhook et
# taches_relais.executer fait le travail puis écrit l'état et le résultat sur l'enregistrement (journal dans Odoo).
@app.route("/odoo/tache", methods=["POST"])
@require_secret
def odoo_tache_webhook():
    donnees = request.get_json(silent=True, force=True) or {}
    if donnees.get("_model") != "x_relais_tache" or not donnees.get("_id"):
        return jsonify({"error": "payload inattendu"}), 400
    hote = _hote_requete()
    nom = donnees.get("x_name") or ""
    app.logger.info(f"tâche relais {nom} #{donnees['_id']} reçue ({hote or 'production'})")
    threading.Thread(target=_tache_traite, args=(int(donnees["_id"]), nom, hote), daemon=True).start()
    return jsonify({"status": "accepted", "tache": nom, "id": donnees["_id"], "base": hote or "production"})


def _tache_traite(tache_id, nom, hote):
    import taches_relais
    try:
        res = taches_relais.executer(_appel_thread(hote), tache_id, nom)
        app.logger.info(f"tâche relais {nom} #{tache_id} ({hote or 'production'}) : {str(res)[:300]}")
    except Exception as exc:  # noqa: BLE001
        app.logger.error(f"tâche relais {nom} #{tache_id} ({hote or 'production'}) : {exc}")


'''
s = rep(s, 'def _fab_dash_nightly():', ROUTE + 'def _fab_dash_nightly():', nom='route')
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('app.py : route /odoo/tache ajoutée, _appel_thread partagé')
