# -*- coding: utf-8 -*-
"""Page EPI : champ « Scan » (douchette) dans les blocs Remise et Entrée en stock ; le code-barres scanné
(suivi d'Entrée) sélectionne l'EPI dans la liste ; inconnu = message."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'epi_page.py'
s = io.open(p, encoding='utf-8').read()
pairs = [
    ("""                    <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id" t-att-data-stock="'%g' % stock.get(pr.id, 0.0)"><t t-esc="pr.display_name"/> — stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/></option></t>""",
     """                    <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id" t-att-data-stock="'%g' % stock.get(pr.id, 0.0)" t-att-data-barcode="pr.barcode or ''"><t t-esc="pr.display_name"/> — stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/></option></t>"""),
    ("""                  <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id"><t t-esc="pr.display_name"/> (stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/>)</option></t>""",
     """                  <t t-foreach="prods" t-as="pr"><option t-att-value="pr.id" t-att-data-barcode="pr.barcode or ''"><t t-esc="pr.display_name"/> (stock <t t-esc="'%g' % stock.get(pr.id, 0.0)"/>)</option></t>"""),
    ("""                <label for="ep-prod">EPI</label>
                <div>
                  <select id="ep-prod">""",
     """                <label for="ep-scan">📷 Scan</label>
                <input type="text" id="ep-scan" class="ep-scan" data-cible="ep-prod" placeholder="scannez le code-barres de l'EPI (douchette), ou choisissez-le ci-dessous" autocomplete="off"/>
                <label for="ep-prod">EPI</label>
                <div>
                  <select id="ep-prod">"""),
    ("""                <label for="ep-rec-prod">EPI</label>
                <select id="ep-rec-prod">""",
     """                <label for="ep-rec-scan">📷 Scan</label>
                <input type="text" id="ep-rec-scan" class="ep-scan" data-cible="ep-rec-prod" placeholder="scannez le code-barres de l'EPI reçu" autocomplete="off"/>
                <label for="ep-rec-prod">EPI</label>
                <select id="ep-rec-prod">"""),
    ("""      .ep-stock-info{font-weight:900;font-size:13px;margin-top:4px;}""",
     """      .ep-stock-info{font-weight:900;font-size:13px;margin-top:4px;}
      .ep-form input.ep-scan{border-color:#0f172a;background:#f8fafc;}
      .ep-form input.ep-scan.ok{border-color:#16a34a;background:#dcfce7;}
      .ep-form input.ep-scan.bad{border-color:#dc2626;background:#fee2e2;}"""),
    ("""  if(selP){ selP.addEventListener('change', majStock); majStock(); }""",
     r"""  if(selP){ selP.addEventListener('change', majStock); majStock(); }
  /* douchette : le code-barres scanné (suivi d'Entrée) sélectionne l'EPI dans la liste ; inconnu = message */
  function scan(inp){
    var code = (inp.value || '').trim(); if(!code){ return; }
    var sel = document.getElementById(inp.getAttribute('data-cible')); var trouve = null;
    for(var i = 0; i < sel.options.length; i++){ var bc = sel.options[i].getAttribute('data-barcode') || ''; if(bc && bc === code){ trouve = sel.options[i]; break; } }
    if(!trouve){ inp.className = 'ep-scan bad'; alert('Code-barres ' + code + ' inconnu.\nEnregistrez-le sur la fiche de l\'article dans Odoo (onglet Inventaire, champ Code-barres) ou choisissez l\'EPI dans la liste.'); inp.select(); return; }
    sel.value = trouve.value; inp.className = 'ep-scan ok'; inp.value = trouve.textContent.trim();
    if(sel === selP){ majStock(); var q = document.getElementById('ep-qty'); if(q){ q.focus(); q.select(); } }
    else { var q2 = document.getElementById('ep-rec-qty'); if(q2){ q2.focus(); q2.select(); } }
  }
  document.querySelectorAll('input.ep-scan').forEach(function(inp){
    inp.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); scan(inp); } });
    inp.addEventListener('focus', function(){ inp.value = ''; inp.className = 'ep-scan'; });
  });"""),
]
for old, new in pairs:
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('page EPI : champs scan ajoutés')
