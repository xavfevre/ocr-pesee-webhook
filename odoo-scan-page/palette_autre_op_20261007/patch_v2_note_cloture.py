# -*- coding: utf-8 -*-
"""v2 (07/10/2026, après l'essai de Xavier) :
 1. relais : stock.package n'a pas de fil de discussion en Odoo 19 (message_post n'existe pas) -> la note de pose
    confirmée va dans le fil de l'OF (mrp.production) via un helper qui n'échoue jamais ; même correctif pour les
    notes du transfert responsable et de la déclôture (bug latent : l'opération était faite mais la tablette
    affichait « Échec »).
 2. tablette (vue 7907) : les palettes des autres opérateurs sont listées (section repliée, nom du responsable),
    la clôture d'une telle palette demande une confirmation explicite ; boîte de confirmation générique.
Entrées : ocr/web_actions.py (v1), vue_7907.AFTER.xml (v1) -> sorties : web_actions.py, vue_7907.AFTER2.xml, vue_operateur.xml.
  python patch_v2_note_cloture.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, '..', '..'))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read()


def ecrire(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def ecrire_comme(p, s):
    if os.path.exists(p) and '\r\n' in lire(p):
        s = s.replace('\r\n', '\n').replace('\n', '\r\n')
    ecrire(p, s)


def remplacer(s, old, new, n=1, nom=''):
    assert s.count(old) == n, 'ancre %s trouvée %d fois (attendu %d) : %r' % (nom, s.count(old), n, old[:90])
    return s.replace(old, new)


esc = lambda t: t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ───────────────────────── 1. relais ─────────────────────────
p = os.path.join(R, 'web_actions.py'); s = lire(p)
if 'def _note(' in s:
    print('web_actions.py : déjà en v2')
else:
    s = remplacer(s, "def _colis_co_operateur(call, colis, emp):", '''def _note(call, model, res_id, body):
    """Note de traçabilité dans le fil d'un enregistrement ; ne fait jamais échouer l'opération (stock.package n'a
    pas de fil de discussion en Odoo 19 : message_post n'existe pas sur ce modèle)."""
    try:
        call(model, 'message_post', [res_id], body=body, message_type='comment')
    except Exception:  # noqa: BLE001
        pass


def _colis_co_operateur(call, colis, emp):''', nom='helper _note')
    s = remplacer(s, """        _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                          body='🤝 %d pcs de %s posées par %s sur la palette de %s (confirmé sur la tablette)'
                               % (res['qte'], of['name'], emp['name'], prop[1])))
""", """        _note(call, 'mrp.production', of['id'], '🤝 %d pcs posées sur %s (palette de %s) par %s, confirmé sur la tablette'
              % (res['qte'], colis['name'], prop[1], emp['name']))
""", nom='note 2101')
    s = remplacer(s, """        _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                          body='🤝 %d pcs de %s (pierre de %s) posées sur la palette de %s (confirmé au poste de scan)'
                               % (res['qte'], of['name'], noms, prop[1])))
""", """        _note(call, 'mrp.production', of['id'], '🤝 %d pcs posées sur %s (palette de %s), pierre de %s, confirmé au poste de scan'
              % (res['qte'], colis['name'], prop[1], noms))
""", nom='note 2102')
    s = remplacer(s, """    _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                      body='🔑 Palette transférée de %s à %s (mode responsable, tablette)' % (avant, emp['name'])))
""", """    _note(call, 'stock.package', colis['id'], '🔑 Palette transférée de %s à %s (mode responsable, tablette)' % (avant, emp['name']))
""", nom='note transfert')
    s = remplacer(s, """    _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                      body='🔓 Palette déclôturée depuis le poste de scan (elle était clôturée → %s)' % (colis['x_studio_zone'] or '?')))
""", """    _note(call, 'stock.package', colis['id'], '🔓 Palette déclôturée depuis le poste de scan (elle était clôturée → %s)' % (colis['x_studio_zone'] or '?'))
""", nom='note déclôture')
    ast.parse(s); ecrire(p, s); print('web_actions.py : v2 (notes sûres, syntaxe ok)')

# ───────────────────────── 2. vue 7907 ─────────────────────────
src, dst = os.path.join(HERE, 'vue_7907.AFTER.xml'), os.path.join(HERE, 'vue_7907.AFTER2.xml')
s = lire(src)
assert 'voConfirmAutre' in s and 'colis_tiers' not in s, 'la vue AFTER v1 est attendue en entrée'
# a) liste des palettes des autres opérateurs (2 écrans)
s = remplacer(s, '''            <t t-set="autres_colis" t-value="[cq for cq in colis_ouverts if not cq.x_operateur_id and (colis_cnt.get(cq.id, 0) + rep_cnt.get(cq.id, 0)) &gt; 0]"/>
''', '''            <t t-set="autres_colis" t-value="[cq for cq in colis_ouverts if not cq.x_operateur_id and (colis_cnt.get(cq.id, 0) + rep_cnt.get(cq.id, 0)) &gt; 0]"/>
            <t t-set="colis_tiers" t-value="[cq for cq in colis_ouverts if cq.x_operateur_id and cq.x_operateur_id.id != op_int]"/>
''', n=2, nom='t-set colis_tiers')
# b) JSON des palettes : + nom du responsable (p) et palettes des autres opérateurs
s = remplacer(s, "&quot;o&quot;:%d}' % (c.id,", "&quot;o&quot;:%d,&quot;p&quot;:&quot;%s&quot;}' % (c.id,", n=2, nom='json clé p')
s = remplacer(s, "(1 if (op_int and c.x_operateur_id.id == op_int) else 0)) for c in (mes_colis + autres_colis)]) + ']'\"",
              "(1 if (op_int and c.x_operateur_id.id == op_int) else 0), ((c.x_operateur_id.name or '') if c.x_operateur_id else '').replace('&quot;', '')) for c in (mes_colis + autres_colis + colis_tiers)]) + ']'\"", n=2, nom='json valeur p')
# c) section repliée « Palettes des autres opérateurs » avant le bouton Responsable (2 écrans)
SECTION = '''              <t t-if="colis_tiers">
                <button type="button" class="vo-colis-tiers btn btn-sm btn-outline-warning w-100" style="margin-top:6px;font-weight:700;" t-att-data-show="'Palettes des autres opérateurs (%d) — pose ou clôture sur confirmation' % len(colis_tiers)">Palettes des autres opérateurs (<t t-esc="len(colis_tiers)"/>) — pose ou clôture sur confirmation</button>
                <div style="display:none;margin-top:8px;">
                  <t t-foreach="colis_tiers" t-as="cp">
                <t t-set="cpn" t-value="colis_cnt.get(cp.id, 0)"/><t t-set="cprn" t-value="rep_cnt.get(cp.id, 0)"/>
                <div class="d-flex gap-1 mb-2">
                  <button type="button" class="vo-colis-choice btn btn-outline-primary flex-grow-1" style="font-weight:800;text-align:left;" t-att-data-cid="cp.id" t-att-data-cname="cp.name"><t t-esc="cp.name"/> <span style="color:#b45309;font-size:12px;">👤 <t t-esc="cp.x_operateur_id.name"/></span> <span style="font-weight:600;color:#64748b;">— <t t-esc="cpn"/> OF<t t-if="cprn"> +<t t-esc="cprn"/> rép.</t> · <t t-esc="'%.0f' % (cp.x_studio_tonnage or 0)"/> kg</span></button>
                  <button type="button" class="vo-colis-lock btn btn-outline-success" style="font-weight:800;" t-att-data-cid="cp.id" t-att-data-cname="cp.name" title="Clôturer ce colis">🔒</button>
                </div>
                  </t>
                </div>
              </t>
'''
CHEF = '''              <button type="button" class="vo-chef btn btn-sm btn-outline-secondary w-100" style="margin-top:10px;font-weight:700;">🔑 Responsable : prendre la palette d'un autre opérateur</button>
'''
s = remplacer(s, CHEF, SECTION + CHEF, n=2, nom='section tiers')
# d) rendu des lignes de recherche : nom du responsable
s = remplacer(s, esc('''+c.name+(c.o?' <span style="color:#0f766e;font-size:12px;">👤 moi</span>':'')+' <span style="font-weight:600;color:#64748b;"'''),
              esc('''+c.name+(c.o?' <span style="color:#0f766e;font-size:12px;">👤 moi</span>':(c.p?' <span style="color:#b45309;font-size:12px;">👤 '+c.p+'</span>':''))+' <span style="font-weight:600;color:#64748b;"'''), n=2, nom='rowC')
# e) repli/dépli de la section + confirmation avant la clôture d'une palette d'un autre opérateur (2 écrans)
ZONE = "          var zonePop=document.getElementById('vo-zone-pop'); var lockCid=0, lockName='', lockRow=null;\n"
TOGGLE = ("          document.querySelectorAll('.vo-colis-tiers').forEach(function(b){ b.onclick=function(){ var l=b.nextElementSibling; if(!l){ return; } var open=(l.style.display==='none'); l.style.display=open?'':'none'; b.textContent=open?'Masquer les palettes des autres opérateurs':b.getAttribute('data-show'); }; });\n")
s = remplacer(s, ZONE, esc(TOGGLE) + ZONE, n=2, nom='toggle tiers')
LOCK_OLD = esc("              if(lb){ lockCid=parseInt(lb.getAttribute('data-cid')); lockName=lb.getAttribute('data-cname'); lockRow=lb.parentNode; var n=document.getElementById('vo-zone-cname'); if(n){ n.textContent=lockName; } if(zonePop){ zonePop.style.display='flex'; } }\n")
LOCK_NEW = esc("              if(lb){ lockCid=parseInt(lb.getAttribute('data-cid')); lockName=lb.getAttribute('data-cname'); lockRow=lb.parentNode; var n=document.getElementById('vo-zone-cname'); if(n){ n.textContent=lockName; } var tc=COLIS.filter(function(c){ return c.id===lockCid; })[0]; var openZone=function(){ if(zonePop){ zonePop.style.display='flex'; } }; if(tc && !tc.o && tc.p){ voConfirmBox('🔒 Palette d\\'un autre opérateur', lockName+' est la palette de '+tc.p+'. Clôturer quand même ?', 'Le bon de colisage sera imprimé et le bureau prévenu, comme pour une clôture normale.', '✅ Oui, clôturer', openZone); } else { openZone(); } }\n")
s = remplacer(s, LOCK_OLD, LOCK_NEW, n=2, nom='lock confirm')
# f) boîte de confirmation générique (remplace la v1)
V1 = r"""          // pose sur la palette d'un autre opérateur : confirmation explicite de l'opérateur (Xavier, 07/10/2026)
          window.voConfirmAutre = function(r, onYes){
            function h(t){ var d=document.createElement('div'); d.textContent=(t==null?'':String(t)); return d.innerHTML; }
            var old=document.getElementById('vo-autre-pop'); if(old){ old.remove(); }
            var ov=document.createElement('div'); ov.id='vo-autre-pop';
            ov.style.cssText='position:fixed;inset:0;background:rgba(2,6,23,.82);z-index:100000;display:flex;align-items:center;justify-content:center;padding:16px;';
            ov.innerHTML='<div style="background:#fff;border:3px solid #f59e0b;border-radius:18px;padding:20px;width:460px;max-width:96vw;box-shadow:0 20px 60px rgba(0,0,0,.5);">'
              +'<div style="font-size:22px;font-weight:900;color:#b45309;text-align:center;margin-bottom:10px;">🤝 Palette d\'un autre opérateur</div>'
              +'<div style="font-size:18px;font-weight:800;color:#0f172a;text-align:center;line-height:1.4;">'+h(r.colis)+' est la palette de <span style="color:#b45309;">'+h(r.proprietaire)+'</span>.<br/>Poser quand même <b>'+h(r.qte||'')+' pièce'+((r.qte||0)>1?'s':'')+'</b> de '+h(r.of)+' dessus ?</div>'
              +'<div style="font-size:13px;color:#64748b;text-align:center;margin:10px 0 14px;">La palette reste celle de '+h(r.proprietaire)+'. Votre pose sera notée sur la palette.</div>'
              +'<div style="display:flex;gap:10px;"><button type="button" id="vo-autre-oui" style="flex:2;background:#d97706;color:#fff;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:900;">✅ Oui, poser</button>'
              +'<button type="button" id="vo-autre-non" style="flex:1;background:#e2e8f0;color:#0f172a;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:800;">✖ Non</button></div></div>';
            document.body.appendChild(ov);
            ov.querySelector('#vo-autre-non').onclick=function(){ ov.remove(); };
            ov.querySelector('#vo-autre-oui').onclick=function(){ ov.remove(); onYes(); };
          };
"""
V2 = r"""          // palette d'un autre opérateur : pose ou clôture seulement sur confirmation explicite (Xavier, 07/10/2026)
          function voH(t){ var d=document.createElement('div'); d.textContent=(t==null?'':String(t)); return d.innerHTML; }
          window.voConfirmBox = function(titre, texteHtml, sous, oui, onYes){
            var old=document.getElementById('vo-autre-pop'); if(old){ old.remove(); }
            var ov=document.createElement('div'); ov.id='vo-autre-pop';
            ov.style.cssText='position:fixed;inset:0;background:rgba(2,6,23,.82);z-index:100000;display:flex;align-items:center;justify-content:center;padding:16px;';
            ov.innerHTML='<div style="background:#fff;border:3px solid #f59e0b;border-radius:18px;padding:20px;width:460px;max-width:96vw;box-shadow:0 20px 60px rgba(0,0,0,.5);">'
              +'<div style="font-size:22px;font-weight:900;color:#b45309;text-align:center;margin-bottom:10px;">'+titre+'</div>'
              +'<div style="font-size:18px;font-weight:800;color:#0f172a;text-align:center;line-height:1.4;">'+texteHtml+'</div>'
              +'<div style="font-size:13px;color:#64748b;text-align:center;margin:10px 0 14px;">'+voH(sous)+'</div>'
              +'<div style="display:flex;gap:10px;"><button type="button" id="vo-autre-oui" style="flex:2;background:#d97706;color:#fff;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:900;">'+voH(oui)+'</button>'
              +'<button type="button" id="vo-autre-non" style="flex:1;background:#e2e8f0;color:#0f172a;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:800;">✖ Non</button></div></div>';
            document.body.appendChild(ov);
            ov.querySelector('#vo-autre-non').onclick=function(){ ov.remove(); };
            ov.querySelector('#vo-autre-oui').onclick=function(){ ov.remove(); onYes(); };
          };
          window.voConfirmAutre = function(r, onYes){
            voConfirmBox('🤝 Palette d\'un autre opérateur',
              voH(r.colis)+' est la palette de <span style="color:#b45309;">'+voH(r.proprietaire)+'</span>.<br/>Poser quand même <b>'+voH(r.qte||'')+' pièce'+((r.qte||0)>1?'s':'')+'</b> de '+voH(r.of)+' dessus ?',
              'La palette reste celle de '+(r.proprietaire||'son opérateur')+'. Votre pose sera notée sur l\'OF.', '✅ Oui, poser', onYes);
          };
"""
s = remplacer(s, esc(V1), esc(V2), nom='confirm box v2')
ecrire(dst, s)
ecrire_comme(os.path.join(R, 'odoo-scan-page', 'vue_operateur.xml'), s)
print('vue_7907.AFTER2.xml : écrite (%d car.)' % len(s))
