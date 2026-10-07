# -*- coding: utf-8 -*-
"""Phase 4, pages Odoo : écran /expedition (départs sur 10 jours, statut livré, bouton « Marquer livré », annulation d'une
livraison) et page Suivi devis/commande (vue 7884 : ligne « 📦 palettes : en stock / parties / livrées »).
  python patch_pages_livraison.py            -> patche expedition_setup.py et prépare vue_7884.AFTER_livraison.xml
  python patch_pages_livraison.py apply      -> idem + écrit la vue 7884 dans Odoo (si inchangée depuis la sauvegarde)"""
import io, os, sys, ssl, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
ecrire = lambda p, s: io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep(s, old, new, n=1, nom=''):
    assert s.count(old) == n, 'ancre %s : %d (attendu %d) %r' % (nom, s.count(old), n, old[:80])
    return s.replace(old, new)


# ── expedition_setup.py (gabarit + JS de /expedition) ──
p = os.path.join(HERE, 'expedition_setup.py'); s = lire(p)
if "web('livrer'" in s:
    print('expedition_setup.py : déjà patché')
else:
    s = rep(s, "    web('lots', {jours: 3}).then(function(r){", "    web('lots', {jours: 10}).then(function(r){", nom='jours')
    s = rep(s, "      if(!lots.length){ box.innerHTML = '<div class=\"exp-empty\">Aucun départ ces 3 derniers jours.</div>'; return; }",
            "      if(!lots.length){ box.innerHTML = '<div class=\"exp-empty\">Aucun départ ces 10 derniers jours.</div>'; return; }", nom='vide')
    s = rep(s, """        return '<div class="exp-lot"><b>' + esc(l.lot) + '</b> · ' + esc(l.date) + ' · ' + esc(MODES[l.mode] || l.mode) + (l.qui ? ' · ' + esc(l.qui) : '') + ' · ' + l.n + ' palette(s) · ' + l.ton + ' kg' + (l.clients ? ' · ' + esc(l.clients) : '')
          + '<div class="pals">' + l.palettes.map(function(p){ return esc(p.name) + ' <button type="button" class="exp-btn red exp-annul" style="padding:3px 8px;font-size:12px;" data-id="' + p.id + '" data-name="' + esc(p.name) + '">↩️ annuler</button>'; }).join(' · ') + '</div>'
          + '<button type="button" class="exp-btn sec exp-reprint" data-lot="' + esc(l.lot) + '">🖨 Liste de chargement</button></div>';""",
            """        var livrees = (l.livrees || 0), reste = l.palettes.filter(function(p){ return p.statut !== 'livree'; }).length;
        var etat = livrees === l.n ? '<span style="color:#5eead4;">📍 livré' + (l.palettes[0].livraison ? ' le ' + esc(l.palettes[0].livraison) : '') + '</span>' : (livrees ? '<span style="color:#fbbf24;">📍 ' + livrees + '/' + l.n + ' livrée(s)</span>' : (l.mode === 'client' ? '<span style="color:#5eead4;">🤝 enlevé par le client</span>' : '<span style="color:#fbbf24;">🚚 en cours de livraison</span>'));
        return '<div class="exp-lot"><b>' + esc(l.lot) + '</b> · ' + esc(l.date) + ' · ' + esc(MODES[l.mode] || l.mode) + (l.qui ? ' · ' + esc(l.qui) : '') + ' · ' + l.n + ' palette(s) · ' + l.ton + ' kg' + (l.clients ? ' · ' + esc(l.clients) : '') + ' · ' + etat
          + '<div class="pals">' + l.palettes.map(function(p){ return esc(p.name) + (p.statut === 'livree' ? ' ✓' : '') + ' <button type="button" class="exp-btn red exp-annul" style="padding:3px 8px;font-size:12px;" data-id="' + p.id + '" data-name="' + esc(p.name) + '" data-statut="' + esc(p.statut) + '">' + (p.statut === 'livree' ? '↩️ annuler la livraison' : '↩️ annuler le départ') + '</button>'; }).join(' · ') + '</div>'
          + '<button type="button" class="exp-btn sec exp-reprint" data-lot="' + esc(l.lot) + '">🖨 Liste de chargement</button>'
          + (reste && l.mode !== 'client' ? '<button type="button" class="exp-btn exp-livrer" style="background:#0e7490;" data-lot="' + esc(l.lot) + '" data-n="' + reste + '">📍 Marquer livré (' + reste + ')</button>' : '') + '</div>';""", nom='rendu lot')
    s = rep(s, """      box.querySelectorAll('.exp-annul').forEach(function(b){ b.onclick = function(){
        if(!confirm('Annuler le départ de ' + b.getAttribute('data-name') + ' ? La palette redevient « en stock ».')){ return; }""",
            """      box.querySelectorAll('.exp-livrer').forEach(function(b){ b.onclick = function(){
        if(!confirm('Marquer les ' + b.getAttribute('data-n') + ' palette(s) du chargement ' + b.getAttribute('data-lot') + ' comme livrées aujourd\\'hui ?')){ return; }
        web('livrer', {lot: b.getAttribute('data-lot'), source: 'expedition'}).then(function(r){ setRes(r.msg || '📍 livré', 'ok'); chargerLots(); }).catch(function(e){ setRes('⚠️ ' + (e && e.message ? e.message : e), 'err'); });
      }; });
      box.querySelectorAll('.exp-annul').forEach(function(b){ b.onclick = function(){
        var livree = b.getAttribute('data-statut') === 'livree';
        if(!confirm(livree ? ('Annuler la livraison de ' + b.getAttribute('data-name') + ' ? La palette redevient « chargée ».') : ('Annuler le départ de ' + b.getAttribute('data-name') + ' ? La palette redevient « en stock ».'))){ return; }""", nom='boutons lot')
    s = rep(s, '<div class="exp-lbl">Départs des 3 derniers jours', '<div class="exp-lbl">Départs des 10 derniers jours', nom='titre lots')
    ecrire(p, s); print('expedition_setup.py : départs 10 jours, statut livré, bouton Marquer livré, annulation de livraison')

# ── vue 7884 Suivi devis/commande : ligne palettes ──
src = os.path.join(HERE, 'vue_7884.BEFORE_livraison.xml'); dst = os.path.join(HERE, 'vue_7884.AFTER_livraison.xml')
a = lire(src)
SNIP = """<span class="sdc-amt"><t t-esc="'%.0f' % so.amount_total"/>€</span>
</div>
<t t-set="so_pals" t-value="request.env['stock.package'].sudo().search([('x_commande_id', '=', so.id), ('x_studio_cloturee', '=', True)])"/>
<t t-if="so_pals"><t t-set="so_last" t-value="so_pals.filtered(lambda pp: pp.x_exp_date).sorted(key=lambda pp: pp.x_exp_date, reverse=True)[:1]"/><div class="sdc-meta" style="color:#0e7490;font-weight:700;">📦 <t t-esc="len(so_pals)"/> palette(s) : <t t-esc="len(so_pals.filtered(lambda pp: not pp.x_exp_statut or pp.x_exp_statut == 'stock'))"/> en stock · <t t-esc="len(so_pals.filtered(lambda pp: pp.x_exp_statut in ('chargee', 'enlevee')))"/> partie(s) · <t t-esc="len(so_pals.filtered(lambda pp: pp.x_exp_statut == 'livree'))"/> livrée(s)<t t-if="so_last"> · dernier départ <span t-field="so_last.x_exp_date" t-options="{'widget': 'date'}"/><t t-if="so_last.x_exp_transporteur_id"> (<t t-esc="so_last.x_exp_transporteur_id.name"/>)</t><t t-elif="so_last.x_exp_camion"> (<t t-esc="so_last.x_exp_camion"/>)</t></t></div></t>"""
import re as _re
RX = _re.compile(r'(<span class="sdc-amt"><t t-esc="\'%\.0f\' % so\.amount_total"/>€</span>\s*</div>)')
if 'so_pals' in a:
    print('vue 7884 : déjà patchée (fichier)')
else:
    n = len(RX.findall(a))
    assert n == 3, 'cartes commande trouvées : %d (attendu 3)' % n
    a = RX.sub(lambda mo: mo.group(1) + '\n' + SNIP.split('</div>\n', 1)[1], a)
    ecrire(dst, a); print('vue_7884.AFTER_livraison.xml : 3 cartes enrichies')
if len(sys.argv) > 1 and sys.argv[1] == 'apply':
    U, D = 'https://maquignon.odoo.com', 'maquignon'
    us = os.environ['ODOO_USER']; pw = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, pw, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    x = lambda mo, me, *ar, **k: m.execute_kw(D, uid, pw, mo, me, list(ar), dict(k, context={'allowed_company_ids': [1]}))
    live = x('ir.ui.view', 'read', [7884], ['arch_db'])[0]['arch_db'].replace('\r\n', '\n')
    before = lire(src); after = lire(dst)
    if live == after:
        print('vue 7884 : déjà en ligne')
    elif live != before:
        print('vue 7884 : modifiée en ligne depuis la sauvegarde, rien écrit')
    else:
        x('ir.ui.view', 'write', [7884], {'arch_db': after})
        print('vue 7884 écrite ; relecture identique :', x('ir.ui.view', 'read', [7884], ['arch_db'])[0]['arch_db'].replace('\r\n', '\n') == after)
