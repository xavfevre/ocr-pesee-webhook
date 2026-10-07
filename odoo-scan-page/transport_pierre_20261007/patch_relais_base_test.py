# -*- coding: utf-8 -*-
"""Relais : les pages d'une BASE DE TEST Odoo (hôte testmaq…odoo.com) sont servies sur cette base de test, jamais sur la
production (Xavier, 07/10/2026). L'hôte vient de l'en-tête Origin/Referer du navigateur (ou de `host` dans la requête) ;
même compte API que la production (la copie de base conserve les utilisateurs). CORS reflété pour ces hôtes.
  python patch_relais_base_test.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
p = os.path.join(R, 'app.py'); s = io.open(p, encoding='utf-8', newline='').read()


def rep(s, old, new, nom=''):
    assert s.count(old) == 1, 'ancre %s : %d' % (nom, s.count(old))
    return s.replace(old, new)


if '_hote_test(' in s:
    print('app.py : déjà patché'); sys.exit(0)
s = rep(s, """def _heures_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = HEURES_ORIGINE""", """_PROD_HOTE = (ODOO_URL or "").replace("https://", "").replace("http://", "").strip("/").lower()
_CONN_HOTES = {}   # hôte de base de test -> (uid, models, db)


def _hote_test(valeur):
    \"\"\"Hôte d'une base de test Odoo Online (copie de la production) tiré d'une origine, d'un referer ou d'un hôte ;
    None pour la production ou pour tout hôte inconnu.\"\"\"
    h = (valeur or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not h or h == _PROD_HOTE:
        return None
    return h if re.fullmatch(r"(testmaq|maquignon-)[a-z0-9-]*\\.odoo\\.com", h) else None


def _hote_requete():
    donnees = request.get_json(silent=True) or {}
    return _hote_test(donnees.get("host")) or _hote_test(request.headers.get("Origin")) or _hote_test(request.headers.get("Referer"))


def _connexion_hote(hote):
    \"\"\"(uid, models, db) pour une base de test ; mêmes identifiants que la production.\"\"\"
    if hote not in _CONN_HOTES:
        db = hote.split(".")[0]
        common = xmlrpc.client.ServerProxy(f"https://{hote}/xmlrpc/2/common")
        uid = common.authenticate(db, ODOO_USER, ODOO_PASSWORD, {})
        if not uid:
            raise ValueError(f"Base de test {hote} : authentification refusée (identifiants différents de la production ?)")
        _CONN_HOTES[hote] = (uid, xmlrpc.client.ServerProxy(f"https://{hote}/xmlrpc/2/object"), db)
    return _CONN_HOTES[hote]


def _heures_cors(resp):
    origine = request.headers.get("Origin") or ""
    resp.headers["Access-Control-Allow-Origin"] = origine if _hote_test(origine) else HEURES_ORIGINE""", nom='cors')
s = rep(s, """        if "uid" not in _HEURES_CONN:
            _HEURES_CONN["uid"], _HEURES_CONN["models"] = odoo_connect()
        uid, models = _HEURES_CONN["uid"], _HEURES_CONN["models"]

        def call(model, method, *params, **kw):
            return x(models, uid, model, method, *params, **kw)""", """        hote = _hote_requete()
        if hote:
            # page d'une base de test : tout se passe sur la base de test, rien n'est écrit en production
            try:
                t_uid, t_models, t_db = _connexion_hote(hote)
            except Exception as exc:  # noqa: BLE001
                return _heures_cors(jsonify({"error": {"message": f"Base de test {hote} : connexion impossible ({str(exc)[:120]})"}}))
            def call(model, method, *params, **kw):
                return t_models.execute_kw(t_db, t_uid, ODOO_PASSWORD, model, method, list(params), kw)
        else:
            if "uid" not in _HEURES_CONN:
                _HEURES_CONN["uid"], _HEURES_CONN["models"] = odoo_connect()
            uid, models = _HEURES_CONN["uid"], _HEURES_CONN["models"]
            def call(model, method, *params, **kw):
                return x(models, uid, model, method, *params, **kw)""", nom='connexion')
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('app.py : routage des pages de base de test vers leur base (Origin/Referer/host), CORS reflété')
