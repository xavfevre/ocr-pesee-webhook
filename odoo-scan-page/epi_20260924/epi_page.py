# -*- coding: utf-8 -*-
"""Page /epi?k=<clé> (accueil) : remise d'un EPI à un salarié, stock EPI, entrées en stock, dernières remises
(annulables), consommation par salarié. Vue website `website.epi` + website.page.
  python epi_page.py            -> vue_epi_NEW.xml
  python epi_page.py prod       -> création / mise à jour dans Odoo"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')


def esc_js(js):
    return js.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


JS = r'''
(function(){
  var K = document.getElementById('ep-k').getAttribute('data-k');
  var RPC = 'https://ocr-pesee-webhook.onrender.com/heures/rpc';
  function rpc(aid, ctx){
    ctx.epi_k = K; ctx.active_model = 'stock.picking';
    return fetch(RPC, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action_id:aid, ctx:ctx})}).then(function(r){ return r.json(); });
  }
  function flash(msg, ok){
    try { sessionStorage.setItem('epFlash', JSON.stringify({m:msg, ok:ok ? 1 : 0})); } catch(e){}
    location.reload();
  }
  try {
    var f = JSON.parse(sessionStorage.getItem('epFlash') || 'null');
    if(f){ sessionStorage.removeItem('epFlash'); var z = document.getElementById('ep-flash'); z.textContent = f.m; z.className = 'ep-flash ' + (f.ok ? 'ok' : 'err'); z.style.display = ''; setTimeout(function(){ z.style.display = 'none'; }, 6000); }
  } catch(e){}
  function msg(d){ return (d.error && ((d.error.data && d.error.data.message) || d.error.message)) || 'Erreur'; }
  var selP = document.getElementById('ep-prod');
  function majStock(){
    var o = selP.options[selP.selectedIndex]; var s = o ? o.getAttribute('data-stock') : null;
    var z = document.getElementById('ep-stock-info');
    if(!o || !o.value){ z.textContent = ''; return; }
    var n = parseFloat(s || 0);
    z.textContent = 'En stock : ' + n; z.className = 'ep-stock-info ' + (n <= 0 ? 'bad' : (n <= 2 ? 'warn' : 'ok'));
  }
  if(selP){ selP.addEventListener('change', majStock); majStock(); }
  /* code-barres tapé (ou scanné) puis Entrée : sélectionne l'EPI dans la liste ; inconnu = message */
  function scan(inp){
    var code = (inp.value || '').trim(); if(!code){ return; }
    var sel = document.getElementById(inp.getAttribute('data-cible')); var trouve = null;
    for(var i = 0; i < sel.options.length; i++){ var bc = sel.options[i].getAttribute('data-barcode') || ''; if(bc && bc === code){ trouve = sel.options[i]; break; } }
    if(!trouve){ inp.className = 'ep-scan bad'; alert('Code-barres ' + code + ' inconnu.' + String.fromCharCode(10) + 'Vérifiez la saisie, ou enregistrez ce code sur la fiche de l' + String.fromCharCode(39) + 'article dans Odoo (champ Code-barres ; pour un EPI à tailles, sur chaque variante). Sinon choisissez l' + String.fromCharCode(39) + 'EPI dans la liste.'); inp.select(); return; }
    sel.value = trouve.value; inp.className = 'ep-scan ok'; inp.value = trouve.textContent.trim();
    if(sel === selP){ majStock(); var q = document.getElementById('ep-qty'); if(q){ q.focus(); q.select(); } }
    else { var q2 = document.getElementById('ep-rec-qty'); if(q2){ q2.focus(); q2.select(); } }
  }
  document.querySelectorAll('input.ep-scan').forEach(function(inp){
    inp.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); scan(inp); } });
    inp.addEventListener('focus', function(){ inp.value = ''; inp.className = 'ep-scan'; });
  });
  var go = document.getElementById('ep-go');
  function remettre(force){
    var emp = document.getElementById('ep-emp').value, prod = selP.value, qty = document.getElementById('ep-qty').value, date = document.getElementById('ep-date').value, note = document.getElementById('ep-note').value;
    if(!emp){ alert('Choisissez le salarié.'); return; }
    if(!prod){ alert("Choisissez l'EPI."); return; }
    go.disabled = true; go.textContent = '…';
    rpc(2110, {emp:emp, product:prod, qty:qty, date:date, note:note, force:force ? 1 : 0}).then(function(d){
      go.disabled = false; go.textContent = '✅ Remettre';
      if(d.error){
        var m = msg(d);
        if(m.indexOf('STOCK|') === 0){
          if(confirm(m.slice(6) + '\n\nRemettre quand même ?')){ remettre(true); }
          return;
        }
        alert('Échec : ' + m); return;
      }
      var r = d.result || {};
      flash('✓ ' + r.produit + ' × ' + r.qty + ' remis à ' + r.salarie + ' (' + r.ref + ') — reste en stock : ' + r.stock, true);
    }).catch(function(){ go.disabled = false; go.textContent = '✅ Remettre'; alert('Échec réseau'); });
  }
  if(go){ go.addEventListener('click', function(){ remettre(false); }); }
  var rec = document.getElementById('ep-rec-go');
  if(rec){ rec.addEventListener('click', function(){
    var prod = document.getElementById('ep-rec-prod').value, qty = document.getElementById('ep-rec-qty').value, date = document.getElementById('ep-rec-date').value, note = document.getElementById('ep-rec-note').value;
    if(!prod){ alert("Choisissez l'EPI reçu."); return; }
    rec.disabled = true;
    rpc(2111, {product:prod, qty:qty, date:date, note:note}).then(function(d){
      rec.disabled = false;
      if(d.error){ alert('Échec : ' + msg(d)); return; }
      var r = d.result || {};
      flash('✓ Entrée en stock : ' + r.produit + ' × ' + r.qty + ' (' + r.ref + ') — stock : ' + r.stock, true);
    }).catch(function(){ rec.disabled = false; alert('Échec réseau'); });
  }); }
  document.addEventListener('click', function(e){
    var b = e.target.closest('.ep-annule'); if(!b){ return; }
    if(!confirm('Annuler cette remise ? ' + b.getAttribute('data-lib') + '\nL\'EPI revient en stock.')){ return; }
    b.disabled = true;
    rpc(2112, {move:b.getAttribute('data-move')}).then(function(d){
      if(d.error){ b.disabled = false; alert('Échec : ' + msg(d)); return; }
      flash('✓ Remise ' + (d.result || {}).annule + ' annulée, EPI remis en stock.', true);
    }).catch(function(){ b.disabled = false; alert('Échec réseau'); });
  });
  /* stock mini / maxi : enregistrés dès la modification (règle de réapprovisionnement) */
  document.addEventListener('change', function(e){
    var i = e.target; if(!i.classList || !i.classList.contains('ep-mini')){ return; }
    var tr = i.closest('tr[data-prod]'); if(!tr){ return; }
    var mi = tr.querySelector('input[data-f=mini]'), ma = tr.querySelector('input[data-f=maxi]');
    rpc(2113, {product:tr.getAttribute('data-prod'), mini:mi.value, maxi:ma.value}).then(function(d){
      if(d.error){ i.className = 'ep-mini err'; alert('Échec : ' + msg(d)); return; }
      var r = d.result || {};
      mi.value = r.mini ? String(r.mini) : ''; ma.value = r.maxi ? String(r.maxi) : '';
      mi.className = 'ep-mini ok'; ma.className = 'ep-mini ok';
      var q = parseFloat((tr.children[1].textContent || '0').replace(',', '.')) || 0;
      tr.className = (q <= 0 || (r.mini && q < r.mini)) ? 'bad' : ((r.mini && q <= r.mini) ? 'warn' : '');
      setTimeout(function(){ mi.className = 'ep-mini'; ma.className = 'ep-mini'; }, 2000);
    }).catch(function(){ i.className = 'ep-mini err'; alert('Échec réseau'); });
  });
  var dp = document.getElementById('ep-dp-go');
  if(dp){ dp.addEventListener('click', function(){
    dp.disabled = true;
    rpc(2114, {apercu:1}).then(function(d){
      if(d.error){ dp.disabled = false; alert('Échec : ' + msg(d)); return; }
      var r = d.result || {};
      if(!r.nb_epi){ dp.disabled = false; alert('Aucun EPI sous son stock mini : rien à commander.\n(Renseignez les colonnes Mini / Maxi dans le tableau.)'); return; }
      var txt = r.nb_epi + ' EPI sous le mini.\n';
      if(r.fournisseurs.length){ txt += 'Demandes de prix à créer : ' + r.fournisseurs.map(function(f){ return f.nom + ' (' + f.nb + ' EPI)'; }).join(', ') + '.\n'; }
      if(r.sans_fournisseur.length){ txt += 'Sans fournisseur référencé (à compléter sur la fiche article) : ' + r.sans_fournisseur.join(', ') + '.\n'; }
      if(!r.fournisseurs.length){ dp.disabled = false; alert(txt); return; }
      if(!confirm(txt + '\nCréer ces demandes de prix dans Odoo ?')){ dp.disabled = false; return; }
      rpc(2114, {}).then(function(d2){
        if(d2.error){ dp.disabled = false; alert('Échec : ' + msg(d2)); return; }
        var r2 = d2.result || {};
        flash('✓ ' + r2.commandes.map(function(c){ return c.nom + ' — ' + c.fournisseur + ' (' + c.nb + ' EPI' + (c.maj ? ', mise à jour' : '') + ')'; }).join(' · ') + (r2.sans_fournisseur.length ? ' — sans fournisseur : ' + r2.sans_fournisseur.join(', ') : ''), true);
      }).catch(function(){ dp.disabled = false; alert('Échec réseau'); });
    }).catch(function(){ dp.disabled = false; alert('Échec réseau'); });
  }); }
  var filtre = document.getElementById('ep-filtre');
  if(filtre){ filtre.addEventListener('input', function(){
    var v = filtre.value.toLowerCase();
    document.querySelectorAll('tr[data-emp-nom]').forEach(function(tr){ tr.style.display = (!v || tr.getAttribute('data-emp-nom').indexOf(v) >= 0) ? '' : 'none'; });
  }); }
})();
'''

ARCH = r'''<t t-name="website.epi">
  <t t-call="website.layout">
    <style>
      header#top, header.o_header_standard, footer, .o_footer, #o_cookies_bar, .o_bottom_fixed_element {display:none !important;}
      #wrapwrap &gt; main {padding-top:0 !important;}
      body{background:#f1f5f9;}
      .ep-wrap{max-width:1180px;margin:0 auto;padding:12px 16px;}
      .ep-brand{background:#fff;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:12px 16px;display:flex;align-items:center;gap:14px;margin-bottom:10px;flex-wrap:wrap;}
      .ep-brand img{height:48px;max-width:160px;object-fit:contain;}
      .ep-brand .t{font-size:22px;font-weight:900;color:#0f172a;}
      .ep-brand .s{font-size:12.5px;color:#64748b;font-weight:600;}
      .ep-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:14px;align-items:start;}
      @media (max-width: 900px){ .ep-grid{grid-template-columns:1fr;} }
      .ep-card{background:#fff;border-radius:14px;box-shadow:0 1px 4px rgba(0,0,0,.08);padding:14px 16px;margin-bottom:14px;}
      .ep-card h5{font-weight:900;font-size:17px;margin:0 0 10px;}
      .ep-form{display:grid;grid-template-columns:auto minmax(0,1fr);gap:8px 12px;align-items:center;}
      .ep-form label{font-weight:800;color:#475569;font-size:13px;}
      .ep-form select, .ep-form input{border:1.5px solid #cbd5e1;border-radius:9px;padding:8px 10px;font-weight:700;font-size:15px;width:100%;box-sizing:border-box;background:#fff;}
      .ep-btn{border:none;border-radius:11px;padding:12px;font-weight:900;font-size:16px;cursor:pointer;width:100%;margin-top:10px;}
      .ep-btn.go{background:#16a34a;color:#fff;}
      .ep-btn.rec{background:#1d4ed8;color:#fff;font-size:14px;padding:9px;}
      .ep-btn:disabled{opacity:.5;}
      .ep-stock-info{font-weight:900;font-size:13px;margin-top:4px;}
      .ep td input.ep-mini{width:58px;border:1.5px solid #cbd5e1;border-radius:7px;padding:3px 4px;font-weight:800;text-align:center;font-size:13px;background:#fff;}
      .ep td input.ep-mini.ok{border-color:#16a34a;background:#dcfce7;}
      .ep td input.ep-mini.err{border-color:#dc2626;background:#fee2e2;}
      .ep-form input.ep-scan{border-color:#0f172a;background:#f8fafc;}
      .ep-form input.ep-scan.ok{border-color:#16a34a;background:#dcfce7;}
      .ep-form input.ep-scan.bad{border-color:#dc2626;background:#fee2e2;}
      .ep-stock-info.ok{color:#15803d;} .ep-stock-info.warn{color:#b45309;} .ep-stock-info.bad{color:#b91c1c;}
      .ep-flash{border-radius:12px;padding:10px 14px;font-weight:900;margin-bottom:12px;}
      .ep-flash.ok{background:#dcfce7;color:#166534;} .ep-flash.err{background:#fee2e2;color:#991b1b;}
      table.ep{width:100%;border-collapse:collapse;font-size:13.5px;}
      .ep th{background:#0f172a;color:#e2e8f0;padding:6px 8px;text-align:left;font-size:12px;}
      .ep td{padding:6px 8px;border-bottom:1px solid #e2e8f0;font-weight:700;}
      .ep td.n, .ep th.n{text-align:right;}
      .ep tr.bad td{background:#fee2e2;} .ep tr.warn td{background:#fef3c7;}
      .ep tr.annul td{color:#94a3b8;text-decoration:line-through;}
      .ep-annule{border:none;border-radius:8px;background:#fee2e2;color:#991b1b;font-weight:800;padding:4px 8px;cursor:pointer;font-size:12px;}
      .ep-help{color:#64748b;font-size:12.5px;font-weight:600;line-height:1.45;}
      .ep-tag{display:inline-block;border-radius:7px;padding:1px 7px;font-size:11.5px;font-weight:800;background:#e2e8f0;color:#334155;margin:1px 2px;}
      #ep-filtre{border:1.5px solid #cbd5e1;border-radius:9px;padding:6px 10px;font-weight:700;width:100%;box-sizing:border-box;margin-bottom:8px;}
    </style>
    <div class="ep-wrap">
      <t t-set="kk" t-value="(request.params.get('k') or '').strip()"/>
      <t t-set="kref" t-value="request.env['ir.config_parameter'].sudo().get_param('maquignon.epi_key') or ''"/>
      <t t-if="not (kk and kref and kk == kref)">
        <div style="background:#fff;border-radius:14px;padding:26px;text-align:center;margin-top:40px;">
          <div style="font-size:44px;">🔒</div>
          <h4 style="font-weight:800;">Accès réservé</h4>
          <div style="color:#64748b;">Cette page s'ouvre uniquement avec le lien complet fourni par le bureau.</div>
        </div>
      </t>
      <t t-else="">
        <t t-set="P" t-value="request.env['ir.config_parameter'].sudo()"/>
        <t t-set="categ" t-value="int(P.get_param('maquignon.epi_categ') or 0)"/>
        <t t-set="loc_stock" t-value="int(P.get_param('maquignon.epi_loc_stock') or 0)"/>
        <t t-set="loc_conso" t-value="int(P.get_param('maquignon.epi_loc_conso') or 0)"/>
        <t t-set="today" t-value="datetime.date.today()"/>
        <t t-set="annee" t-value="request.params.get('annee') or str(today.year)"/>
        <t t-set="prods" t-value="request.env['product.product'].sudo().search([('categ_id','child_of',categ),('active','=',True)], order='product_tmpl_id, id')"/>
        <t t-set="quants" t-value="request.env['stock.quant'].sudo().search([('location_id','=',loc_stock)])"/>
        <t t-set="stock" t-value="{}"/>
        <t t-set="_q" t-value="[stock.update({q.product_id.id: stock.get(q.product_id.id, 0.0) + q.quantity}) for q in quants]"/>
        <t t-set="emps" t-value="request.env['hr.employee'].sudo().search([('active','=',True)], order='company_id, name')"/>
        <t t-set="regles" t-value="dict((o.product_id.id, o) for o in request.env['stock.warehouse.orderpoint'].sudo().search([('location_id','=',loc_stock)]))"/>
        <t t-set="fourn" t-value="{}"/>
        <t t-set="_f" t-value="[fourn.setdefault(si.product_tmpl_id.id, []).append(si.partner_id.name) for si in request.env['product.supplierinfo'].sudo().search([('product_tmpl_id','in',prods.mapped('product_tmpl_id').ids),'|',('company_id','=',False),('company_id','=',1)], order='sequence, id') if si.partner_id.name not in fourn.get(si.product_tmpl_id.id, [])]"/>
        <t t-set="dps" t-value="request.env['purchase.order'].sudo().search([('origin','=','EPI stock mini'),('state','in',['draft','sent','to approve','purchase'])], order='id desc', limit=12)"/>
        <t t-set="etat_dp" t-value="{'draft': 'brouillon', 'sent': 'envoyée', 'to approve': 'à approuver', 'purchase': 'commandée'}"/>
        <t t-set="mvs" t-value="request.env['stock.move'].sudo().search([('state','=','done'),('product_id.active','=',True),'|',('location_dest_id','=',loc_conso),('location_id','=',loc_conso)], order='date desc, id desc', limit=60)"/>
        <t t-set="annules" t-value="set([r.origin.replace('Annulation ', '') for r in request.env['stock.picking'].sudo().search([('origin','like','Annulation EPI'),('state','=','done')])])"/>
        <t t-set="mvs_an" t-value="request.env['stock.move'].sudo().search([('state','=','done'),('product_id.active','=',True),('x_employee_id','!=',False),('date','&gt;=',annee + '-01-01'),('date','&lt;=',annee + '-12-31 23:59:59'),'|',('location_dest_id','=',loc_conso),('location_id','=',loc_conso)])"/>
        <t t-set="conso" t-value="{}"/>
        <t t-set="_c" t-value="[conso.setdefault(r.x_employee_id, {}).update({r.product_id: conso.get(r.x_employee_id, {}).get(r.product_id, 0.0) + (r.quantity if r.location_dest_id.id == loc_conso else -r.quantity)}) for r in mvs_an]"/>
        <div class="ep-brand">
          <img src="/web/image/res.company/1/logo" alt="Maquignon"/>
          <div><div class="t">🦺 EPI — remise et stock</div><div class="s">Accueil · équipements de protection individuelle · remise aux salariés et suivi du stock</div></div>
        </div>
        <div id="ep-flash" class="ep-flash" style="display:none;"></div>
        <div class="ep-grid">
          <div>
            <div class="ep-card">
              <h5>✅ Remettre un EPI à un salarié</h5>
              <div class="ep-form">
                <label for="ep-emp">Salarié</label>
                <select id="ep-emp">
                  <option value="">— choisir —</option>
                  <t t-foreach="emps.mapped('company_id')" t-as="co">
                    <optgroup t-att-label="co.name">
                      <t t-foreach="emps.filtered(lambda e0: e0.company_id.id == co.id)" t-as="e0"><option t-att-value="e0.id" t-esc="e0.name"/></t>
                    </optgroup>
                  </t>
                </select>
                <label for="ep-scan">Code-barres</label>
                <input type="text" id="ep-scan" class="ep-scan" data-cible="ep-prod" placeholder="tapez le code-barres de l'EPI puis Entrée (ou choisissez-le ci-dessous)" autocomplete="off" inputmode="numeric"/>
                <label for="ep-prod">EPI</label>
                <div>
                  <select id="ep-prod">
                    <option value="">— choisir —</option>
                    <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id" t-att-data-stock="'%g' % stock.get(pr.id, 0.0)" t-att-data-barcode="pr.barcode or ''"><t t-esc="pr.display_name"/> — stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/></option></t>
                  </select>
                  <div id="ep-stock-info" class="ep-stock-info"></div>
                </div>
                <label for="ep-qty">Quantité</label>
                <input type="number" id="ep-qty" value="1" min="1" max="200" step="1"/>
                <label for="ep-date">Date</label>
                <input type="date" id="ep-date" t-att-value="today.strftime('%Y-%m-%d')" t-att-max="today.strftime('%Y-%m-%d')"/>
                <label for="ep-note">Note</label>
                <input type="text" id="ep-note" placeholder="facultatif (remplacement, taille…)"/>
              </div>
              <button type="button" id="ep-go" class="ep-btn go">✅ Remettre</button>
              <div class="ep-help" style="margin-top:8px;">La remise sort l'EPI du stock et l'inscrit sur la fiche du salarié (onglet EPI dans Odoo). Une erreur ? Annulez la remise dans la liste ci-contre, l'EPI revient en stock.</div>
            </div>
            <div class="ep-card">
              <h5>📦 Entrée en stock (EPI reçus)</h5>
              <div class="ep-form">
                <label for="ep-rec-scan">Code-barres</label>
                <input type="text" id="ep-rec-scan" class="ep-scan" data-cible="ep-rec-prod" placeholder="tapez le code-barres de l'EPI reçu puis Entrée" autocomplete="off" inputmode="numeric"/>
                <label for="ep-rec-prod">EPI</label>
                <select id="ep-rec-prod">
                  <option value="">— choisir —</option>
                  <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id" t-att-data-barcode="pr.barcode or ''"><t t-esc="pr.display_name"/> (stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/>)</option></t>
                </select>
                <label for="ep-rec-qty">Quantité</label>
                <input type="number" id="ep-rec-qty" value="1" min="1" max="200" step="1"/>
                <label for="ep-rec-date">Date</label>
                <input type="date" id="ep-rec-date" t-att-value="today.strftime('%Y-%m-%d')" t-att-max="today.strftime('%Y-%m-%d')"/>
                <label for="ep-rec-note">Note</label>
                <input type="text" id="ep-rec-note" placeholder="fournisseur, n° de BL… (facultatif)"/>
              </div>
              <button type="button" id="ep-rec-go" class="ep-btn rec">📦 Entrer en stock</button>
              <div class="ep-help" style="margin-top:8px;">Nouvel EPI à suivre ? Dans Odoo, créer l'article dans la catégorie <b>EPI</b> avec « Suivre l'inventaire » coché et son code-barres tapé dans le champ Code-barres (tailles en variantes : un code par taille). Il apparaît ici aussitôt.</div>
            </div>
          </div>
          <div>
            <div class="ep-card">
              <h5>📊 Stock EPI</h5>
              <table class="ep">
                <tr><th>EPI</th><th class="n">En stock</th><th class="n" title="Stock mini : en dessous, l'EPI est à commander">Mini</th><th class="n" title="Quantité à atteindre lors de la commande">Maxi</th><th class="n">Prix</th><th>Fournisseurs</th></tr>
                <t t-foreach="prods" t-as="pr">
                  <t t-set="q" t-value="stock.get(pr.id, 0.0)"/>
                  <t t-set="rg" t-value="regles.get(pr.id)"/>
                  <t t-set="mini" t-value="rg.product_min_qty if rg else 0.0"/>
                  <tr t-att-data-prod="pr.id" t-attf-class="{{'bad' if (q &lt;= 0 or (mini and q &lt; mini)) else ('warn' if (mini and q &lt;= mini) else '')}}">
                    <td t-esc="pr.display_name"/>
                    <td class="n"><t t-esc="'%g' % q"/></td>
                    <td class="n"><input type="number" class="ep-mini" data-f="mini" min="0" max="999" step="1" t-att-value="('%g' % mini) if mini else ''" placeholder="–"/></td>
                    <td class="n"><input type="number" class="ep-mini" data-f="maxi" min="0" max="999" step="1" t-att-value="('%g' % rg.product_max_qty) if (rg and rg.product_max_qty) else ''" placeholder="–"/></td>
                    <td class="n" style="color:#64748b;font-weight:600;"><t t-esc="('%.2f' % pr.standard_price).replace('.', ',')"/> €</td>
                    <td style="font-weight:600;color:#475569;font-size:12px;"><t t-esc="', '.join(fourn.get(pr.product_tmpl_id.id, []))"/><span t-if="not fourn.get(pr.product_tmpl_id.id)" style="color:#b45309;" title="Aucun fournisseur sur la fiche article (onglet Achats) : pas de demande de prix possible">aucun</span></td>
                  </tr>
                </t>
                <tr t-if="not prods"><td colspan="6" style="color:#94a3b8;">Aucun article dans la catégorie EPI.</td></tr>
              </table>
              <div class="ep-help" style="margin-top:6px;">Rouge = rupture ou sous le mini, orange = au mini. <b>Mini / Maxi</b> se saisissent ici (enregistrés aussitôt). Valeur du stock : <b><t t-esc="('%.2f' % sum([stock.get(pr.id, 0.0) * pr.standard_price for pr in prods])).replace('.', ',')"/> €</b>.</div>
              <button type="button" id="ep-dp-go" class="ep-btn rec" style="margin-top:10px;">🛒 Demandes de prix aux fournisseurs (EPI sous le mini)</button>
              <div class="ep-help" style="margin-top:6px;">Crée dans Odoo une demande de prix (brouillon) par fournisseur référencé sur l'article, pour la quantité qui ramène le stock au maxi. Le bureau l'envoie depuis Odoo (Achats → Demandes de prix). Réception dans Odoo = entrée dans Stock EPI.</div>
              <table class="ep" style="margin-top:8px;" t-if="dps">
                <tr><th>Demande de prix</th><th>Fournisseur</th><th>État</th><th class="n">Montant</th><th>Date</th></tr>
                <t t-foreach="dps" t-as="dp">
                  <tr>
                    <td><a t-attf-href="/odoo/action-purchase.purchase_rfq/{{dp.id}}" target="_blank" style="font-weight:800;color:#1d4ed8;text-decoration:none;" t-esc="dp.name"/></td>
                    <td t-esc="dp.partner_id.name"/>
                    <td><span class="ep-tag" t-esc="etat_dp.get(dp.state, dp.state)"/></td>
                    <td class="n"><t t-esc="('%.2f' % dp.amount_total).replace('.', ',')"/> €</td>
                    <td style="color:#64748b;font-weight:600;" t-esc="dp.date_order.strftime('%d/%m/%Y')"/>
                  </tr>
                </t>
              </table>
            </div>
            <div class="ep-card">
              <h5>🕒 Dernières remises</h5>
              <table class="ep">
                <tr><th>Date</th><th>Salarié</th><th>EPI</th><th class="n">Qté</th><th/></tr>
                <t t-foreach="mvs" t-as="mv">
                  <t t-set="sortie" t-value="mv.location_dest_id.id == loc_conso"/>
                  <tr t-attf-class="{{'annul' if (sortie and mv.reference in annules) else ''}}">
                    <td t-esc="mv.date.strftime('%d/%m/%Y')"/>
                    <td t-esc="mv.x_employee_id.name or '—'"/>
                    <td><t t-esc="mv.product_id.display_name"/><t t-if="not sortie"> <span class="ep-tag">↩ retour en stock</span></t><t t-if="mv.picking_id.note"> <span class="ep-tag" t-esc="mv.picking_id.note"/></t></td>
                    <td class="n" t-esc="'%g' % mv.quantity"/>
                    <td><button t-if="sortie and mv.reference not in annules" type="button" class="ep-annule" t-att-data-move="mv.id" t-attf-data-lib="{{mv.product_id.display_name}} × {{'%g' % mv.quantity}} — {{mv.x_employee_id.name or ''}}">↩ annuler</button><span t-elif="sortie" style="color:#94a3b8;font-size:11px;font-weight:800;">annulée</span></td>
                  </tr>
                </t>
                <tr t-if="not mvs"><td colspan="5" style="color:#94a3b8;">Aucune remise enregistrée.</td></tr>
              </table>
            </div>
          </div>
        </div>
        <div class="ep-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px;">
            <h5 style="margin:0;">👤 Consommation par salarié — <t t-esc="annee"/></h5>
            <div>
              <a t-attf-href="/epi?k={{kk}}&amp;annee={{int(annee) - 1}}" style="border:1px solid #cbd5e1;border-radius:9px;padding:5px 10px;font-weight:800;text-decoration:none;color:#0f172a;background:#fff;">◀ <t t-esc="int(annee) - 1"/></a>
              <a t-attf-href="/epi?k={{kk}}&amp;annee={{int(annee) + 1}}" style="border:1px solid #cbd5e1;border-radius:9px;padding:5px 10px;font-weight:800;text-decoration:none;color:#0f172a;background:#fff;"><t t-esc="int(annee) + 1"/> ▶</a>
            </div>
          </div>
          <input type="text" id="ep-filtre" placeholder="filtrer par nom de salarié…"/>
          <table class="ep">
            <tr><th>Salarié</th><th>Société</th><th>EPI reçus</th><th class="n">Total</th><th class="n">Coût</th></tr>
            <t t-foreach="sorted(conso.keys(), key=lambda e0: (e0.company_id.name or '', e0.name or ''))" t-as="e0">
              <t t-set="det" t-value="conso[e0]"/>
              <tr t-att-data-emp-nom="(e0.name or '').lower()">
                <td t-esc="e0.name"/>
                <td style="color:#64748b;font-weight:600;" t-esc="e0.company_id.name"/>
                <td><t t-foreach="sorted(det.keys(), key=lambda p0: p0.display_name)" t-as="p0"><span t-if="det[p0]" class="ep-tag"><t t-esc="p0.display_name"/> × <t t-esc="'%g' % det[p0]"/></span></t></td>
                <td class="n" t-esc="'%g' % sum(det.values())"/>
                <td class="n" style="color:#64748b;font-weight:600;"><t t-esc="('%.2f' % sum([det[p0] * p0.standard_price for p0 in det])).replace('.', ',')"/> €</td>
              </tr>
            </t>
            <tr t-if="not conso"><td colspan="5" style="color:#94a3b8;">Aucune remise en <t t-esc="annee"/>.</td></tr>
          </table>
          <div class="ep-help" style="margin-top:6px;">Dans Odoo : fiche salarié → onglet <b>EPI</b> ; Inventaire → Analyse des mouvements, grouper par <b>Salarié</b> ; transferts « Dotation EPI » et « Réception EPI ».</div>
        </div>
        <div id="ep-k" t-att-data-k="kk" style="display:none;"/>
        <script>__JS__</script>
      </t>
    </div>
  </t>
</t>'''
ARCH = ARCH.replace('__JS__', esc_js(JS))
import xml.dom.minidom
xml.dom.minidom.parseString(ARCH.encode('utf-8'))
io.open('vue_epi_NEW.xml', 'w', encoding='utf-8', newline='\n').write(ARCH)
print('vue_epi_NEW.xml :', len(ARCH), 'chars, XML OK')

mode = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
if mode == 'prod':
    import ssl, xmlrpc.client
    U, D = 'https://maquignon.odoo.com', 'maquignon'
    us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
    ids = x('ir.ui.view', 'search', [['key', '=', 'website.epi']])
    if ids:
        x('ir.ui.view', 'write', ids, {'arch_db': ARCH}); vid = ids[0]; print('vue mise à jour', vid)
    else:
        vid = x('ir.ui.view', 'create', [{'name': 'EPI — remise et stock', 'key': 'website.epi', 'type': 'qweb', 'arch_db': ARCH}])
        vid = vid[0] if isinstance(vid, list) else vid; print('vue créée', vid)
    pg = x('website.page', 'search', [['url', '=', '/epi']])
    if pg:
        x('website.page', 'write', pg, {'view_id': vid, 'is_published': True}); print('page existante', pg)
    else:
        print('page créée', x('website.page', 'create', [{'name': 'EPI — remise et stock', 'url': '/epi', 'view_id': vid, 'is_published': True, 'website_id': False}]))
