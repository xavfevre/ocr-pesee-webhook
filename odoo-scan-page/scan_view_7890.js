(function(){
  var qp = new URLSearchParams(window.location.search);
  var SITE = (qp.get('poste') === '2' || /usine/i.test(qp.get('site') || '')) ? 'USINE' : 'ATELIER';
  var h = document.querySelector('.scan-h');
  if(h){ h.textContent = '📦 Poste de scan — ' + SITE + ' — Palettes / OF'; }
  document.title = 'Poste de scan ' + SITE + ' | Maquignon';
  var RENDER = 'https://ocr-pesee-webhook.onrender.com/heures/rpc';
  var input = document.getElementById('scan-input');
  var resEl = document.getElementById('scan-res');
  var colisEl = document.getElementById('colis-name');
  var zoneEl = document.getElementById('colis-zone');
  var mesureEl = document.getElementById('colis-mesure');
  var opEl = document.getElementById('colis-op');
  var KEY = 'scan_colis_' + SITE;
  var colisActif = false, colisNom = '';
  try{ colisActif = parseInt(localStorage.getItem(KEY)) || false; }catch(e){}
  var pending = null, qteStr = '';
  var busy = false;

  // ── utilitaires ──
  function esc(s){ var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }
  function fmtN(n){ return (Math.round(n * 1000) / 1000).toString().replace('.', ','); }
  function classFor(txt){
    if(!txt) return 'idle';
    if(txt.indexOf('✅') === 0 || txt.indexOf('📦') === 0 || txt.indexOf('✂') === 0) return 'ok';
    if(txt.indexOf('ℹ') === 0 || txt.indexOf('↩') === 0 || txt.indexOf('🗑') === 0 || txt.indexOf('📍') === 0 || txt.indexOf('👤') === 0 || txt.indexOf('👉') === 0 || txt.indexOf('⏳') === 0) return 'info';
    if(txt.indexOf('⚠') === 0 || txt.indexOf('🔒') === 0) return 'warn';
    if(txt.indexOf('❌') === 0 || txt.indexOf('⛔') === 0) return 'err';
    return 'idle';
  }
  function beep(good){
    try{
      var c = new (window.AudioContext || window.webkitAudioContext)();
      var o = c.createOscillator(); var g = c.createGain();
      o.connect(g); g.connect(c.destination);
      o.frequency.value = good ? 880 : 220; g.gain.value = 0.12;
      o.start(); setTimeout(function(){ o.stop(); c.close(); }, good ? 110 : 260);
    }catch(e){}
  }
  function setRes(txt){ resEl.textContent = txt; resEl.className = 'scan-res ' + classFor(txt); }

  // ── appel Render (action 2102 : palette active du poste, opérateur déduit de l'OF) ──
  function web(mode, extra){
    var ctx = {colis_id: colisActif || 0, mode: mode};
    if(extra){ for(var k in extra){ if(Object.prototype.hasOwnProperty.call(extra, k)){ ctx[k] = extra[k]; } } }
    return fetch(RENDER, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action_id: 2102, ctx: ctx})})
      .then(function(r){ return r.json(); })
      .then(function(d){ if(d.error){ throw new Error(d.error.message || 'Erreur'); } return d.result || {}; });
  }
  function act(mode, extra){
    if(busy){ setRes('⏳ Patientez, action en cours…'); return Promise.resolve(); }
    busy = true; setRes('⏳ …');
    return web(mode, extra).then(function(r){ busy = false; applyEtat(r); beep(!!r.ok); return r; })
      .catch(function(e){ busy = false; setRes('⚠️ ' + (e && e.message ? e.message : e)); beep(false); });
  }

  // ── rendu de l'état ──
  function metaOf(o){
    var dims = [];
    if(o.x_studio_long_m_1){ dims.push(fmtN(o.x_studio_long_m_1)); }
    if(o.x_studio_larg_m_1){ dims.push(fmtN(o.x_studio_larg_m_1)); }
    if(o.x_studio_haut_m_1){ dims.push(fmtN(o.x_studio_haut_m_1)); }
    var meta = [];
    if(o.x_studio_ref_pierre){ meta.push('◆ ' + esc(o.x_studio_ref_pierre)); }
    if(o.x_studio_nom_du_client){ meta.push(esc(o.x_studio_nom_du_client)); }
    if(o.x_studio_palette){ meta.push('🟪 ' + esc(o.x_studio_palette)); }
    if(dims.length){ meta.push(dims.join(' × ') + ' m'); }
    var out = meta.join(' · ');
    if(o.x_note_atelier){ out += '<div style="background:#854d0e;color:#fef9c3;border-radius:6px;padding:1px 7px;margin-top:2px;display:inline-block;font-weight:800;">💬 ' + esc(o.x_note_atelier) + '</div>'; }
    return out;
  }
  function renderItem(it){
    var cls = it.kind === 'line' ? 'part' : 'whole';
    return '<div class="scan-of-item">'
      + '<div class="of-main"><div class="of-name">🪨 ' + esc(it.name) + '<span class="of-qty ' + cls + '">' + esc(it.label) + '</span></div>'
      + '<div class="of-meta">' + metaOf(it.o || {}) + '</div></div>'
      + '<button class="of-reb" data-ofid="' + it.of_id + '" data-max="' + (it.qte || 1) + '" data-name="' + esc(it.name) + '" title="Déclarer un rebut">💥</button>'
      + '<button class="of-del" data-kind="' + it.kind + '" data-id="' + it.id + '" data-name="' + esc(it.name) + '">🗑️</button>'
      + '</div>';
  }
  function applyEtat(r){
    if(!r || r.palettes){ return; }
    var c = r.colis;
    colisActif = c ? c.id : false; colisNom = c ? c.name : '';
    try{ if(colisActif){ localStorage.setItem(KEY, String(colisActif)); } else { localStorage.removeItem(KEY); } }catch(e){}
    colisEl.textContent = c ? c.name : '—';
    colisEl.className = c ? 'scan-colis-name' : 'scan-colis-none';
    if(opEl){ opEl.textContent = c ? (c.op_nom ? ('👤 Palette de ' + c.op_nom) : '🟡 Palette vierge — au premier opérateur qui y pose') : ''; }
    if(mesureEl){ mesureEl.textContent = c ? ('📦 ' + fmtN(c.cub || 0) + ' m³  ·  ' + fmtN(Math.round((c.ton || 0) / 100) / 10) + ' t  (' + Math.round(c.ton || 0) + ' kg)') : ''; }
    if(zoneEl){ zoneEl.textContent = (c && c.zone) ? ('📍 Emplacement : ' + c.zone) : ''; }
    var box = document.getElementById('of-list'), itemsBox = document.getElementById('of-items');
    if(c){
      document.getElementById('of-count').textContent = (r.items || []).length;
      itemsBox.innerHTML = (r.items || []).map(renderItem).join('') || '<div style="color:#64748b;font-size:14px;">Palette vide — scannez les OF à y poser</div>';
      bindItems(itemsBox);
      box.style.display = '';
    } else { box.style.display = 'none'; itemsBox.innerHTML = ''; }
    if(r.msg){ setRes(r.msg); }
    if(r.demande_qte){ openPop(r.demande_qte); }
    if(r.print_id){ window.open('/report/pdf/maquignon.report_bon_colisage/' + r.print_id, '_blank'); }
  }
  function bindItems(box){
    box.querySelectorAll('.of-del').forEach(function(btn){
      btn.addEventListener('click', function(){
        var kind = btn.getAttribute('data-kind'), id = parseInt(btn.getAttribute('data-id')), nm = btn.getAttribute('data-name');
        if(!confirm((kind === 'line' ? 'Retirer cette répartition de ' : 'Retirer ') + nm + ' de la palette ' + colisNom + ' ?')){ return; }
        (kind === 'line' ? act('retirer_ligne', {line_id: id}) : act('retirer_of', {of_id: id})).then(function(){ input.focus(); });
      });
    });
    box.querySelectorAll('.of-reb').forEach(function(btn){
      btn.addEventListener('click', function(){
        var mx = parseInt(btn.getAttribute('data-max')) || 1, ofid = parseInt(btn.getAttribute('data-ofid'));
        var q = parseInt(prompt('💥 Rebut sur ' + btn.getAttribute('data-name') + '\nNombre de pierres cassées (max ' + mx + ') :', '1')) || 0;
        if(q < 1 || q > mx){ return; }
        var m = prompt('Motif du rebut :', 'Casse mise en palette') || '';
        if(m.replace(/\s/g, '') === ''){ return; }
        fetch(RENDER, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action_id: 1987, ctx: {active_id: ofid, rebut_n: q, rebut_motif: m}})})
          .then(function(r){ return r.json(); })
          .then(function(d){ if(d.error){ throw new Error(d.error.message); } return d.result; })
          .then(function(res){ return act('etat').then(function(){ setRes('💥 Rebut enregistré — OF relancé : ' + ((res && res.new_of) || '')); beep(true); input.focus(); }); })
          .catch(function(e){ alert('Erreur : ' + e.message); });
      });
    });
  }

  // ── pop-up quantité (OF à plusieurs pièces) ──
  var pop = document.getElementById('qte-pop'), popOf = document.getElementById('qte-of'), popMax = document.getElementById('qte-max'), popDisp = document.getElementById('qte-disp');
  function updateDisp(){ if(!pending){ return; } popDisp.textContent = (qteStr === '' ? pending.remaining : qteStr); popDisp.className = (qteStr === '' ? 'qte-disp def' : 'qte-disp'); }
  function openPop(p){
    pending = p; qteStr = '';
    popOf.textContent = p.name;
    var qn = document.getElementById('qte-note');
    if(qn){ qn.textContent = p.note ? ('💬 ' + p.note) : ''; qn.style.display = p.note ? '' : 'none'; }
    var qs = document.getElementById('qte-sub');
    if(qs){ qs.textContent = (p.placed ? (p.placed + ' déjà sur palette · ') : '') + p.remaining + ' disponible(s) sur ' + p.total + ' — tapez le nombre, ou scannez la suite pour tout mettre'; }
    popMax.textContent = p.remaining;
    updateDisp(); pop.style.display = 'flex'; input.focus();
  }
  function closePop(){ pop.style.display = 'none'; pending = null; qteStr = ''; }
  function press(d){
    if(!pending){ return; }
    if(d === 'C'){ qteStr = ''; updateDisp(); return; }
    if(d === 'back'){ qteStr = qteStr.slice(0, -1); updateDisp(); return; }
    var nv = (qteStr + d).replace(/^0+/, ''); if(nv === ''){ nv = '0'; }
    if(parseInt(nv) > pending.remaining){ nv = String(pending.remaining); }
    qteStr = nv; updateDisp();
  }
  function placer(p, qty){
    if(qty < 1){ qty = 1; } if(qty > p.remaining){ qty = p.remaining; }
    return act('placer', {of_id: p.of_id, qte: qty}).then(function(){ input.focus(); });
  }
  function confirmPop(useMax){
    if(!pending){ return; }
    var p = pending, qty = (useMax || qteStr === '') ? p.remaining : parseInt(qteStr);
    closePop(); placer(p, qty);
  }

  // ── entrée principale : douchette, caméra, clavier ──
  function doScan(val){
    input.value = '';
    val = (val || '').trim(); if(!val){ return; }
    if(pending){
      var p = pending; closePop();
      if(/^[0-9]+$/.test(val)){ placer(p, parseInt(val)); return; }
      placer(p, p.remaining).then(function(){ doScan(val); });
      return;
    }
    act('scan', {code: val}).then(function(){ input.focus(); });
  }
  input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); doScan(input.value); } });
  pop.addEventListener('mousedown', function(e){ if(e.target.tagName === 'BUTTON'){ e.preventDefault(); } });
  pop.querySelectorAll('.qte-key').forEach(function(b){ b.addEventListener('click', function(){ press(b.getAttribute('data-k')); input.focus(); }); });
  document.getElementById('qte-ok').addEventListener('click', function(){ confirmPop(false); });
  document.getElementById('qte-all').addEventListener('click', function(){ confirmPop(true); });
  document.getElementById('qte-cancel').addEventListener('click', function(){ closePop(); input.focus(); });
  document.addEventListener('keydown', function(e){
    if(document.activeElement === input){ return; }
    var t = document.activeElement; if(t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')){ return; }
    if(e.key && e.key.length === 1){ input.focus(); }
  });
  document.getElementById('btn-undo').addEventListener('click', function(){
    if(!colisActif){ setRes('⚠️ Aucune palette active'); beep(false); return; }
    if(!confirm('Retirer le dernier OF posé sur ' + colisNom + ' ?')){ return; }
    act('retirer_dernier').then(function(){ input.focus(); });
  });
  document.getElementById('btn-refresh').addEventListener('click', function(){ act('etat').then(function(){ input.focus(); }); });
  document.querySelectorAll('.zone-btn').forEach(function(zb){
    zb.addEventListener('click', function(){
      if(!colisActif){ setRes("⚠️ Scannez d'abord une palette"); beep(false); return; }
      var z = zb.getAttribute('data-zone');
      if(!confirm('Clôturer la palette ' + colisNom + ' → ' + z + ' ?\nElle sera verrouillée et le bon de colisage imprimé.')){ return; }
      act('cloturer', {zone: z}).then(function(){ input.focus(); });
    });
  });
  document.getElementById('btn-colis-print').addEventListener('click', function(){
    if(!colisActif){ setRes('⚠️ Aucune palette active — scannez ou choisissez une palette'); beep(false); return; }
    window.open('/report/pdf/maquignon.report_bon_colisage/' + colisActif, '_blank'); input.focus();
  });

  // ── caméra (tablette) ──
  var camPop = document.getElementById('cam-pop'), camVid = document.getElementById('cam-video'), camMsg = document.getElementById('cam-msg');
  var camStream = null, camTimer = null;
  function camStop(){
    if(camTimer){ clearInterval(camTimer); camTimer = null; }
    if(camStream){ camStream.getTracks().forEach(function(t){ t.stop(); }); camStream = null; }
    if(camVid){ camVid.srcObject = null; }
    if(camPop){ camPop.style.display = 'none'; }
  }
  function camOpen(onCode){
    if(!window.BarcodeDetector){ setRes('⚠️ Scanner caméra non supporté par ce navigateur — utilisez la douchette'); beep(false); return; }
    if(!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)){ setRes('⚠️ Caméra indisponible sur cet appareil'); beep(false); return; }
    camPop.style.display = 'block';
    if(camMsg){ camMsg.textContent = 'Visez le code-barre (palette, OF ou emplacement)…'; }
    navigator.mediaDevices.getUserMedia({audio: false, video: {facingMode: {ideal: 'environment'}, width: {ideal: 1280}, height: {ideal: 720}}}).then(function(st){
      camStream = st; camVid.srcObject = st; return camVid.play();
    }).then(function(){
      var det;
      try{ det = new BarcodeDetector({formats: ['code_128', 'code_39', 'ean_13', 'ean_8', 'itf', 'qr_code']}); }catch(e){ det = new BarcodeDetector(); }
      var b2 = false;
      camTimer = setInterval(function(){
        if(b2 || !camStream || camVid.readyState < 2){ return; }
        b2 = true;
        det.detect(camVid).then(function(codes){
          b2 = false; var v = '';
          for(var ci = 0; ci < codes.length; ci++){ if(codes[ci].rawValue && codes[ci].rawValue.trim()){ v = codes[ci].rawValue.trim(); break; } }
          if(!v){ return; }
          camStop();
          try{ if(navigator.vibrate){ navigator.vibrate(90); } }catch(e){}
          onCode(v);
        }).catch(function(){ b2 = false; });
      }, 220);
    }).catch(function(err){ camStop(); setRes('⚠️ Caméra inaccessible : ' + ((err && err.message) || err) + ' — autorisez la caméra pour ce site'); beep(false); });
  }
  document.getElementById('cam-close').addEventListener('click', function(){ camStop(); input.focus(); });
  document.getElementById('btn-cam').addEventListener('click', function(){ camOpen(function(v){ doScan(v); }); });

  // ── palettes ouvertes ──
  var navPop = document.getElementById('nav-pop'), navList = document.getElementById('nav-list'), navSrch = document.getElementById('nav-srch');
  var navData = {palettes: [], libres: []};
  function navRow(c, libre){
    var cur = (c.id === colisActif);
    return '<button type="button" class="nav-row" data-id="' + c.id + '" style="display:block;width:100%;text-align:left;border:none;border-radius:10px;padding:12px;margin-bottom:6px;font-weight:800;font-size:15px;cursor:pointer;background:' + (cur ? '#075985' : '#1e293b') + ';color:#e2e8f0;">'
      + '<span style="display:flex;justify-content:space-between;gap:8px;"><span>' + (cur ? '▶ ' : '') + esc(c.name) + (libre ? ' <span style="color:#fbbf24;font-size:12px;">sans opérateur</span>' : ' <span style="color:#5eead4;font-size:12px;">👤 ' + esc(c.op) + '</span>') + '</span><span style="color:#93c5fd;font-weight:700;white-space:nowrap;">' + c.n + ' OF · ' + c.cub + ' m³ · ' + c.ton + ' kg</span></span>'
      + (c.m ? '<span style="display:block;color:#94a3b8;font-weight:700;font-size:13px;margin-top:3px;">' + esc(c.m) + '</span>' : '') + '</button>';
  }
  function navRender(){
    var f = (navSrch.value || '').trim().toLowerCase();
    function ok(c){ return !f || (c.name + ' ' + (c.op || '') + ' ' + (c.m || '')).toLowerCase().indexOf(f) !== -1; }
    var pal = navData.palettes.filter(ok), libres = navData.libres.filter(ok);
    var html = '<div style="color:#5eead4;font-weight:800;font-size:13px;margin:2px 0 6px;">🟢 Palettes ouvertes des opérateurs (' + pal.length + ')</div>';
    html += pal.slice(0, 60).map(function(c){ return navRow(c, false); }).join('') || '<div style="color:#64748b;padding:4px 0 10px;font-size:14px;">Aucune palette ouverte — scannez une palette vierge (ou tapez son n°).</div>';
    if(libres.length){
      html += '<div style="color:#fbbf24;font-weight:800;font-size:13px;margin:10px 0 6px;">🟡 Palettes sans opérateur (' + libres.length + ') — au premier opérateur qui y pose</div>';
      html += libres.slice(0, 40).map(function(c){ return navRow(c, true); }).join('');
    }
    navList.innerHTML = html;
    navList.querySelectorAll('.nav-row').forEach(function(b){
      b.addEventListener('click', function(){ navPop.style.display = 'none'; act('choisir', {colis_id_choix: parseInt(b.getAttribute('data-id'))}).then(function(){ input.focus(); }); });
    });
  }
  function openNav(){
    navPop.style.display = 'flex'; navSrch.value = '';
    navList.innerHTML = '<div style="color:#94a3b8;padding:8px;">Chargement…</div>';
    web('liste').then(function(r){ navData = {palettes: r.palettes || [], libres: r.libres || []}; navRender(); setTimeout(function(){ navSrch.focus(); }, 60); })
      .catch(function(e){ navList.innerHTML = '<div style="color:#f87171;padding:8px;">Erreur : ' + esc(e.message) + '</div>'; });
  }
  document.getElementById('btn-colis-nav').addEventListener('click', openNav);
  document.getElementById('nav-cancel').addEventListener('click', function(){ navPop.style.display = 'none'; input.focus(); });
  navSrch.addEventListener('input', navRender);
  navSrch.addEventListener('keydown', function(e){
    if(e.key === 'Enter'){ e.preventDefault(); var v = (navSrch.value || '').trim(); if(v){ navPop.style.display = 'none'; act('choisir', {colis_name: v}).then(function(){ input.focus(); }); } }
  });

  // ── démarrage : palette active du poste (mémorisée), contrôlée côté serveur ──
  act('etat');
  input.focus();
})();
