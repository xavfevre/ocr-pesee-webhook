# -*- coding: utf-8 -*-
"""Expédition des palettes, phase 2 (Xavier, 07/10/2026) :
  - champs de suivi sur la palette (stock.package) : statut, mode, transporteur, camion, chauffeur, date, chargé par, n° de
    chargement, lettre de voiture, date de livraison ; ajoutés au formulaire et à la liste Inventaire > Colis ;
  - page web /expedition (scan des bons de colisage, choix du mode, validation du départ, départs récents) qui appelle le
    relais Render (action 2104) ;
  - page web /expedition/liste?lot=CHG-… : liste de chargement imprimable (à signer).
  python expedition_setup.py dry | apply"""
import os, ssl, sys, re, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [1], 'active_test': False}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
esc = lambda t: t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
MODEL_PK = x('ir.model', 'search', [['model', '=', 'stock.package']])[0]
CAT_TRANSPORTEUR = x('res.partner.category', 'search', [['name', '=', 'Transporteur']])[0]

CHAMPS = [
    ('x_exp_statut', {'field_description': 'Statut expédition', 'ttype': 'selection',
                      'selection': "[('stock', 'En stock'), ('chargee', 'Chargée (départ enregistré)'), ('enlevee', 'Enlevée par le client'), ('livree', 'Livrée')]"}),
    ('x_exp_mode', {'field_description': "Mode d'expédition", 'ttype': 'selection',
                    'selection': "[('camions', 'Nos camions'), ('exterieur', 'Transporteur extérieur'), ('client', 'Enlèvement par le client')]"}),
    ('x_exp_transporteur_id', {'field_description': 'Transporteur', 'ttype': 'many2one', 'relation': 'res.partner'}),
    ('x_exp_camion', {'field_description': 'Camion / immatriculation', 'ttype': 'char'}),
    ('x_exp_chauffeur', {'field_description': 'Chauffeur / personne', 'ttype': 'char'}),
    ('x_exp_date', {'field_description': 'Date de départ', 'ttype': 'datetime'}),
    ('x_exp_par_id', {'field_description': 'Chargé par', 'ttype': 'many2one', 'relation': 'hr.employee'}),
    ('x_exp_lot', {'field_description': 'N° de chargement', 'ttype': 'char'}),
    ('x_exp_lettre', {'field_description': 'Lettre de voiture / référence', 'ttype': 'char'}),
    ('x_livraison_date', {'field_description': 'Date de livraison', 'ttype': 'datetime'}),
]

VUE_FORM = '''<data>
  <xpath expr="//sheet" position="inside">
    <group name="maq_expedition" string="Expédition">
      <group>
        <field name="x_exp_statut"/>
        <field name="x_exp_mode"/>
        <field name="x_exp_transporteur_id" domain="[('category_id', 'in', [%(cat)d])]"/>
        <field name="x_exp_camion"/>
        <field name="x_exp_chauffeur"/>
      </group>
      <group>
        <field name="x_exp_date"/>
        <field name="x_exp_par_id"/>
        <field name="x_exp_lot"/>
        <field name="x_exp_lettre"/>
        <field name="x_livraison_date"/>
      </group>
    </group>
  </xpath>
</data>'''

VUE_LIST = '''<data>
  <xpath expr="//%(racine)s" position="inside">
    <field name="x_exp_statut" optional="show"/>
    <field name="x_exp_date" optional="show"/>
    <field name="x_exp_lot" optional="hide"/>
    <field name="x_exp_transporteur_id" optional="hide"/>
  </xpath>
</data>'''

CSS_COMMUN = '''
      header#top, header.o_header_standard, footer, .o_footer, #o_cookies_bar, .o_bottom_fixed_element {display:none !important;}
      #wrapwrap > main {padding-top:0 !important;}
      body{background:#0f172a;}
      .scan-wrap{max-width:820px;margin:0 auto;padding:14px;}
      .scan-h{color:#e2e8f0;text-align:center;font-weight:300;letter-spacing:1px;margin:6px 0 12px;}
      .exp-card{background:#1e293b;border:2px solid #334155;border-radius:14px;padding:14px;margin-bottom:12px;}
      .exp-lbl{color:#94a3b8;font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}
      .exp-modes{display:flex;gap:8px;flex-wrap:wrap;}
      .exp-mode{flex:1;min-width:160px;border:2px solid #334155;border-radius:12px;padding:14px 10px;font-size:16px;font-weight:800;background:#0f172a;color:#e2e8f0;cursor:pointer;}
      .exp-mode.on{background:#0369a1;border-color:#38bdf8;color:#fff;}
      .exp-field{margin-top:10px;}
      .exp-field label{display:block;color:#94a3b8;font-size:12px;font-weight:700;text-transform:uppercase;margin-bottom:3px;}
      .exp-field select, .exp-field input{width:100%;font-size:18px;font-weight:700;padding:10px;border:2px solid #475569;border-radius:10px;background:#fff;color:#0f172a;}
      #scan-input{width:100%;font-size:30px;font-weight:800;text-align:center;padding:18px;border:4px solid #38bdf8;border-radius:14px;background:#fff;color:#0f172a;letter-spacing:2px;}
      #scan-input:focus{outline:none;border-color:#22d3ee;box-shadow:0 0 0 4px rgba(34,211,238,.35);}
      .scan-res{border-radius:10px;padding:10px 14px;text-align:center;font-size:16px;font-weight:700;display:flex;align-items:center;justify-content:center;margin-top:10px;}
      .scan-res.ok{background:#065f46;color:#d1fae5;} .scan-res.info{background:#1e3a8a;color:#dbeafe;} .scan-res.warn{background:#92400e;color:#fef3c7;}
      .scan-res.err{background:#991b1b;color:#fee2e2;} .scan-res.idle{background:#0f172a;color:#64748b;}
      .exp-pal{display:flex;gap:8px;align-items:flex-start;background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px;margin-top:8px;}
      .exp-pal.warn{border-color:#f59e0b;}
      .exp-pal-main{flex:1;min-width:0;} .exp-pal-name{color:#fff;font-size:20px;font-weight:900;} .exp-pal-zone{color:#5eead4;font-size:13px;font-weight:700;margin-left:6px;}
      .exp-pal-meta{color:#cbd5e1;font-size:13px;margin-top:2px;word-break:break-word;}
      .exp-del{border:none;border-radius:10px;background:#7f1d1d;color:#fff;font-size:18px;padding:10px 12px;cursor:pointer;}
      .exp-alert{background:#92400e;color:#fef3c7;border-radius:10px;padding:8px 12px;font-weight:800;margin-top:8px;}
      .exp-empty{color:#64748b;font-size:14px;padding:6px 0;}
      #exp-total{color:#5eead4;font-weight:800;font-size:16px;margin-top:10px;text-align:right;}
      .exp-go{width:100%;border:none;border-radius:12px;padding:18px;font-size:20px;font-weight:900;background:#16a34a;color:#fff;cursor:pointer;}
      .exp-go:disabled{opacity:.4;cursor:default;}
      .exp-btn{border:none;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;cursor:pointer;background:#1d4ed8;color:#fff;margin:6px 6px 0 0;}
      .exp-btn.sec{background:#334155;color:#e2e8f0;} .exp-btn.red{background:#7f1d1d;}
      #exp-result{background:#065f46;color:#d1fae5;border-radius:12px;padding:14px;margin-top:10px;font-weight:800;font-size:16px;}
      .exp-lot{background:#0f172a;border:1px solid #334155;border-radius:10px;padding:10px;margin-top:8px;color:#e2e8f0;font-size:14px;}
      .exp-lot b{color:#fff;} .exp-lot .pals{color:#94a3b8;font-size:13px;margin-top:4px;}
      #btn-cam{width:100%;margin-top:10px;border:none;border-radius:12px;padding:14px;font-size:17px;font-weight:800;cursor:pointer;background:#0284c7;color:#fff;}
      .cam-pop{display:none;position:fixed;inset:0;background:#000;z-index:99999;}
      .cam-pop video{width:100%;height:100%;object-fit:cover;}
      .cam-pop .cam-close{position:absolute;top:14px;right:14px;border:none;border-radius:12px;padding:12px 18px;font-size:18px;font-weight:900;background:#7f1d1d;color:#fff;}
      .cam-pop .cam-msg{position:absolute;bottom:20px;left:0;right:0;text-align:center;color:#fff;font-weight:800;text-shadow:0 1px 4px #000;}
'''

JS_PAGE = r'''
(function(){
  var RENDER = 'https://ocr-pesee-webhook.onrender.com/heures/rpc';
  var KEY = 'exp_chargement_v1';
  var MODES = {camions: 'Nos camions', exterieur: 'Transporteur extérieur', client: 'Enlèvement par le client'};
  var st = {mode: '', transporteur_id: 0, camion: '', chauffeur: '', charge_par: 0, lettre: '', palettes: []};
  try{ var s0 = JSON.parse(localStorage.getItem(KEY) || 'null'); if(s0 && s0.palettes){ st = s0; } }catch(e){}
  var input = document.getElementById('scan-input'), resEl = document.getElementById('scan-res'), busy = false;
  var btnValider = document.getElementById('btn-valider');
  function esc(s){ var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }
  function save(){ try{ localStorage.setItem(KEY, JSON.stringify(st)); }catch(e){} }
  function setRes(txt, cls){ resEl.textContent = txt; resEl.className = 'scan-res ' + (cls || 'idle'); }
  function beep(good){ try{ var c = new (window.AudioContext || window.webkitAudioContext)(); var o = c.createOscillator(); var g = c.createGain(); o.connect(g); g.connect(c.destination); o.frequency.value = good ? 880 : 220; g.gain.value = 0.12; o.start(); setTimeout(function(){ o.stop(); c.close(); }, good ? 110 : 260); }catch(e){} }
  function web(mode, extra){
    var ctx = {mode: mode};
    if(extra){ for(var k in extra){ if(Object.prototype.hasOwnProperty.call(extra, k)){ ctx[k] = extra[k]; } } }
    return fetch(RENDER, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action_id: 2104, ctx: ctx})})
      .then(function(r){ return r.json(); })
      .then(function(d){ if(d.error){ throw new Error(d.error.message || 'Erreur'); } return d.result || {}; });
  }
  function show(id, on){ var e = document.getElementById(id); if(e){ e.style.display = on ? '' : 'none'; } }
  function val(id, v){ var e = document.getElementById(id); if(e){ e.value = (v == null ? '' : String(v)); } }
  function get(id){ var e = document.getElementById(id); return e ? e.value : ''; }
  function lireForm(){
    st.transporteur_id = parseInt(get('exp-transporteur')) || 0;
    st.camion = (st.mode === 'camions') ? get('exp-camion') : get('exp-immat');
    st.chauffeur = get('exp-chauffeur'); st.charge_par = parseInt(get('exp-par')) || 0; st.lettre = get('exp-lettre');
    save();
  }
  function renderMode(){
    document.querySelectorAll('.exp-mode').forEach(function(b){ b.className = 'exp-mode' + (b.getAttribute('data-mode') === st.mode ? ' on' : ''); });
    show('exp-f-camion', st.mode === 'camions'); show('exp-f-transporteur', st.mode === 'exterieur');
    show('exp-f-immat', st.mode === 'exterieur' || st.mode === 'client'); show('exp-f-chauffeur', !!st.mode); show('exp-f-lettre', st.mode === 'exterieur');
    var lbl = document.getElementById('exp-chauffeur-lbl'); if(lbl){ lbl.textContent = st.mode === 'client' ? 'Personne qui enlève (nom)' : 'Chauffeur (facultatif)'; }
    val('exp-camion', st.mode === 'camions' ? st.camion : ''); val('exp-immat', st.mode === 'camions' ? '' : st.camion);
    val('exp-transporteur', st.transporteur_id || 0); val('exp-chauffeur', st.chauffeur); val('exp-par', st.charge_par || 0); val('exp-lettre', st.lettre);
  }
  function renderList(){
    var box = document.getElementById('exp-list'), tot = document.getElementById('exp-total');
    if(!st.palettes.length){ box.innerHTML = '<div class="exp-empty">Aucune palette scannée pour l\'instant.</div>'; tot.textContent = ''; btnValider.disabled = true; return; }
    var clients = {}; st.palettes.forEach(function(p){ clients[p.client || '?'] = 1; });
    var multi = Object.keys(clients).length > 1;
    box.innerHTML = (multi ? '<div class="exp-alert">⚠️ Palettes de plusieurs clients dans le même chargement : vérifiez avant de valider.</div>' : '')
      + st.palettes.map(function(p, i){
        return '<div class="exp-pal' + (multi ? ' warn' : '') + '"><div class="exp-pal-main"><div class="exp-pal-name">📦 ' + esc(p.name) + '<span class="exp-pal-zone">' + esc(p.zone) + '</span></div>'
          + '<div class="exp-pal-meta">' + esc(p.client) + (p.commande ? ' · ' + esc(p.commande) : '') + (p.adresse ? '<br/>📍 ' + esc(p.adresse) : '') + '</div>'
          + '<div class="exp-pal-meta">' + p.n + ' OF · ' + p.ton + ' kg · ' + p.cub + ' m³' + (p.contenu ? ' · ' + esc(p.contenu) : '') + '</div></div>'
          + '<button type="button" class="exp-del" data-i="' + i + '" title="Retirer du chargement">🗑️</button></div>';
      }).join('');
    var ton = 0, cub = 0; st.palettes.forEach(function(p){ ton += (p.ton || 0); cub += (p.cub || 0); });
    tot.textContent = st.palettes.length + ' palette(s) · ' + Math.round(ton) + ' kg · ' + (Math.round(cub * 1000) / 1000) + ' m³';
    btnValider.disabled = false;
    box.querySelectorAll('.exp-del').forEach(function(b){ b.onclick = function(){ st.palettes.splice(parseInt(b.getAttribute('data-i')), 1); save(); renderList(); }; });
  }
  function doScan(v){
    input.value = ''; v = (v || '').trim(); if(!v || busy){ return; }
    busy = true; setRes('⏳ …', 'idle');
    web('scanner', {code: v}).then(function(p){
      busy = false;
      if(st.palettes.some(function(q){ return q.id === p.id; })){ setRes('ℹ️ ' + p.name + ' est déjà dans le chargement', 'info'); beep(false); input.focus(); return; }
      st.palettes.push(p);
      if(!st.mode && p.mode_devis){ st.mode = p.mode_devis; if(p.transporteur_devis_id){ st.transporteur_id = p.transporteur_devis_id; } renderMode(); setRes('✅ ' + p.name + ' ajoutée — mode prévu au devis : ' + (MODES[p.mode_devis] || p.mode_devis) + (p.transporteur_devis ? ' (' + p.transporteur_devis + ')' : ''), 'ok'); }
      else { setRes('✅ ' + p.name + ' ajoutée (' + (p.client || '?') + ', ' + p.ton + ' kg)', 'ok'); }
      save(); renderList(); beep(true); input.focus();
    }).catch(function(e){ busy = false; setRes(String(e && e.message ? e.message : e), 'err'); beep(false); input.focus(); });
  }
  document.querySelectorAll('.exp-mode').forEach(function(b){ b.addEventListener('click', function(){ lireForm(); st.mode = b.getAttribute('data-mode'); save(); renderMode(); }); });
  ['exp-transporteur', 'exp-camion', 'exp-immat', 'exp-chauffeur', 'exp-par', 'exp-lettre'].forEach(function(id){ var e = document.getElementById(id); if(e){ e.addEventListener('change', lireForm); } });
  input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); doScan(input.value); } });
  document.addEventListener('keydown', function(e){
    var t = document.activeElement; if(t === input || (t && (t.tagName === 'INPUT' || t.tagName === 'SELECT' || t.tagName === 'TEXTAREA'))){ return; }
    if(e.key && e.key.length === 1){ input.focus(); }
  });
  btnValider.addEventListener('click', function(){
    lireForm();
    if(!st.mode){ setRes('⚠️ Choisissez d\'abord qui transporte (étape 1)', 'warn'); return; }
    var qui = st.mode === 'camions' ? ('nos camions — ' + (st.camion || '?')) : (st.mode === 'exterieur' ? ('transporteur ' + ((document.getElementById('exp-transporteur').selectedOptions[0] || {}).text || '?')) : ('enlèvement par ' + (st.chauffeur || '?')));
    if(!confirm('Valider le départ de ' + st.palettes.length + ' palette(s) — ' + qui + ' ?')){ return; }
    btnValider.disabled = true; setRes('⏳ Enregistrement du départ…', 'idle');
    web('valider', {palettes: st.palettes.map(function(p){ return p.id; }), exp_mode: st.mode, transporteur_id: st.transporteur_id, camion: st.camion, chauffeur: st.chauffeur, charge_par: st.charge_par, lettre: st.lettre})
      .then(function(r){
        setRes(r.msg || '✅ Départ enregistré', 'ok'); beep(true);
        var box = document.getElementById('exp-result');
        box.style.display = ''; box.innerHTML = esc(r.msg) + '<div style="margin-top:10px;"><button type="button" class="exp-btn" id="exp-print">🖨 Liste de chargement</button><button type="button" class="exp-btn sec" id="exp-new">🆕 Nouveau chargement</button></div>';
        document.getElementById('exp-print').onclick = function(){ window.open(r.liste_url, '_blank'); };
        document.getElementById('exp-new').onclick = function(){ box.style.display = 'none'; st = {mode: '', transporteur_id: 0, camion: '', chauffeur: '', charge_par: st.charge_par, lettre: '', palettes: []}; save(); renderMode(); renderList(); setRes('En attente d\'un scan…', 'idle'); input.focus(); };
        st.palettes = []; st.lettre = ''; save(); renderList(); chargerLots();
      }).catch(function(e){ btnValider.disabled = false; setRes('⚠️ ' + (e && e.message ? e.message : e), 'err'); beep(false); });
  });
  function chargerLots(){
    var box = document.getElementById('exp-lots'); box.innerHTML = '<div class="exp-empty">Chargement…</div>';
    web('lots', {jours: 3}).then(function(r){
      var lots = r.lots || [];
      if(!lots.length){ box.innerHTML = '<div class="exp-empty">Aucun départ ces 3 derniers jours.</div>'; return; }
      box.innerHTML = lots.map(function(l){
        return '<div class="exp-lot"><b>' + esc(l.lot) + '</b> · ' + esc(l.date) + ' · ' + esc(MODES[l.mode] || l.mode) + (l.qui ? ' · ' + esc(l.qui) : '') + ' · ' + l.n + ' palette(s) · ' + l.ton + ' kg' + (l.clients ? ' · ' + esc(l.clients) : '')
          + '<div class="pals">' + l.palettes.map(function(p){ return esc(p.name) + ' <button type="button" class="exp-btn red exp-annul" style="padding:3px 8px;font-size:12px;" data-id="' + p.id + '" data-name="' + esc(p.name) + '">↩️ annuler</button>'; }).join(' · ') + '</div>'
          + '<button type="button" class="exp-btn sec exp-reprint" data-lot="' + esc(l.lot) + '">🖨 Liste de chargement</button></div>';
      }).join('');
      box.querySelectorAll('.exp-reprint').forEach(function(b){ b.onclick = function(){ window.open('/expedition/liste?lot=' + encodeURIComponent(b.getAttribute('data-lot')), '_blank'); }; });
      box.querySelectorAll('.exp-annul').forEach(function(b){ b.onclick = function(){
        if(!confirm('Annuler le départ de ' + b.getAttribute('data-name') + ' ? La palette redevient « en stock ».')){ return; }
        web('annuler', {palette_id: parseInt(b.getAttribute('data-id'))}).then(function(r){ setRes(r.msg || '↩️ annulé', 'info'); chargerLots(); }).catch(function(e){ setRes('⚠️ ' + (e && e.message ? e.message : e), 'err'); });
      }; });
    }).catch(function(e){ box.innerHTML = '<div class="exp-empty">Erreur : ' + esc(e && e.message ? e.message : e) + '</div>'; });
  }
  document.getElementById('btn-lots').addEventListener('click', chargerLots);
  // caméra (tablette)
  var camPop = document.getElementById('cam-pop'), camVid = document.getElementById('cam-video'), camMsg = document.getElementById('cam-msg'), camStream = null, camTimer = null;
  function camStop(){ if(camTimer){ clearInterval(camTimer); camTimer = null; } if(camStream){ camStream.getTracks().forEach(function(t){ t.stop(); }); camStream = null; } if(camVid){ camVid.srcObject = null; } if(camPop){ camPop.style.display = 'none'; } }
  function camOpen(onCode){
    if(!window.BarcodeDetector){ setRes('⚠️ Scanner caméra non supporté par ce navigateur — utilisez la douchette', 'warn'); return; }
    if(!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)){ setRes('⚠️ Caméra indisponible sur cet appareil', 'warn'); return; }
    camPop.style.display = 'block'; if(camMsg){ camMsg.textContent = 'Visez le code-barre du bon de colisage…'; }
    navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: {ideal: 'environment'}, width: {ideal: 1280}, height: {ideal: 720}}}).then(function(s){ camStream = s; camVid.srcObject = s; return camVid.play(); }).then(function(){
      var det; try{ det = new BarcodeDetector({formats: ['code_128', 'code_39', 'ean_13', 'qr_code']}); }catch(e){ det = new BarcodeDetector(); }
      var b2 = false;
      camTimer = setInterval(function(){
        if(b2 || !camStream || camVid.readyState < 2){ return; }
        b2 = true;
        det.detect(camVid).then(function(codes){ b2 = false; var v = ''; for(var i = 0; i < codes.length; i++){ if(codes[i].rawValue && codes[i].rawValue.trim()){ v = codes[i].rawValue.trim(); break; } } if(!v){ return; } camStop(); try{ if(navigator.vibrate){ navigator.vibrate(90); } }catch(e){} onCode(v); }).catch(function(){ b2 = false; });
      }, 220);
    }).catch(function(err){ camStop(); setRes('⚠️ Caméra inaccessible : ' + ((err && err.message) || err), 'warn'); });
  }
  document.getElementById('cam-close').addEventListener('click', function(){ camStop(); input.focus(); });
  document.getElementById('btn-cam').addEventListener('click', function(){ camOpen(function(v){ doScan(v); }); });
  renderMode(); renderList(); chargerLots(); input.focus();
})();
'''

PAGE = '''<t t-name="website.expedition_page">
  <t t-call="website.layout">
    <style>%(css)s</style>
    <t t-set="transporteurs" t-value="request.env['res.partner'].sudo().search([('category_id', 'in', [%(cat)d])], order='name')"/>
    <t t-set="camions" t-value="request.env['delivery.carrier'].sudo().search([('active', '=', True), ('company_id', 'in', [1, False]), ('name', 'not ilike', 'Retrait'), ('name', 'not ilike', 'Standard')], order='name')"/>
    <t t-set="chargeurs" t-value="request.env['hr.employee'].sudo().search([('company_id', '=', 1), ('active', '=', True)], order='name')"/>
    <div class="scan-wrap">
      <ul class="nav nav-tabs mb-2 flex-nowrap overflow-auto" style="font-size:16px;white-space:nowrap;background:#fff;border-radius:8px 8px 0 0;padding:4px 6px 0;"><li class="nav-item"><a class="nav-link" href="/vue-operateur">✅ Ma production</a></li><li class="nav-item"><a class="nav-link" href="/vue-operateur?hist=1">🕘 Historique</a></li><li class="nav-item"><a class="nav-link" href="/scan">📦 Poste de scan</a></li><li class="nav-item"><a class="nav-link active fw-bold" href="#">🚚 Expédition</a></li></ul>
      <h3 class="scan-h">🚚 Expédition — départ des palettes</h3>
      <div class="exp-card">
        <div class="exp-lbl">1. Qui transporte ?</div>
        <div class="exp-modes">
          <button type="button" class="exp-mode" data-mode="camions">🚛 Nos camions</button>
          <button type="button" class="exp-mode" data-mode="exterieur">🏢 Transporteur extérieur</button>
          <button type="button" class="exp-mode" data-mode="client">🤝 Enlèvement par le client</button>
        </div>
        <div id="exp-f-camion" class="exp-field" style="display:none;"><label>Camion</label>
          <select id="exp-camion"><option value="">— choisir le camion —</option><t t-foreach="camions" t-as="cm"><option t-att-value="cm.name"><t t-esc="cm.name"/></option></t></select></div>
        <div id="exp-f-transporteur" class="exp-field" style="display:none;"><label>Transporteur</label>
          <select id="exp-transporteur"><option value="0">— choisir le transporteur —</option><t t-foreach="transporteurs" t-as="tr"><option t-att-value="tr.id"><t t-esc="tr.name"/></option></t></select></div>
        <div id="exp-f-immat" class="exp-field" style="display:none;"><label>Immatriculation du camion</label><input id="exp-immat" type="text" autocomplete="off" autocapitalize="characters"/></div>
        <div id="exp-f-chauffeur" class="exp-field" style="display:none;"><label id="exp-chauffeur-lbl">Chauffeur</label><input id="exp-chauffeur" type="text" autocomplete="off"/></div>
        <div class="exp-field"><label>Chargé par</label>
          <select id="exp-par"><option value="0">— qui charge —</option><t t-foreach="chargeurs" t-as="em"><option t-att-value="em.id"><t t-esc="em.name"/></option></t></select></div>
        <div id="exp-f-lettre" class="exp-field" style="display:none;"><label>N° de lettre de voiture / référence (facultatif)</label><input id="exp-lettre" type="text" autocomplete="off"/></div>
      </div>
      <div class="exp-card">
        <div class="exp-lbl">2. Scannez les bons de colisage</div>
        <input id="scan-input" type="text" autocomplete="off" autocorrect="off" autocapitalize="characters" spellcheck="false" placeholder="Scanner le bon de colisage…"/>
        <button type="button" id="btn-cam">📷 Scanner avec la caméra</button>
        <div id="scan-res" class="scan-res idle">En attente d'un scan…</div>
        <div id="exp-list"/>
        <div id="exp-total"/>
      </div>
      <div class="exp-card">
        <div class="exp-lbl">3. Départ</div>
        <button type="button" id="btn-valider" class="exp-go" disabled="disabled">🚚 Valider le départ</button>
        <div id="exp-result" style="display:none;"/>
      </div>
      <div class="exp-card">
        <div class="exp-lbl">Départs des 3 derniers jours <button type="button" id="btn-lots" class="exp-btn sec" style="padding:4px 10px;font-size:13px;">↻</button></div>
        <div id="exp-lots"/>
      </div>
    </div>
    <div id="cam-pop" class="cam-pop"><video id="cam-video" playsinline="playsinline" muted="muted"/><button type="button" id="cam-close" class="cam-close">✖ Fermer</button><div id="cam-msg" class="cam-msg"/></div>
    <script>%(js)s</script>
  </t>
</t>'''

LISTE = '''<t t-name="website.expedition_liste">
  <t t-call="website.layout">
    <style>
      header#top, header.o_header_standard, footer, .o_footer, #o_cookies_bar, .o_bottom_fixed_element {display:none !important;}
      #wrapwrap > main {padding-top:0 !important;}
      .lc-wrap{max-width:900px;margin:0 auto;padding:16px;font-family:Arial,Helvetica,sans-serif;color:#0f172a;font-size:13px;}
      .lc-h{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid #01666B;padding-bottom:8px;margin-bottom:12px;}
      .lc-h h2{margin:0;color:#01666B;font-size:22px;}
      .lc-box{border:1px solid #cbd5e1;border-radius:8px;padding:10px;margin-bottom:12px;page-break-inside:avoid;}
      .lc-box h3{margin:0 0 6px;font-size:15px;color:#01666B;}
      table.lc{width:100%;border-collapse:collapse;margin-top:6px;}
      table.lc th, table.lc td{border:1px solid #cbd5e1;padding:5px 6px;text-align:left;vertical-align:top;}
      table.lc th{background:#eaf4f4;}
      .lc-tot{font-weight:800;text-align:right;margin-top:6px;}
      .lc-sign{display:flex;gap:12px;margin-top:16px;}
      .lc-sign div{flex:1;border:1px solid #94a3b8;border-radius:8px;height:110px;padding:6px;font-weight:700;color:#64748b;}
      .lc-print{position:fixed;right:16px;top:16px;background:#01666B;color:#fff;border:none;border-radius:10px;padding:12px 18px;font-weight:800;font-size:15px;cursor:pointer;}
      @media print { .lc-print{display:none;} .lc-wrap{max-width:none;padding:0;} }
    </style>
    <t t-set="lot" t-value="(request.params.get('lot') or '').strip()"/>
    <t t-set="pals" t-value="request.env['stock.package'].sudo().search([('x_exp_lot', '=', lot)], order='name') if lot else request.env['stock.package'].sudo().browse([])"/>
    <t t-set="modes" t-value="{'camions': 'Nos camions', 'exterieur': 'Transporteur extérieur', 'client': 'Enlèvement par le client'}"/>
    <div class="lc-wrap">
      <button class="lc-print" onclick="window.print()">🖨 Imprimer</button>
      <t t-if="not pals"><h2>Liste de chargement</h2><p>Aucune palette pour le chargement « <t t-esc="lot"/> ».</p></t>
      <t t-else="">
        <t t-set="p0" t-value="pals[0]"/>
        <div class="lc-h">
          <div><h2>SARL MAQUIGNON — Liste de chargement</h2><div>Carrières Maquignon · 51 rue du Prieuré · 86230 Usseau · 05 49 02 72 63</div></div>
          <div style="text-align:right;"><div style="font-size:18px;font-weight:900;"><t t-esc="lot"/></div><div>Départ le <span t-field="p0.x_exp_date" t-options="{'widget': 'datetime', 'format': 'dd/MM/yyyy HH:mm'}"/></div></div>
        </div>
        <div class="lc-box">
          <h3>Transport</h3>
          <div><b>Mode :</b> <t t-esc="modes.get(p0.x_exp_mode or '', '')"/>
            <t t-if="p0.x_exp_transporteur_id"> · <b>Transporteur :</b> <t t-esc="p0.x_exp_transporteur_id.name"/></t>
            <t t-if="p0.x_exp_camion"> · <b>Camion / immatriculation :</b> <t t-esc="p0.x_exp_camion"/></t>
            <t t-if="p0.x_exp_chauffeur"> · <b><t t-esc="'Personne' if p0.x_exp_mode == 'client' else 'Chauffeur'"/> :</b> <t t-esc="p0.x_exp_chauffeur"/></t>
            <t t-if="p0.x_exp_lettre"> · <b>Lettre de voiture :</b> <t t-esc="p0.x_exp_lettre"/></t>
            <t t-if="p0.x_exp_par_id"> · <b>Chargé par :</b> <t t-esc="p0.x_exp_par_id.name"/></t>
          </div>
        </div>
        <t t-set="groupes" t-value="{}"/>
        <t t-set="_g" t-value="[groupes.setdefault(pp.x_commande_id.id or 0, []).append(pp) for pp in pals]"/>
        <t t-foreach="groupes.items()" t-as="g">
          <t t-set="so" t-value="g[1][0].x_commande_id"/>
          <div class="lc-box">
            <h3><t t-esc="so.name if so else 'Sans commande'"/> — <t t-esc="so.partner_id.name if so else (g[1][0].x_studio_client or '')"/></h3>
            <t t-if="so and so.partner_shipping_id"><div><b>Livraison :</b> <t t-esc="so.partner_shipping_id.name"/>, <t t-esc="so.partner_shipping_id.street or ''"/> <t t-esc="so.partner_shipping_id.street2 or ''"/> <t t-esc="so.partner_shipping_id.zip or ''"/> <t t-esc="so.partner_shipping_id.city or ''"/><t t-if="so.partner_shipping_id.phone"> · ☎ <t t-esc="so.partner_shipping_id.phone"/></t></div></t>
            <table class="lc"><tr><th>Palette</th><th>Emplacement</th><th>Contenu (OF)</th><th>Poids</th><th>Volume</th></tr>
              <t t-foreach="g[1]" t-as="pp">
                <t t-set="reps" t-value="request.env['x_repartition_palette'].sudo().search([('x_studio_colis_id', '=', pp.id)])"/>
                <tr><td><b><t t-esc="pp.name"/></b></td><td><t t-esc="pp.x_studio_zone or ''"/></td>
                  <td><t t-esc="', '.join(pp.x_studio_one2many_field_55p_1jh99tbrr.mapped('name') + ['%s x%d' % (rr.x_studio_of_id.name, int(rr.x_studio_qte or 0)) for rr in reps if rr.x_studio_of_id])"/></td>
                  <td style="text-align:right;"><t t-esc="'%.0f kg' % (pp.x_studio_tonnage or 0)"/></td><td style="text-align:right;"><t t-esc="'%.3f m³' % (pp.x_studio_cubage or 0)"/></td></tr>
              </t>
            </table>
            <div class="lc-tot"><t t-esc="len(g[1])"/> palette(s) · <t t-esc="'%.0f' % sum([(pp.x_studio_tonnage or 0) for pp in g[1]])"/> kg · <t t-esc="'%.3f' % sum([(pp.x_studio_cubage or 0) for pp in g[1]])"/> m³</div>
          </div>
        </t>
        <div class="lc-tot" style="font-size:15px;">TOTAL : <t t-esc="len(pals)"/> palette(s) · <t t-esc="'%.0f' % sum([(pp.x_studio_tonnage or 0) for pp in pals])"/> kg · <t t-esc="'%.3f' % sum([(pp.x_studio_cubage or 0) for pp in pals])"/> m³</div>
        <div class="lc-sign"><div>Chargeur (Maquignon)</div><div><t t-esc="'Client (enlèvement)' if p0.x_exp_mode == 'client' else 'Chauffeur / transporteur'"/></div><div>Réserves</div></div>
      </t>
    </div>
  </t>
</t>'''


def etat():
    champs = {f['name']: f['id'] for f in x('ir.model.fields', 'search_read', [['model', '=', 'stock.package'], ['name', 'in', [n for n, _ in CHAMPS]]], fields=['name'])}
    vues = {v['key'] or v['name']: v['id'] for v in x('ir.ui.view', 'search_read', [['key', 'in', ['website.expedition_page', 'website.expedition_liste', 'maq.stock_package_expedition_form', 'maq.stock_package_expedition_list']]], fields=['key', 'name'])}
    pages = {pg['url']: pg['id'] for pg in x('website.page', 'search_read', [['url', 'in', ['/expedition', '/expedition/liste']]], fields=['url'])}
    return champs, vues, pages


champs, vues, pages = etat()
print('état : champs %s | vues %s | pages %s' % (sorted(champs), vues, pages))
if mode != 'apply':
    print('simulation : rien modifié'); sys.exit(0)

for name, vals in CHAMPS:
    if name in champs:
        continue
    v = dict(vals); v.update({'name': name, 'model_id': MODEL_PK, 'state': 'manual', 'store': True, 'copied': False})
    champs[name] = one(x('ir.model.fields', 'create', [v]))
print('champs palette :', champs)

# formulaire et liste Inventaire > Colis
arch_list = x('ir.ui.view', 'read', [1904], ['arch_db'])[0]['arch_db']
racine = 'list' if '<list' in arch_list else 'tree'
for key, nom, modele, base, arch in (('maq.stock_package_expedition_form', 'Palette - expédition (formulaire)', 'form', 1903, VUE_FORM % {'cat': CAT_TRANSPORTEUR}),
                                      ('maq.stock_package_expedition_list', 'Palette - expédition (liste)', 'list', 1904, VUE_LIST % {'racine': racine})):
    if key in vues:
        x('ir.ui.view', 'write', [vues[key]], {'arch_db': arch})
    else:
        vues[key] = one(x('ir.ui.view', 'create', [{'name': nom, 'key': key, 'model': 'stock.package', 'type': modele, 'inherit_id': base, 'mode': 'extension', 'priority': 200, 'arch_db': arch}]))
print('vues colis :', {k: v for k, v in vues.items() if k.startswith('maq.')})

# pages web
arch_page = PAGE % {'css': CSS_COMMUN, 'cat': CAT_TRANSPORTEUR, 'js': esc(JS_PAGE)}
for key, nom, url, arch in (('website.expedition_page', 'Expédition palettes', '/expedition', arch_page), ('website.expedition_liste', 'Liste de chargement', '/expedition/liste', LISTE)):
    if key in vues:
        x('ir.ui.view', 'write', [vues[key]], {'arch_db': arch})
    else:
        vues[key] = one(x('ir.ui.view', 'create', [{'name': nom, 'key': key, 'type': 'qweb', 'arch_db': arch}]))
    if url not in pages:
        pages[url] = one(x('website.page', 'create', [{'name': nom, 'url': url, 'view_id': vues[key], 'is_published': True, 'website_id': False}]))
print('pages :', pages, '| vues :', {k: v for k, v in vues.items() if k.startswith('website.')})
