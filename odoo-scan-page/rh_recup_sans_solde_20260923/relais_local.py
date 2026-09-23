# -*- coding: utf-8 -*-
"""Relais /heures/rpc local (port 5055) branché sur la BASE DE TEST, pour tester les pages avant déploiement Render.
Même contrat que app.py : {action_id, ctx} -> {result} | {error:{message}}."""
import os, sys, ssl, json, importlib.util, xmlrpc.client
from flask import Flask, request, jsonify
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://testmaq230926v2.odoo.com', 'testmaq230926v2'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
def call(mo, me, *a, **k): return m.execute_kw(D, uid, p, mo, me, list(a), k)
spec = importlib.util.spec_from_file_location('ha', 'ocr/heures_actions.py'); ha = importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
AUTORISEES = {2012, 2013, 2014, 2020, 2021, 2048, 2050, 2069, 2090}
app = Flask(__name__)
def cors(r):
    r.headers['Access-Control-Allow-Origin'] = '*'; r.headers['Access-Control-Allow-Headers'] = 'Content-Type'; r.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'; return r
@app.route('/heures/rpc', methods=['POST', 'OPTIONS'])
def rpc():
    if request.method == 'OPTIONS': return cors(app.make_response(('', 204)))
    d = request.get_json(silent=True) or {}
    aid, ctx = d.get('action_id'), d.get('ctx')
    if aid not in AUTORISEES or not isinstance(ctx, dict): return cors(jsonify({'error': {'message': 'action non autorisée'}}))
    try:
        res = ha.executer(call, int(aid), ctx)
        print('OK', aid, {k: v for k, v in ctx.items() if k not in ('hj_token', 'hj_k', 'dc_token')}, '->', res, flush=True)
        return cors(jsonify({'result': res if isinstance(res, dict) else {}}))
    except ha.HeuresErreur as e:
        print('REF', aid, str(e)[:120], flush=True); return cors(jsonify({'error': {'message': str(e)}}))
    except xmlrpc.client.Fault as e:
        print('FAULT', aid, e.faultString[-300:], flush=True); return cors(jsonify({'error': {'message': (e.faultString or 'Erreur Odoo')[-400:]}}))
    except Exception as e:
        print('EXC', aid, repr(e)[:300], flush=True); return cors(jsonify({'error': {'message': 'Service indisponible : %s' % e}}))
if __name__ == '__main__':
    print('relais local -> base de test', D, 'uid', uid, flush=True)
    app.run(host='127.0.0.1', port=5055, debug=False)
