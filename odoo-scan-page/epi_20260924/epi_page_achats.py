# -*- coding: utf-8 -*-
"""Page EPI : colonnes Mini / Maxi (règles de réapprovisionnement, saisie directe), fournisseurs référencés,
bouton « Demandes de prix » (EPI sous le mini -> une demande par fournisseur), liste des demandes de prix en cours."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'epi_page.py'
s = io.open(p, encoding='utf-8').read()
pairs = [
    # données : règles, fournisseurs, demandes de prix
    ("""        <t t-set="emps" t-value="request.env['hr.employee'].sudo().search([('active','=',True)], order='company_id, name')"/>""",
     """        <t t-set="emps" t-value="request.env['hr.employee'].sudo().search([('active','=',True)], order='company_id, name')"/>
        <t t-set="regles" t-value="dict((o.product_id.id, o) for o in request.env['stock.warehouse.orderpoint'].sudo().search([('location_id','=',loc_stock)]))"/>
        <t t-set="fourn" t-value="{}"/>
        <t t-set="_f" t-value="[fourn.setdefault(si.product_tmpl_id.id, []).append(si.partner_id.name) for si in request.env['product.supplierinfo'].sudo().search([('product_tmpl_id','in',prods.mapped('product_tmpl_id').ids),'|',('company_id','=',False),('company_id','=',1)], order='sequence, id') if si.partner_id.name not in fourn.get(si.product_tmpl_id.id, [])]"/>
        <t t-set="dps" t-value="request.env['purchase.order'].sudo().search([('origin','=','EPI stock mini'),('state','in',['draft','sent','to approve','purchase'])], order='id desc', limit=12)"/>
        <t t-set="etat_dp" t-value="{'draft': 'brouillon', 'sent': 'envoyée', 'to approve': 'à approuver', 'purchase': 'commandée'}"/>"""),
    # tableau stock : colonnes mini / maxi / fournisseurs, alerte selon le mini
    ("""              <table class="ep">
                <tr><th>EPI</th><th class="n">En stock</th><th class="n">Prix</th></tr>
                <t t-foreach="prods" t-as="pr">
                  <t t-set="q" t-value="stock.get(pr.id, 0.0)"/>
                  <tr t-attf-class="{{'bad' if q &lt;= 0 else ('warn' if q &lt;= 2 else '')}}">
                    <td t-esc="pr.display_name"/>
                    <td class="n"><t t-esc="'%g' % q"/></td>
                    <td class="n" style="color:#64748b;font-weight:600;"><t t-esc="('%.2f' % pr.standard_price).replace('.', ',')"/> €</td>
                  </tr>
                </t>
                <tr t-if="not prods"><td colspan="3" style="color:#94a3b8;">Aucun article dans la catégorie EPI.</td></tr>
              </table>
              <div class="ep-help" style="margin-top:6px;">Rouge = rupture, orange = 2 ou moins. Valeur du stock : <b><t t-esc="('%.2f' % sum([stock.get(pr.id, 0.0) * pr.standard_price for pr in prods])).replace('.', ',')"/> €</b>.</div>""",
     """              <table class="ep">
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
              </table>"""),
    # CSS
    ("""      .ep-stock-info{font-weight:900;font-size:13px;margin-top:4px;}""",
     """      .ep-stock-info{font-weight:900;font-size:13px;margin-top:4px;}
      .ep td input.ep-mini{width:58px;border:1.5px solid #cbd5e1;border-radius:7px;padding:3px 4px;font-weight:800;text-align:center;font-size:13px;background:#fff;}
      .ep td input.ep-mini.ok{border-color:#16a34a;background:#dcfce7;}
      .ep td input.ep-mini.err{border-color:#dc2626;background:#fee2e2;}"""),
    # JS : mini / maxi + demandes de prix
    ("""  var filtre = document.getElementById('ep-filtre');""",
     """  /* stock mini / maxi : enregistrés dès la modification (règle de réapprovisionnement) */
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
      if(!r.nb_epi){ dp.disabled = false; alert('Aucun EPI sous son stock mini : rien à commander.\\n(Renseignez les colonnes Mini / Maxi dans le tableau.)'); return; }
      var txt = r.nb_epi + ' EPI sous le mini.\\n';
      if(r.fournisseurs.length){ txt += 'Demandes de prix à créer : ' + r.fournisseurs.map(function(f){ return f.nom + ' (' + f.nb + ' EPI)'; }).join(', ') + '.\\n'; }
      if(r.sans_fournisseur.length){ txt += 'Sans fournisseur référencé (à compléter sur la fiche article) : ' + r.sans_fournisseur.join(', ') + '.\\n'; }
      if(!r.fournisseurs.length){ dp.disabled = false; alert(txt); return; }
      if(!confirm(txt + '\\nCréer ces demandes de prix dans Odoo ?')){ dp.disabled = false; return; }
      rpc(2114, {}).then(function(d2){
        if(d2.error){ dp.disabled = false; alert('Échec : ' + msg(d2)); return; }
        var r2 = d2.result || {};
        flash('✓ ' + r2.commandes.map(function(c){ return c.nom + ' — ' + c.fournisseur + ' (' + c.nb + ' EPI' + (c.maj ? ', mise à jour' : '') + ')'; }).join(' · ') + (r2.sans_fournisseur.length ? ' — sans fournisseur : ' + r2.sans_fournisseur.join(', ') : ''), true);
      }).catch(function(){ dp.disabled = false; alert('Échec réseau'); });
    }).catch(function(){ dp.disabled = false; alert('Échec réseau'); });
  }); }
  var filtre = document.getElementById('ep-filtre');"""),
]
for old, new in pairs:
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('page EPI : mini / maxi, fournisseurs, demandes de prix')
