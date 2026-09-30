# -*- coding: utf-8 -*-
"""Page « Tranches » (/planning-tranches) pour l'opérateur du sciage primaire : pièces dont le sciage secondaire est
planifié dans les N prochains jours, regroupées par matière puis par épaisseur de tranche retenue (H par défaut,
changeable pièce par pièce ; le choix est ENREGISTRÉ SUR L'OF, champ x_epaisseur_tranche, donc partagé entre tous les écrans),
avec le nombre de pièces et les m² de tranche à débiter. Rafraîchissement automatique toutes les 3 minutes.
  python tranches_page.py dry    -> boards/tranches.xml + contrôle XML (lecture seule)
  python tranches_page.py apply  -> crée ou met à jour la vue website.planning_tranches et la page /planning-tranches"""
import html, io, os, ssl, sys, xmlrpc.client
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()

JS = r"""
(function () {
  function f3(v) { return (Math.round(v * 1000) / 1000).toFixed(3); }
  function f1(v) { return (Math.round(v * 100) / 100).toFixed(2).replace('.', ','); }
  function meme(a, b) { return Math.abs(a - b) < 0.0000005; }
  function rpcWrite(ids, vals, cb) {
    fetch('/web/dataset/call_kw', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { model: 'mrp.production', method: 'write', args: [ids, vals], kwargs: {} } })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.error) { cb(false, d.error.data && d.error.data.message || d.error.message); } else { cb(true); }
    }).catch(function (e) { cb(false, String(e)); });
  }
  function toast(txt, ko) {
    var t = document.createElement('div');
    t.textContent = txt;
    t.style.cssText = 'position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:' + (ko ? '#b91c1c' : '#2d6a6f') + ';color:#fff;padding:8px 16px;border-radius:8px;z-index:999;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.3);';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 3500);
  }
  function dimsOf(tr) {
    return [parseFloat(tr.getAttribute('data-l')) || 0, parseFloat(tr.getAttribute('data-w')) || 0, parseFloat(tr.getAttribute('data-h')) || 0];
  }
  function choix(tr) {
    var d = dimsOf(tr), c = parseFloat(tr.getAttribute('data-ep')) || 0;
    if (c) { for (var i = 0; i < d.length; i++) { if (d[i] && meme(d[i], c)) { return d[i]; } } }
    return d[2] || d[1] || d[0];
  }
  function render() {
    document.querySelectorAll('.tr-mat').forEach(function (sec) {
      var tb = sec.querySelector('table.tr-pieces tbody');
      var rows = Array.prototype.slice.call(tb.querySelectorAll('tr.tr-piece'));
      tb.querySelectorAll('tr.tr-grp').forEach(function (g) { g.remove(); });
      var groupes = {};
      rows.forEach(function (tr) {
        var d = dimsOf(tr), e = choix(tr), nb = parseInt(tr.getAttribute('data-nb')) || 1;
        var vol = d[0] * d[1] * d[2] * nb, m2 = e ? vol / e : 0;
        var cell = tr.querySelector('td.tr-ep'); cell.innerHTML = '';
        var vus = [];
        d.forEach(function (v) {
          if (!v) { return; }
          for (var k = 0; k < vus.length; k++) { if (meme(vus[k], v)) { return; } }
          vus.push(v);
          var b = document.createElement('button'); b.type = 'button';
          b.className = 'ep-btn' + (meme(v, e) ? ' on' : ''); b.textContent = f3(v);
          b.title = meme(v, e) ? 'Épaisseur retenue' : 'Retenir cette cote comme épaisseur de tranche (enregistré sur l’OF, visible sur tous les écrans)';
          b.addEventListener('click', function () {
            if (meme(v, e)) { return; }
            var ofId = parseInt(tr.getAttribute('data-of'));
            b.disabled = true;
            rpcWrite([ofId], { x_epaisseur_tranche: v }, function (ok, msg) {
              if (!ok) { b.disabled = false; toast('Échec de l’enregistrement : ' + msg, true); return; }
              tr.setAttribute('data-ep', String(v));
              render();
              toast(tr.getAttribute('data-name') + ' : épaisseur ' + f3(v) + ' m enregistrée');
            });
          });
          cell.appendChild(b);
        });
        if (parseFloat(tr.getAttribute('data-ep')) > 0) { var m_ = document.createElement('span'); m_.textContent = '✎'; m_.title = 'Choix enregistré sur l’OF'; m_.style.cssText = 'color:#0f766e;font-size:12px;margin-left:2px;'; cell.appendChild(m_); }
        var k2 = f3(e);
        if (!groupes[k2]) { groupes[k2] = { nb: 0, m2: 0, vol: 0, rows: [] }; }
        groupes[k2].nb += nb; groupes[k2].m2 += m2; groupes[k2].vol += vol; groupes[k2].rows.push(tr);
      });
      var cles = Object.keys(groupes).sort(function (a, b) { return parseFloat(b) - parseFloat(a); });
      var totNb = 0, totM2 = 0, totVol = 0;
      var res = sec.querySelector('table.tr-res tbody'); res.innerHTML = '';
      cles.forEach(function (k) {
        var g = groupes[k]; totNb += g.nb; totM2 += g.m2; totVol += g.vol;
        var trg = document.createElement('tr'); trg.className = 'tr-grp';
        var td = document.createElement('td'); td.setAttribute('colspan', '9');
        td.textContent = 'Épaisseur ' + k + ' m  —  ' + g.nb + ' pièce(s)  —  ' + f1(g.m2) + ' m² de tranche  —  ' + f3(g.vol) + ' m³';
        trg.appendChild(td); tb.appendChild(trg);
        g.rows.sort(function (a, b) { return (a.getAttribute('data-date') || '').localeCompare(b.getAttribute('data-date') || ''); });
        g.rows.forEach(function (tr) { tb.appendChild(tr); });
        var r = document.createElement('tr');
        r.innerHTML = '<td><b>' + k + ' m</b></td><td class="n">' + g.nb + '</td><td class="n">' + f1(g.m2) + '</td><td class="n">' + f3(g.vol) + '</td>';
        res.appendChild(r);
      });
      var tot = document.createElement('tr');
      tot.innerHTML = '<td><b>Total</b></td><td class="n"><b>' + totNb + '</b></td><td class="n"><b>' + f1(totM2) + '</b></td><td class="n"><b>' + f3(totVol) + '</b></td>';
      res.appendChild(tot);
      var nbEl = sec.querySelector('.tr-nb-of'), m2El = sec.querySelector('.tr-m2');
      if (nbEl) { nbEl.textContent = totNb; }
      if (m2El) { m2El.textContent = f1(totM2); }
    });
  }
  var rz = document.getElementById('tr-reset');
  if (rz) {
    rz.addEventListener('click', function () {
      var rows = Array.prototype.slice.call(document.querySelectorAll('tr.tr-piece')).filter(function (tr) { return parseFloat(tr.getAttribute('data-ep')) > 0; });
      if (!rows.length) { toast('Aucun choix enregistré sur les pièces affichées.'); return; }
      if (!confirm('Remettre la hauteur H comme épaisseur sur les ' + rows.length + ' pièce(s) affichée(s) ayant un choix enregistré ? Cela s’applique à tous les écrans.')) { return; }
      rpcWrite(rows.map(function (tr) { return parseInt(tr.getAttribute('data-of')); }), { x_epaisseur_tranche: 0 }, function (ok, msg) {
        if (!ok) { toast('Échec : ' + msg, true); return; }
        rows.forEach(function (tr) { tr.setAttribute('data-ep', '0'); });
        render(); toast(rows.length + ' pièce(s) remise(s) en H');
      });
    });
  }
  var pr = document.getElementById('tr-print');
  if (pr) { pr.addEventListener('click', function () { window.print(); }); }
  render();
  setTimeout(function () { window.location.reload(); }, 180000);
})();
"""

ARCH = """<t t-name="website.planning_tranches">
  <t t-call="website.layout">
    <div id="wrap" class="oe_structure">
      <section class="container-fluid px-3 py-3">

    <t t-set="colors" t-value="{'TUFFEAU': '#5B8DEF', 'HAIMS': '#4CAF50', 'MIGNE': '#E0973F', 'RICHEMONT': '#3BC9B5', 'TERVOUX': '#D946C8', 'SIREUIL': '#F2D63B'}"/>
    <style>
      header#top, header.o_header_standard, footer, .o_footer, #o_cookies_bar, .o_bottom_fixed_element, .o_header_sales_one {display:none !important;}
      #wrapwrap &gt; main {padding-top:0 !important;}
      #wrap {padding-top:0 !important; margin-top:0 !important;}
      .tr-mat{border-radius:10px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;background:#fff;}
      .tr-head{padding:8px 14px;font-weight:800;font-size:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;}
      .tr-head small{font-weight:600;font-size:13px;opacity:.95;}
      .tr-body{display:flex;gap:14px;padding:12px 14px;flex-wrap:wrap;}
      .tr-resume{flex:0 0 330px;min-width:280px;}
      .tr-liste{flex:1 1 640px;min-width:0;overflow:auto;}
      table.tr{width:100%;border-collapse:collapse;font-size:13px;}
      table.tr th{background:#f1f5f9;font-weight:800;padding:5px 7px;text-align:left;white-space:nowrap;font-size:12px;color:#334155;}
      table.tr td{padding:4px 7px;border-top:1px solid #e2e8f0;vertical-align:middle;white-space:nowrap;}
      table.tr td.n, table.tr th.n{text-align:right;}
      tr.tr-grp td{background:#fef3c7;font-weight:800;font-size:13px;border-top:2px solid #f59e0b;}
      .ep-btn{border:1.5px solid #cbd5e1;background:#fff;border-radius:6px;padding:1px 7px;font-weight:700;font-size:12px;margin-right:3px;cursor:pointer;color:#334155;}
      .ep-btn.on{background:#0f172a;color:#fff;border-color:#0f172a;}
      .ep-btn:disabled{opacity:.5;}
      @media print { .nav-tabs, .tr-outils, .ep-btn:not(.on) {display:none !important;} .tr-mat{box-shadow:none;border:1px solid #999;page-break-inside:avoid;} }
    </style>

        <t t-set="tp" t-value="(request.httprequest.args.get('tp') or '').strip().upper()"/>
        <t t-set="days" t-value="int(request.httprequest.args.get('days') or 14)"/>
        <t t-set="today" t-value="datetime.date.today()"/>
        <t t-set="fin" t-value="today + datetime.timedelta(days=days)"/>
        <t t-set="matfn" t-value="lambda w: ((w.production_id.x_studio_catgorie and len((w.production_id.x_studio_catgorie.display_name or '').split('/')) &gt; 1) and w.production_id.x_studio_catgorie.display_name.split('/')[1].strip().upper() or 'AUTRE')"/>
        <t t-set="ots" t-value="website.env['mrp.workorder'].sudo().search([('state','not in',['done','cancel']),('production_id.state','in',['confirmed','progress','to_close']),('production_id.company_id','=',1),('name','ilike','secondaire'),('date_start','&gt;=',today.strftime('%Y-%m-%d 00:00:00')),('date_start','&lt;',fin.strftime('%Y-%m-%d 00:00:00'))], order='date_start, id')"/>
        <t t-set="matcol" t-value="dict((matfn(w), ((w.production_id.x_studio_catgorie and w.production_id.x_studio_catgorie.x_studio_couleur_hex) or colors.get(matfn(w), '#9AA0A6'))) for w in ots)"/>
        <t t-set="mats" t-value="sorted(matcol, key=lambda k: (k == 'AUTRE', k))"/>
        <t t-set="ots" t-value="ots.filtered(lambda w: matfn(w) == tp) if tp else ots"/>
        <t t-set="premier" t-value="{}"/>
        <t t-set="_x" t-value="[premier.setdefault(w.production_id.id, w) for w in ots]"/>
        <t t-set="ofs" t-value="ots.mapped('production_id')"/>

        <ul class="nav nav-tabs mb-2 flex-nowrap overflow-auto" style="font-size:15px;white-space:nowrap;">
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=complet&amp;tp={{tp}}">🏭 Board complet</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=atelier&amp;tp={{tp}}">📍 Board Atelier</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=usine&amp;tp={{tp}}">🏗️ Board Usine</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=primaire&amp;tp={{tp}}">🪨 Board Primaire</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=carriere&amp;tp={{tp}}">🏔 Board Carrière</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=finition&amp;tp={{tp}}">✨ Board Finition</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-machines?board=autres&amp;tp={{tp}}">🛠 Autres postes</a></li>
          <li class="nav-item"><a class="nav-link active fw-bold" href="#">🪚 Tranches</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-operateurs?tp={{tp}}">👷 Vue opérateurs</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-fabrication?tp={{tp}}">📅 Vue semaine</a></li>
          <li class="nav-item"><a class="nav-link" t-attf-href="/planning-mois?tp={{tp}}">📆 Vue mois</a></li>
        </ul>
        <div class="d-flex align-items-center mb-2 flex-wrap gap-3 tr-outils">
          <h3 class="mb-0">Tranches à débiter — sciage secondaire planifié du <t t-esc="today.strftime('%d/%m')"/> au <t t-esc="(fin - datetime.timedelta(days=1)).strftime('%d/%m/%Y')"/></h3>
          <div class="d-flex gap-2 flex-wrap align-items-center">
            <span class="small text-muted">Horizon :</span>
            <t t-foreach="[7, 14, 30]" t-as="dd">
              <a t-attf-href="/planning-tranches?days={{dd}}&amp;tp={{tp}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if days == dd else 'btn-outline-secondary'}}"><t t-esc="dd"/> jours</a>
            </t>
            <button type="button" id="tr-reset" class="btn btn-sm btn-outline-secondary py-0" title="Remettre la hauteur H sur toutes les pièces affichées ayant un choix enregistré (pour tous les écrans)">↺ Tout en H</button>
            <button type="button" id="tr-print" class="btn btn-sm btn-outline-dark py-0">🖨 Imprimer</button>
            <button onclick="window.location.reload()" class="btn btn-sm btn-outline-dark py-0">↻ Actualiser</button>
          </div>
        </div>
        <div class="d-flex gap-2 mb-2 small flex-wrap align-items-center tr-outils">
          <span class="text-muted">Matière :</span>
          <a t-attf-href="/planning-tranches?days={{days}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if not tp else 'btn-outline-secondary'}}">Toutes</a>
          <t t-foreach="mats" t-as="pk">
            <a t-attf-href="/planning-tranches?days={{days}}&amp;tp={{pk}}" t-attf-class="btn btn-sm py-0 {{'btn-dark' if tp == pk else 'btn-outline-secondary'}}">
              <span t-attf-style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{{matcol.get(pk, '#9AA0A6')}};margin-right:4px;"/><t t-esc="pk.capitalize()"/>
            </a>
          </t>
          <a t-if="tp and tp not in mats" t-attf-href="/planning-tranches?days={{days}}" class="btn btn-sm py-0 btn-dark" title="Aucune pièce de cette matière sur la période : cliquer pour retirer le filtre"><t t-esc="tp.capitalize()"/> ✕</a>
        </div>
        <p class="small text-muted mb-3 tr-outils">Une ligne = un OF (toutes ses pièces). L'épaisseur de tranche retenue est par défaut la hauteur H de la pièce ; cliquer une autre cote la retient : le choix est enregistré sur l'OF (✎) et s'affiche sur tous les écrans, qui se rafraîchissent toutes les 3 minutes. m² de tranche = volume des pièces ÷ épaisseur retenue.</p>

        <t t-foreach="mats" t-as="mk">
          <t t-set="m_ofs" t-value="[o for o in ofs if matfn(premier[o.id]) == mk]"/>
          <t t-if="m_ofs">
            <t t-set="hc" t-value="matcol.get(mk, '#9AA0A6')"/>
            <t t-set="lum" t-value="(int(hc[1:3],16)*299 + int(hc[3:5],16)*587 + int(hc[5:7],16)*114)/1000.0 if (hc and len(hc)==7) else 0"/>
            <div class="tr-mat" t-att-data-mat="mk">
              <div class="tr-head" t-attf-style="background:{{hc}};color:{{'#1a1a1a' if lum &gt; 150 else '#ffffff'}};">
                <span><t t-esc="mk.capitalize()"/> <small><span class="tr-nb-of"/> pièces · <span class="tr-m2"/> m² de tranches · <t t-esc="len(m_ofs)"/> OF</small></span>
              </div>
              <div class="tr-body">
                <div class="tr-resume">
                  <table class="tr tr-res">
                    <thead><tr><th>Épaisseur retenue</th><th class="n">Pièces</th><th class="n">m² tranche</th><th class="n">m³</th></tr></thead>
                    <tbody/>
                  </table>
                </div>
                <div class="tr-liste">
                  <table class="tr tr-pieces">
                    <thead><tr><th>Épaisseur (cote retenue)</th><th>Réf pierre</th><th>L × l × H (m)</th><th class="n">Nb</th><th>Client</th><th>BC</th><th>Prévu</th><th>Machine</th><th>OF</th></tr></thead>
                    <tbody>
                      <t t-foreach="m_ofs" t-as="o">
                        <t t-set="w" t-value="premier[o.id]"/>
                        <tr class="tr-piece" t-att-data-of="o.id" t-att-data-name="o.name" t-att-data-l="o.x_studio_long_m_1 or 0" t-att-data-w="o.x_studio_larg_m_1 or 0" t-att-data-h="o.x_studio_haut_m_1 or 0" t-att-data-nb="int(o.x_studio_nbr or 0) or 1" t-att-data-ep="o.x_epaisseur_tranche or 0" t-att-data-date="w.date_start and w.date_start.strftime('%Y-%m-%d') or ''">
                          <td class="tr-ep"/>
                          <td><b t-esc="o.x_studio_ref_pierre or ''"/></td>
                          <td><t t-esc="'%.3f' % (o.x_studio_long_m_1 or 0)"/> × <t t-esc="'%.3f' % (o.x_studio_larg_m_1 or 0)"/> × <t t-esc="'%.3f' % (o.x_studio_haut_m_1 or 0)"/></td>
                          <td class="n" t-esc="int(o.x_studio_nbr or 0) or 1"/>
                          <td class="text-truncate" style="max-width:190px;" t-esc="o.x_studio_nom_du_client or ''"/>
                          <td t-esc="o.origin or ''"/>
                          <td t-esc="w.date_start and w.date_start.strftime('%d/%m') or ''"/>
                          <td t-esc="w.workcenter_id.name or ''"/>
                          <td><a t-attf-href="/web#id={{o.id}}&amp;model=mrp.production&amp;view_type=form" target="_blank" t-esc="o.name"/></td>
                        </tr>
                      </t>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </t>
        </t>
        <div t-if="not ofs" class="alert alert-info">Aucune opération de sciage secondaire planifiée sur cette période<t t-if="tp"> pour cette matière</t>.</div>

        <script>
__JS__
        </script>
      </section>
    </div>
  </t>
</t>"""

arch = ARCH.replace('__JS__', html.escape(JS, quote=False))
ET.fromstring(arch.encode('utf-8'))
os.makedirs('boards', exist_ok=True)
io.open('boards/tranches.xml', 'w', encoding='utf-8', newline='\n').write(arch)
print('arch : %d caractères, XML OK' % len(arch))
if mode == 'apply':
    U, D = 'https://maquignon.odoo.com', 'maquignon'
    us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
    assert 'x_epaisseur_tranche' in x('mrp.production', 'fields_get', ['x_epaisseur_tranche'], ['type']), 'champ x_epaisseur_tranche absent : lancer tranches_champ.py'
    ids = x('ir.ui.view', 'search', [['key', '=', 'website.planning_tranches']])
    if ids:
        x('ir.ui.view', 'write', ids, {'arch_db': arch}); vid = ids[0]; print('vue mise à jour', vid)
    else:
        vid = x('ir.ui.view', 'create', [{'name': 'Planning Tranches', 'key': 'website.planning_tranches', 'type': 'qweb', 'arch_db': arch}])
        vid = vid[0] if isinstance(vid, list) else vid; print('vue créée', vid)
    pg = x('website.page', 'search', [['url', '=', '/planning-tranches']])
    if pg:
        x('website.page', 'write', pg, {'view_id': vid, 'is_published': True}); print('page existante', pg)
    else:
        print('page créée', x('website.page', 'create', [{'name': 'Planning Tranches', 'url': '/planning-tranches', 'view_id': vid, 'is_published': True, 'website_id': False}]))
    os.makedirs('ocr/odoo-scan-page/planning_matiere_20260930', exist_ok=True)
    io.open('ocr/odoo-scan-page/planning_matiere_20260930/tranches_%d.xml' % vid, 'w', encoding='utf-8', newline='\n').write(arch)
