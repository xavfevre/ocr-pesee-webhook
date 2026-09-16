# -*- coding: utf-8 -*-
"""Vue opérateur v4 : messages non bloquants (toasts) à la place des alert(), « Palettiser (N faites) » sur
l'Historique avec pavé quantité, jauge de remplissage (seuil maquignon.palette_max_kg), ⚡ avec le poids,
mode responsable (transfert d'une palette sur code), filtres en cascade (client → réf. cde → palette)."""
import io, re, sys, html
import xml.etree.ElementTree as ET
import esprima
sys.stdout.reconfigure(encoding='utf-8')
s = io.open('vue_operateur_v3.xml', encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90]); s = s.replace(old, new)


# ── CSS ──
rep(""".vo-hist-time{font-size:14px;font-weight:800;color:#166534;background:#dcfce7;border-radius:7px;padding:2px 10px;display:inline-block;margin:3px 0;}""",
    """.vo-hist-time{font-size:14px;font-weight:800;color:#166534;background:#dcfce7;border-radius:7px;padding:2px 10px;display:inline-block;margin:3px 0;}
        .vo-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:20000;background:#0f172a;color:#fff;font-weight:800;font-size:16px;border-radius:12px;padding:12px 18px;box-shadow:0 8px 30px rgba(0,0,0,.35);max-width:92vw;opacity:0;transition:opacity .2s;pointer-events:none;text-align:center;}
        .vo-toast.on{opacity:1;} .vo-toast.ok{background:#15803d;} .vo-toast.err{background:#b91c1c;} .vo-toast.warn{background:#b45309;}
        .vo-jauge{height:8px;border-radius:6px;background:#e2e8f0;overflow:hidden;margin-top:4px;} .vo-jauge > div{height:8px;}""")
# ── seuil de poids (paramètre) ──
rep("""      <t t-set="jours" t-value="['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']"/>""",
    """      <t t-set="jours" t-value="['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche']"/>
      <t t-set="max_kg" t-value="float(request.env['ir.config_parameter'].sudo().get_param('maquignon.palette_max_kg', '1500') or 1500)"/>""")
# ── jauge dans les lignes de palettes (QWeb, 4 occurrences) + poids sur ⚡ ──
rep("""· <t t-esc="'%.0f' % cp.x_studio_tonnage"/> kg</span>""",
    """· <t t-esc="'%.0f' % cp.x_studio_tonnage"/> kg</span><div class="vo-jauge"><div t-attf-style="width:{{min(100, int(100 * (cp.x_studio_tonnage or 0) / max_kg))}}%;background:{{'#dc2626' if (cp.x_studio_tonnage or 0) >= max_kg else ('#f59e0b' if (cp.x_studio_tonnage or 0) >= 0.8 * max_kg else '#16a34a')}};"/></div>""", 4)
rep("""<div id="vo-pal-act" style="display:none;" t-att-data-id="pal_act.id if pal_act else ''" t-att-data-name="pal_act.name if pal_act else ''"/>""",
    """<div id="vo-pal-act" style="display:none;" t-att-data-id="pal_act.id if pal_act else ''" t-att-data-name="pal_act.name if pal_act else ''" t-att-data-ton="('%.0f' % (pal_act.x_studio_tonnage or 0)) if pal_act else ''"/>""", 2)
rep("""<div id="vo-colis-data" style="display:none;" t-att-data-colis=""", """<div id="vo-colis-data" style="display:none;" t-att-data-maxkg="max_kg" t-att-data-colis=""", 2)
rep("""lastColis={id:parseInt(_pa.getAttribute('data-id')), name:_pa.getAttribute('data-name')};""",
    """lastColis={id:parseInt(_pa.getAttribute('data-id')), name:_pa.getAttribute('data-name'), ton:parseFloat(_pa.getAttribute('data-ton'))||0};""", 2)
rep("""          function saveLast(cid,cname){ lastColis={id:cid,name:cname}; }""",
    """          function saveLast(cid,cname,ton){ lastColis={id:cid,name:cname,ton:ton||0}; }
          function voLastLbl(){ return '⚡ '+lastColis.name+(lastColis.ton?' · '+Math.round(lastColis.ton)+' kg':''); }""")
rep("""        function saveLastC(cid,cname){ lastColis={id:cid,name:cname}; }""",
    """        function saveLastC(cid,cname,ton){ lastColis={id:cid,name:cname,ton:ton||0}; }
        function voLastLbl(){ return '⚡ '+lastColis.name+(lastColis.ton?' · '+Math.round(lastColis.ton)+' kg':''); }""")
assert s.count("⚡ '+lastColis.name") >= 3
s = s.replace("⚡ '+lastColis.name", "'+voLastLbl()")
# ne pas toucher la fonction elle-même (sinon récursion infinie : bug du 16/09 corrigé)
s = s.replace("function voLastLbl(){ return ''+voLastLbl()+(lastColis.ton", "function voLastLbl(){ return '⚡ '+lastColis.name+(lastColis.ton")
# jauge dans les lignes construites en JS (rowC, 2 occurrences) + MAXKG
rep("""var COLIS=[]; try{ COLIS=JSON.parse((dataC &amp;&amp; dataC.getAttribute('data-colis'))||'[]'); }catch(e){}""",
    """var COLIS=[]; try{ COLIS=JSON.parse((dataC &amp;&amp; dataC.getAttribute('data-colis'))||'[]'); }catch(e){}
          var MAXKG=parseFloat(dataC &amp;&amp; dataC.getAttribute('data-maxkg'))||1500;
          function jaugeC(t){ return '&lt;div class="vo-jauge"&gt;&lt;div style="width:'+Math.min(100,Math.round(100*(t||0)/MAXKG))+'%;background:'+((t||0)&gt;=MAXKG?'#dc2626':((t||0)&gt;=0.8*MAXKG?'#f59e0b':'#16a34a'))+';"&gt;&lt;/div&gt;&lt;/div&gt;'; }""", 2)
rep("""+c.n+' OF · '+c.c+' m³ · '+c.t+' kg&lt;/span&gt;'+(c.m?""", """+c.n+' OF · '+c.c+' m³ · '+c.t+' kg&lt;/span&gt;'+jaugeC(c.t)+(c.m?""", 2)

# ── toasts ──
rep("""      function voPickOp(v){""", """      var _vtEl=null,_vtTimer=null;
      window.voToast=function(msg,kind){
        msg=String(msg==null?'':msg);
        if(!kind){ kind=/^(Échec|Echec|Erreur|⚠|❌|⛔|Caméra|Scanner)/.test(msg)?'err':(/^🔒/.test(msg)?'warn':'ok'); }
        if(!_vtEl){ _vtEl=document.createElement('div'); _vtEl.className='vo-toast'; document.body.appendChild(_vtEl); }
        _vtEl.textContent=msg; _vtEl.className='vo-toast '+kind;
        void _vtEl.offsetWidth; _vtEl.classList.add('on');
        if(_vtTimer){ clearTimeout(_vtTimer); }
        _vtTimer=setTimeout(function(){ _vtEl.classList.remove('on'); }, kind==='ok'?3200:6000);
      };
      function voPickOp(v){""")
s2 = re.sub(r"alert\('💥 Rebut enregistré — OF relancé : '\+nn\);\s*location\.reload\(\);",
            "voToast('💥 Rebut enregistré — OF relancé : '+nn, 'ok');\n              setTimeout(function(){ location.reload(); }, 1500);", s)
assert s2 != s; s = s2
assert 'window.alert' not in s
n_alert = s.count('alert(')
s = s.replace('alert(', 'voToast(')
print('alert() remplacés :', n_alert)
# message de succès après une pose (historique + production)
rep("""              var r=d.result||{};
              saveLast(r.colis_id||cid, r.colis||cname);
              markDone(btn,(r.colis||cname)+(r.entier?'':' (réparti)'));""",
    """              var r=d.result||{};
              voQteH=null;
              voToast((r.msg||('✅ Posé sur '+(r.colis||cname)))+(r.colis_ton?' · '+r.colis_ton+' / '+Math.round(r.max_kg||1500)+' kg':''), 'ok');
              saveLast(r.colis_id||cid, r.colis||cname, r.colis_ton);
              if(r.entier || !(r.reste&gt;0)){ markDone(btn,(r.colis||cname)+(r.entier?'':' (réparti)')); }
              else if(btn){ var nd=Math.max(0,(parseInt(btn.getAttribute('data-dispo'))||0)-(r.qte||0)); btn.setAttribute('data-dispo', String(nd)); btn.textContent='📦 Palettiser ('+nd+' faite'+(nd&gt;1?'s':'')+')'; if(!nd){ btn.disabled=true; } }""")
rep("""            var r=d.result||{};
            if(r.colis_id){ saveLastC(r.colis_id, r.colis||cname); }""",
    """            var r=d.result||{};
            voToast((r.msg||('✅ Posé sur '+(r.colis||cname)))+(r.colis_ton?' · '+r.colis_ton+' / '+Math.round(r.max_kg||1500)+' kg':''), 'ok');
            if(r.colis_id){ saveLastC(r.colis_id, r.colis||cname, r.colis_ton); }""")

# ── Historique : Palettiser (N faites) ──
rep("""        <t t-set="colis_ouverts" t-value="request.env['stock.package'].sudo().search([('x_studio_cloturee','!=',True)], order='id desc', limit=300)"/>
        <t t-set="colis_cnt" t-value="dict((g['x_studio_colis'][0], g['x_studio_colis_count']) for g in request.env['mrp.production'].sudo().read_group([('x_studio_colis','in',colis_ouverts.ids)], ['id'], ['x_studio_colis']))"/>
        <t t-set="rep_cnt" t-value="dict((g['x_studio_colis_id'][0], g['x_studio_colis_id_count']) for g in request.env['x_repartition_palette'].sudo().read_group([('x_studio_colis_id','in',colis_ouverts.ids)], ['id'], ['x_studio_colis_id']))"/>
        <t t-set="colis_ofs" t-value="request.env['mrp.production'].sudo().search([('x_studio_colis','in',colis_ouverts.ids)])"/>
        <t t-set="colis_reps" t-value="request.env['x_repartition_palette'].sudo().search([('x_studio_colis_id','in',colis_ouverts.ids)])"/>
        <t t-set="colis_pairs" t-value="[(o, o.x_studio_colis.id) for o in colis_ofs] + [(r.x_studio_of_id, r.x_studio_colis_id.id) for r in colis_reps if r.x_studio_of_id]"/>
        <t t-set="cm_cl" t-value="{}"/><t t-set="cm_rf" t-value="{}"/><t t-set="cm_pa" t-value="{}"/>
        <t t-set="_m1" t-value="[cm_cl.setdefault(ci, set()).add(o.x_studio_nom_du_client) for o, ci in colis_pairs if o.x_studio_nom_du_client]"/>
        <t t-set="_m2" t-value="[cm_rf.setdefault(ci, set()).add(o.x_studio_ref_commande_client) for o, ci in colis_pairs if o.x_studio_ref_commande_client]"/>
        <t t-set="_m3" t-value="[cm_pa.setdefault(ci, set()).add(o.x_studio_palette) for o, ci in colis_pairs if o.x_studio_palette]"/>
        <t t-set="colis_meta" t-value="dict((c.id, ' · '.join([x for x in [', '.join(sorted(cm_cl.get(c.id, []))), ', '.join(sorted(cm_rf.get(c.id, []))), ', '.join(sorted(cm_pa.get(c.id, [])))] if x]).replace('&quot;',' ')) for c in colis_ouverts)"/>
        <t t-set="hmach\"""",
    """        <t t-set="colis_ouverts" t-value="request.env['stock.package'].sudo().search([('x_studio_cloturee','!=',True)], order='id desc', limit=300)"/>
        <t t-set="colis_cnt" t-value="dict((g['x_studio_colis'][0], g['x_studio_colis_count']) for g in request.env['mrp.production'].sudo().read_group([('x_studio_colis','in',colis_ouverts.ids)], ['id'], ['x_studio_colis']))"/>
        <t t-set="rep_cnt" t-value="dict((g['x_studio_colis_id'][0], g['x_studio_colis_id_count']) for g in request.env['x_repartition_palette'].sudo().read_group([('x_studio_colis_id','in',colis_ouverts.ids)], ['id'], ['x_studio_colis_id']))"/>
        <t t-set="colis_ofs" t-value="request.env['mrp.production'].sudo().search([('x_studio_colis','in',colis_ouverts.ids)])"/>
        <t t-set="colis_reps" t-value="request.env['x_repartition_palette'].sudo().search([('x_studio_colis_id','in',colis_ouverts.ids)])"/>
        <t t-set="colis_pairs" t-value="[(o, o.x_studio_colis.id) for o in colis_ofs] + [(r.x_studio_of_id, r.x_studio_colis_id.id) for r in colis_reps if r.x_studio_of_id]"/>
        <t t-set="cm_cl" t-value="{}"/><t t-set="cm_rf" t-value="{}"/><t t-set="cm_pa" t-value="{}"/>
        <t t-set="_m1" t-value="[cm_cl.setdefault(ci, set()).add(o.x_studio_nom_du_client) for o, ci in colis_pairs if o.x_studio_nom_du_client]"/>
        <t t-set="_m2" t-value="[cm_rf.setdefault(ci, set()).add(o.x_studio_ref_commande_client) for o, ci in colis_pairs if o.x_studio_ref_commande_client]"/>
        <t t-set="_m3" t-value="[cm_pa.setdefault(ci, set()).add(o.x_studio_palette) for o, ci in colis_pairs if o.x_studio_palette]"/>
        <t t-set="colis_meta" t-value="dict((c.id, ' · '.join([x for x in [', '.join(sorted(cm_cl.get(c.id, []))), ', '.join(sorted(cm_rf.get(c.id, []))), ', '.join(sorted(cm_pa.get(c.id, [])))] if x]).replace('&quot;',' ')) for c in colis_ouverts)"/>
        <!-- pièces déjà réparties sur palette pour les OF de l'historique (Palettiser N faites) -->
        <t t-set="reps_h" t-value="{}"/>
        <t t-set="_rh" t-value="[reps_h.update({r.x_studio_of_id.id: reps_h.get(r.x_studio_of_id.id, 0) + int(r.x_studio_qte or 0)}) for r in request.env['x_repartition_palette'].sudo().search([('x_studio_of_id','in',dones.mapped('production_id').ids)]) if r.x_studio_of_id]"/>
        <t t-set="hmach\"""")
rep("""<t t-else=""><t t-set="nxt" t-value="of.workorder_ids.filtered(lambda o: o.state not in ('done', 'cancel')).sorted(key=lambda o: (o.sequence or 0, o.id))[:1]"/><span style="font-size:11.5px;color:#94a3b8;"><t t-if="nxt">⏭ Reste à faire : <b t-esc="nxt.name"/><t t-if="nxt.workcenter_id"> · <t t-esc="nxt.workcenter_id.name"/></t> — mise en palette après la dernière opération</t><t t-else="">OF non clôturé — colisage impossible</t></span></t>""",
    """<t t-else=""><t t-set="nxt" t-value="of.workorder_ids.filtered(lambda o: o.state not in ('done', 'cancel')).sorted(key=lambda o: (o.sequence or 0, o.id))[:1]"/><t t-set="wo_last" t-value="of.workorder_ids.sorted(key=lambda o: (o.sequence or 0, o.id))[-1:]"/><t t-set="tot_h" t-value="int(of.x_studio_nbr or 1)"/><t t-set="faites_h" t-value="tot_h if (wo_last and wo_last.state == 'done') else int((wo_last.x_studio_nbr_fait if wo_last else 0) or 0)"/><t t-set="dispo_h" t-value="max(0, min(tot_h, faites_h) - reps_h.get(of.id, 0))"/><button t-if="dispo_h" type="button" class="vo-addcolis btn btn-sm btn-warning" t-att-data-ofid="of.id" t-att-data-dispo="dispo_h" t-att-data-of="of.name" style="font-weight:800;">📦 Palettiser (<t t-esc="dispo_h"/> faite<t t-if="dispo_h &gt; 1">s</t>)</button><span style="font-size:11.5px;color:#94a3b8;"><t t-if="nxt"> ⏭ Reste à faire : <b t-esc="nxt.name"/><t t-if="nxt.workcenter_id"> · <t t-esc="nxt.workcenter_id.name"/></t><t t-if="not dispo_h"> — mise en palette après la dernière opération, ou après « +1 pièce » sur Ma production</t></t><t t-else="">OF non clôturé</t></span></t>""")
# pavé quantité dans la branche historique (copie de celui de la production)
a = s.index('        <div id="vo-qte-pop"'); b = s.index('        <div id="vo-colis-pop"', a)
pad = s[a:b]
first_colis_pop = s.index('        <div id="vo-colis-pop"')
assert first_colis_pop < a
s = s[:first_colis_pop] + pad + s[first_colis_pop:]
rep("""          function assign(ofid, cid, cname, btn, after){
            var ctx={of_id:ofid, qte:0, op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; }""",
    """          var voQteH=null; var qPopH=document.getElementById('vo-qte-pop'), qPendH=null, qStrH='';
          function qDispH(){ var d=document.getElementById('vo-qte-disp'); if(d &amp;&amp; qPendH){ d.textContent=(qStrH===''?qPendH.max:qStrH); d.style.color=(qStrH===''?'#94a3b8':'#0f172a'); } }
          function qOpenH(p, ok){ qPendH={max:p.max, ok:ok}; qStrH=''; document.getElementById('vo-qte-of').textContent=(p.of||'')+(p.info?' — '+p.info:''); document.getElementById('vo-qte-max').textContent=p.max; document.getElementById('vo-qte-max2').textContent=p.max; qDispH(); if(qPopH){ qPopH.style.display='flex'; } }
          function qCloseH(){ if(qPopH){ qPopH.style.display='none'; } qPendH=null; qStrH=''; }
          if(qPopH){ qPopH.addEventListener('click', function(e){
            var k=e.target.closest('.vo-qk'); if(k &amp;&amp; qPendH){ var d=k.getAttribute('data-k'); if(d==='C'){ qStrH=''; } else if(d==='back'){ qStrH=qStrH.slice(0,-1); } else { var nv=(qStrH+d).replace(/^0+/,''); if(parseInt(nv||'0')&gt;qPendH.max){ nv=String(qPendH.max); } qStrH=nv; } qDispH(); return; }
            if(e.target.closest('#vo-qte-close')){ qCloseH(); return; }
            if(e.target.closest('#vo-qte-all')){ var f=qPendH.ok; var mx=qPendH.max; qCloseH(); f(mx); return; }
            if(e.target.closest('#vo-qte-ok')){ var q=(qStrH===''?qPendH.max:parseInt(qStrH)); if(!(q&gt;0)){ return; } var f2=qPendH.ok; qCloseH(); f2(q); return; }
          }); }
          function assign(ofid, cid, cname, btn, after){
            var ctx={of_id:ofid, qte:(voQteH||0), op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; }""")
rep("""          document.querySelectorAll('.vo-addcolis').forEach(function(b){
            b.onclick=function(){ curOf=parseInt(b.getAttribute('data-ofid')); curBtn=b; if(pop){ pop.style.display='flex'; var s=document.getElementById('vo-colis-search'); if(s){ s.value=''; applySrchH(); setTimeout(function(){ s.focus(); },80); } } };
            if(lastColis &amp;&amp; lastColis.id){
              var q=document.createElement('button'); q.type='button'; q.className='vo-lastq btn btn-sm btn-primary'; q.style.cssText='font-weight:800;margin-left:6px;';
              q.textContent=''+voLastLbl();
              q.onclick=function(){ q.disabled=true; assign(parseInt(b.getAttribute('data-ofid')), lastColis.id, lastColis.name, b, function(){ q.disabled=false; }); };
              b.after(q);
            }
          });""",
    """          document.querySelectorAll('.vo-addcolis').forEach(function(b){
            var dspB=parseInt(b.getAttribute('data-dispo'))||0;
            var ouvrir=function(qq){ voQteH=qq; curOf=parseInt(b.getAttribute('data-ofid')); curBtn=b; if(pop){ pop.style.display='flex'; var s=document.getElementById('vo-colis-search'); if(s){ s.value=''; applySrchH(); setTimeout(function(){ s.focus(); },80); } } };
            b.onclick=function(){ var dsp=parseInt(b.getAttribute('data-dispo'))||0; if(dsp&gt;1){ qOpenH({max:dsp, of:b.getAttribute('data-of')||'OF', info:dsp+' pièce(s) faite(s) pas encore sur palette'}, ouvrir); } else { ouvrir(dsp||0); } };
            if(lastColis &amp;&amp; lastColis.id){
              var q=document.createElement('button'); q.type='button'; q.className='vo-lastq btn btn-sm btn-primary'; q.style.cssText='font-weight:800;margin-left:6px;';
              q.textContent=''+voLastLbl();
              q.onclick=function(){ var dsp=parseInt(b.getAttribute('data-dispo'))||0; var go=function(qq){ voQteH=qq; q.disabled=true; assign(parseInt(b.getAttribute('data-ofid')), lastColis.id, lastColis.name, b, function(){ q.disabled=false; }); }; if(dsp&gt;1){ qOpenH({max:dsp, of:b.getAttribute('data-of')||'OF', info:dsp+' pièce(s) faite(s) pas encore sur palette'}, go); } else { go(0); } };
              b.after(q);
            }
          });""")

# ── mode responsable : bouton dans le choix de palette (2 branches) ──
rep("""                  </t>
                </div>
              </t>
            </div>
          </div>
        </div>""",
    """                  </t>
                </div>
              </t>
              <button type="button" class="vo-chef btn btn-sm btn-outline-secondary w-100" style="margin-top:10px;font-weight:700;">🔑 Responsable : prendre la palette d'un autre opérateur</button>
              <div class="vo-chef-list" style="display:none;margin-top:8px;"/>
            </div>
          </div>
        </div>""", 2)
rep("""        var params = new URLSearchParams(window.location.search);
        var op = params.get('op');""",
    """        var params = new URLSearchParams(window.location.search);
        var op = params.get('op');
        // mode responsable : transférer une palette d'un autre opérateur à l'opérateur de la tablette (code bureau)
        document.querySelectorAll('.vo-chef').forEach(function(b){
          b.onclick=function(){
            var code=prompt('Code responsable :'); if(!code){ return; }
            var box=b.nextElementSibling; if(!box){ return; }
            box.style.display=''; box.innerHTML='&lt;div style="color:#64748b;font-size:13px;"&gt;Chargement…&lt;/div&gt;';
            var sel=document.getElementById('vo-op'); var opNom=sel &amp;&amp; sel.options[sel.selectedIndex] ? sel.options[sel.selectedIndex].text : 'moi';
            fetch('https://ocr-pesee-webhook.onrender.com/heures/rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:2102, ctx:{mode:'liste', colis_id:0}})})
            .then(function(r){return r.json();}).then(function(d){
              if(d.error){ throw new Error(d.error.message); }
              var rows=(d.result&amp;&amp;d.result.palettes||[]).filter(function(c){ return c.n&gt;0; });
              box.innerHTML = rows.length ? rows.map(function(c){ return '&lt;div class="d-flex gap-1 mb-2"&gt;&lt;div class="flex-grow-1" style="font-weight:800;font-size:14px;"&gt;'+c.name+' &lt;span style="color:#0f766e;font-size:12px;"&gt;👤 '+c.op+'&lt;/span&gt;&lt;div style="font-weight:600;color:#64748b;font-size:12px;"&gt;'+c.n+' OF · '+c.t_kg_placeholder+'&lt;/div&gt;&lt;/div&gt;&lt;button type="button" class="vo-chef-take btn btn-sm btn-warning" data-cid="'+c.id+'" data-cname="'+c.name+'" style="font-weight:800;white-space:nowrap;"&gt;Prendre pour '+opNom.split(' ')[0]+'&lt;/button&gt;&lt;/div&gt;'; }).join('') : '&lt;div style="color:#64748b;font-size:13px;"&gt;Aucune palette ouverte chez les autres opérateurs.&lt;/div&gt;';
              box.querySelectorAll('.vo-chef-take').forEach(function(t){ t.onclick=function(){
                if(!confirm('Transférer '+t.getAttribute('data-cname')+' à '+opNom+' ?')){ return; }
                t.disabled=true;
                fetch('https://ocr-pesee-webhook.onrender.com/heures/rpc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action_id:2102, ctx:{mode:'transferer', code:code, op:(parseInt(op)||0), colis_id:parseInt(t.getAttribute('data-cid'))}})})
                .then(function(r){return r.json();}).then(function(d2){ if(d2.error){ throw new Error(d2.error.message); } voToast(d2.result.msg||'Transféré', 'ok'); setTimeout(function(){ location.reload(); }, 1200); })
                .catch(function(e){ t.disabled=false; voToast('Échec : '+e.message, 'err'); });
              }; });
            }).catch(function(e){ box.innerHTML='&lt;div style="color:#b91c1c;font-size:13px;"&gt;'+e.message+'&lt;/div&gt;'; });
          };
        });""")
s = s.replace("c.n+' OF · '+c.t_kg_placeholder+'", "c.n+' OF · '+c.ton+' kg'+'")

# ── filtres en cascade (production) ──
rep("""            c.style.display = (okC &amp;&amp; okR &amp;&amp; okM &amp;&amp; okP &amp;&amp; okD &amp;&amp; okS) ? '' : 'none';
          });
          updateCount();
        }""",
    """            c.setAttribute('data-dimok', okD ? '1' : '0');
            c.style.display = (okC &amp;&amp; okR &amp;&amp; okM &amp;&amp; okP &amp;&amp; okD &amp;&amp; okS) ? '' : 'none';
          });
          updateCount();
          updateChips();
        }
        // filtres en cascade : chaque rangée ne propose que les valeurs présentes dans les cartes qui passent les autres filtres
        function updateChips(){
          var groups=[['.chip-site',selS,'data-site'],['.chip-mac',selM,'data-machine'],['.chip-cli',selC,'data-client'],['.chip-ref',selR,'data-ref'],['.chip-pal',selP,'data-palette']];
          var cards=Array.prototype.slice.call(document.querySelectorAll('.vo-card'));
          groups.forEach(function(g){
            var present={};
            cards.forEach(function(c){
              var ok=c.getAttribute('data-dimok')!=='0';
              groups.forEach(function(h){ if(h===g || !ok){ return; } var ks=Object.keys(h[1]); if(ks.length &amp;&amp; !h[1][c.getAttribute(h[2])||'']){ ok=false; } });
              if(ok){ present[c.getAttribute(g[2])||'']=1; }
            });
            var any=false, row=null;
            document.querySelectorAll(g[0]).forEach(function(ch){ var v=ch.getAttribute('data-val'); var show=!!(present[v]||g[1][v]); ch.style.display=show?'':'none'; if(show){ any=true; } row=row||ch.closest('.vo-chips'); });
            if(row){ row.style.display=any?'':'none'; }
          });
        }""")

ET.fromstring(s.encode('utf-8'))
# syntaxe JS du script (après désencodage XML)
m = re.search(r'<script>(.*?)</script>', s, re.S)
esprima.parseScript(html.unescape(m.group(1)))
io.open('vue_operateur_v4.xml', 'w', encoding='utf-8', newline='\n').write(s)
print('vue_operateur_v4.xml OK :', len(s), 'car.')
