/* Parcours de devis Chatel'Granulats : 1 service + adresse, 2 produit, 3 quantité / camion / date, 4 récapitulatif. */
(function () {
  var B = CG.base, $ = function (id) { return document.getElementById(id); };
  var NOMS = { livraison: 'Livraison de granulats', evacuation: 'Évacuation de déblais', affretement: 'Affrètement de camion', benne: 'Location de benne' };
  var JOURS = ['dim.', 'lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.'];
  var S = cgStock.lire('cg_parcours') || {};
  S.unite = S.unite || 't'; S.duree = S.duree || 'jour'; S.nb = S.nb || 1; S.vue = S.vue || 'liste';
  S.camionManuel = false;
  var D = null, etape = 1, chargement = null;

  var q = new URLSearchParams(location.search);
  if (q.get('service') && NOMS[q.get('service')]) { if (S.service !== q.get('service')) { S.produit = null; } S.service = q.get('service'); }
  if (q.get('famille')) S.famille = q.get('famille');
  if (q.get('produit')) S.produit = +q.get('produit');
  S.adresse = cgStock.lire('cg_adresse') || S.adresse || null;

  function sauver() { cgStock.ecrire('cg_parcours', S); }
  function eur(v, dec) { return v == null ? '—' : v.toLocaleString('fr-FR', { minimumFractionDigits: dec == null ? 2 : dec, maximumFractionDigits: dec == null ? 2 : dec }) + ' €'; }
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function km() { return S.adresse && S.adresse.km != null ? S.adresse.km : null; }
  function produit() { return D && S.produit ? D.produits.filter(function (p) { return p.id === S.produit; })[0] : null; }
  function tonnes() {
    var v = parseFloat(S.qte); if (!(v > 0)) return 0;
    if (S.unite === 'm3') { var p = produit(); return Math.round(v * (S.service === 'evacuation' ? 1.6 : (p ? p.densite : 1.5)) * 10) / 10; }
    return v;
  }
  function transportT(k) { return k.fixe_t + k.eur_km_t * Math.max(km() || 0, D.km_mini || 0); }
  function conseille(t) {
    var ks = D.camions.slice().sort(function (a, b) { return a.charge - b.charge; });
    for (var i = 0; i < ks.length; i++) if (ks[i].charge >= t) return ks[i];
    return ks[ks.length - 1];
  }

  /* ------------------------------------------------ données */
  function charger() {
    var k = km();
    var url = B + '/api/catalogue' + (k != null ? '?km=' + k : '');
    chargement = fetch(url).then(function (r) { return r.json(); }).then(function (j) { D = j; return j; });
    return chargement;
  }

  /* ------------------------------------------------ navigation */
  function aller(n) {
    etape = n;
    for (var i = 1; i <= 5; i++) $('e' + i).hidden = i !== n;
    document.querySelectorAll('#stepper li').forEach(function (li) {
      var e = +li.dataset.e; li.classList.toggle('actif', e === n); li.classList.toggle('fait', e < n && n < 5);
    });
    $('lib-e2').textContent = { livraison: 'Produit', evacuation: 'Déblais', affretement: 'Camion', benne: 'Benne' }[S.service] || 'Produit';
    $('lib-e3').textContent = (S.service === 'affretement' || S.service === 'benne') ? 'Durée' : 'Volume';
    if (n === 2) rendreE2();
    if (n === 3) rendreE3();
    if (n === 4) rendreE4();
    resume(); sauver();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    try { history.replaceState(null, '', '?service=' + (S.service || '') + '#etape' + n); } catch (e) {}
  }
  document.querySelectorAll('#stepper li').forEach(function (li) {
    li.addEventListener('click', function () { if (li.classList.contains('fait')) aller(+li.dataset.e); });
  });
  document.querySelectorAll('[data-retour]').forEach(function (b) { b.addEventListener('click', function () { aller(+b.dataset.retour); }); });

  /* ------------------------------------------------ étape 1 */
  function majE1() {
    document.querySelectorAll('#services .choix').forEach(function (b) { b.classList.toggle('on', b.dataset.s === S.service); });
    $('go1').disabled = !(S.service && S.adresse && S.adresse.lat);
  }
  document.querySelectorAll('#services .choix').forEach(function (b) {
    b.addEventListener('click', function () {
      if (S.service !== b.dataset.s) { S.produit = null; S.camion = null; S.benne = null; S.deblais = null; }
      S.service = b.dataset.s; majE1(); resume(); sauver();
      if (!(S.adresse && S.adresse.lat)) $('adresse').focus();
    });
  });
  Adresse($('adresse'), $('sugg'), $('km'), function (a) { S.adresse = a; majE1(); resume(); sauver(); charger(); });
  $('go1').addEventListener('click', function () { (chargement || charger()).then(function () { aller(2); }); });

  /* ------------------------------------------------ étape 2 */
  function rendreE2() {
    ['livraison', 'evacuation', 'affretement', 'benne'].forEach(function (s) { $('e2-' + s).hidden = s !== S.service; });
    if (!D) { (chargement || charger()).then(rendreE2); return; }
    if (S.service === 'livraison') rendreCatalogue();
    if (S.service === 'evacuation') rendreChoix('deblais', D.deblais.map(function (d) { return { code: d, nom: d, sous: 'Reprise ' + eur(D.evacuation ? D.evacuation.prix_t : null) + ' HT/t + transport' }; }), 'deblais');
    if (S.service === 'affretement') rendreChoix('affr', D.affretement.map(function (a) {
      return { code: a.code, nom: a.nom, sous: a.jour ? ('Journée ' + eur(a.jour, 0) + ' HT' + (a.demi ? ' · demi ' + eur(a.demi, 0) : '')) : 'Prix sur devis' };
    }), 'camion');
    if (S.service === 'benne') rendreChoix('bennes', D.bennes.map(function (b) {
      return { code: b.code, nom: b.nom, sous: b.prix ? ('Pose + enlèvement ' + eur(b.prix, 0) + ' HT') : 'Prix sur devis' };
    }), 'benne');
    majGo2();
  }
  function rendreChoix(id, items, champ) {
    $(id).innerHTML = items.map(function (it) {
      return '<button type="button" class="choix' + (S[champ] === it.code ? ' on' : '') + '" data-c="' + esc(it.code) + '"><b>' + esc(it.nom) + '</b><small>' + esc(it.sous) + '</small></button>';
    }).join('');
    $(id).querySelectorAll('.choix').forEach(function (b) {
      b.addEventListener('click', function () { S[champ] = b.dataset.c; rendreE2(); resume(); sauver(); setTimeout(function () { aller(3); }, 150); });
    });
  }
  function vignette(p) {
    if (p.img) return '<img loading="lazy" alt="' + esc(p.nom) + '" src="' + CG.img + p.tmpl + '">';
    var d = (D.deco || {})[p.famille] || ['🪨', '#E3DED6'];
    return '<div class="ph" style="background:' + d[1] + '" aria-hidden="true">' + d[0] + '</div>';
  }
  function filtres() {
    var r = (S.recherche || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
    return D.produits.filter(function (p) {
      if (S.famille && S.famille !== 'Tous' && p.famille !== S.famille) return false;
      if (S.usage && p.usages.indexOf(S.usage) < 0) return false;
      if (r) { var n = (p.nom + ' ' + p.famille).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); if (r.split(/\s+/).some(function (m) { return n.indexOf(m) < 0; })) return false; }
      return true;
    });
  }
  function rendreCatalogue() {
    var nb = {}; D.produits.forEach(function (p) { nb[p.famille] = (nb[p.famille] || 0) + 1; });
    var fams = ['Tous'].concat(D.familles.filter(function (f) { return nb[f]; }), Object.keys(nb).filter(function (f) { return D.familles.indexOf(f) < 0; }));
    if (S.famille && !nb[S.famille]) S.famille = 'Tous';
    $('familles').innerHTML = fams.map(function (f) {
      return '<button type="button" data-f="' + esc(f) + '" class="' + ((S.famille || 'Tous') === f ? 'on' : '') + '">' + esc(f) + ' <small>' + (f === 'Tous' ? D.produits.length : nb[f]) + '</small></button>';
    }).join('');
    $('familles').querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { S.famille = b.dataset.f; rendreCatalogue(); sauver(); }); });
    var us = D.usages.filter(function (u) { return D.produits.some(function (p) { return p.usages.indexOf(u) >= 0; }); });
    $('usages').innerHTML = us.map(function (u) { return '<button type="button" class="' + (S.usage === u ? 'on' : '') + '" data-u="' + esc(u) + '">' + esc(u) + '</button>'; }).join('');
    $('usages').querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { S.usage = S.usage === b.dataset.u ? null : b.dataset.u; rendreCatalogue(); sauver(); }); });
    document.querySelectorAll('.vue [data-v]').forEach(function (b) { b.classList.toggle('on', b.dataset.v === S.vue); });
    $('produits').className = 'produits ' + S.vue;
    var ps = filtres();
    $('produits').innerHTML = ps.length ? ps.map(function (p) {
      var prix = p.min != null ? ('<b>' + (p.min === p.max ? 'dès ' + p.min + ' €' : p.min + ' € – ' + p.max + ' €') + '</b><small>HT/T · prix livré</small>')
        : ('<b>' + eur(p.prix_t) + '</b><small>HT/T départ carrière</small>');
      return '<button type="button" class="prod' + (S.produit === p.id ? ' on' : '') + '" data-p="' + p.id + '">' +
        vignette(p) +
        '<div><div class="nom">' + esc(p.nom) + (p.declasse ? '<span class="declasse">Déclassé</span>' : '') + '</div><div class="fam">' + esc(p.famille) + (p.usages.length ? ' · ' + esc(p.usages.slice(0, 2).join(', ')) : '') + '</div></div>' +
        '<div class="px">' + prix + '</div></button>';
    }).join('') : '<div class="vide">Aucun produit ne correspond. Essayez une autre famille ou appelez-nous.</div>';
    $('produits').querySelectorAll('.prod').forEach(function (b) {
      b.addEventListener('click', function () { S.produit = +b.dataset.p; S.camionManuel = false; sauver(); resume(); b.classList.add('on'); setTimeout(function () { aller(3); }, 150); });
    });
    $('cat-maj').textContent = 'Prix HT par tonne, mis à jour le ' + D.maj + (km() != null ? ' · livraison à ' + Math.round(km()) + ' km' : '') + '.';
  }
  $('recherche').addEventListener('input', function () { S.recherche = this.value; rendreCatalogue(); });
  document.querySelectorAll('.vue [data-v]').forEach(function (b) { b.addEventListener('click', function () { S.vue = b.dataset.v; rendreCatalogue(); sauver(); }); });
  function majGo2() {
    $('go2').disabled = !({ livraison: S.produit, evacuation: S.deblais, affretement: S.camion, benne: S.benne }[S.service]);
  }
  $('go2').addEventListener('click', function () { aller(3); });

  /* ------------------------------------------------ étape 3 */
  function rendreE3() {
    var tonnage = S.service === 'livraison' || S.service === 'evacuation';
    $('bloc-qte').hidden = !tonnage; $('bloc-duree').hidden = tonnage;
    $('l-duree').hidden = S.service !== 'affretement';
    $('l-nb').textContent = S.service === 'benne' ? 'Nombre de jours de location' : 'Nombre (jours ou demi-journées)';
    $('h-e3').textContent = tonnage ? 'Quantité, camion et date' : 'Durée et date';
    $('h-date').textContent = S.service === 'evacuation' ? "Date d'enlèvement" : (S.service === 'benne' ? 'Date de pose' : (S.service === 'affretement' ? 'Date' : 'Date de livraison'));
    $('qte').value = S.qte || ''; $('duree').value = S.duree; $('nb').value = S.nb;
    document.querySelectorAll('.qte-saisie [data-u]').forEach(function (b) { b.classList.toggle('on', b.dataset.u === S.unite); });
    if (S.date && D.dates.indexOf(S.date) < 0) S.date = null;
    $('dates').innerHTML = D.dates.map(function (d) {
      var j = new Date(d + 'T12:00:00');
      return '<button type="button" data-d="' + d + '" class="' + (S.date === d ? 'on' : '') + '">' + JOURS[j.getDay()] + '<b>' + j.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) + '</b></button>';
    }).join('');
    $('dates').querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { S.date = b.dataset.d; rendreE3(); resume(); sauver(); }); });
    $('creneaux').innerHTML = D.creneaux.map(function (c) { return '<button type="button" data-c="' + esc(c) + '" class="' + (S.creneau === c ? 'on' : '') + '"><b>' + esc(c) + '</b></button>'; }).join('');
    $('creneaux').querySelectorAll('button').forEach(function (b) { b.addEventListener('click', function () { S.creneau = b.dataset.c; rendreE3(); resume(); sauver(); }); });
    if (tonnage) rendreCamions();
    majGo3();
  }
  function rendreCamions() {
    var t = tonnes();
    var p = produit();
    $('rapides').innerHTML = [2, 5, 8, 13, 17, 28].map(function (v) {
      return '<button type="button" class="' + (S.unite === 't' && parseFloat(S.qte) === v ? 'on' : '') + '" data-v="' + v + '">' + v + ' t</button>';
    }).join('');
    $('rapides').querySelectorAll('button').forEach(function (b) {
      b.addEventListener('click', function () { S.qte = +b.dataset.v; S.unite = 't'; S.camionManuel = false; $('qte').value = S.qte;
        document.querySelectorAll('.qte-saisie [data-u]').forEach(function (x) { x.classList.toggle('on', x.dataset.u === 't'); });
        rendreCamions(); resume(); sauver(); majGo3(); });
    });
    $('conv').textContent = t > 0 ? (S.unite === 'm3' ? '≈ ' + t.toLocaleString('fr-FR') + ' t (densité ' + (S.service === 'evacuation' ? 1.6 : (p ? p.densite : 1.5)).toLocaleString('fr-FR') + ')' : '') : '';
    var c = t > 0 ? conseille(t) : null;
    if (c && !S.camionManuel) S.camion = c.code;
    $('camions').innerHTML = D.camions.map(function (k) {
      var tours = t > 0 ? Math.ceil(t / k.charge) : 1;
      var mini = t > 0 && t < k.mini_t ? '<small>Minimum ' + k.mini_t + ' t facturées en transport</small>' : '';
      return '<button type="button" class="choix' + (S.camion === k.code ? ' on' : '') + '" data-k="' + k.code + '"><b>' + esc(k.nom) + '</b>' +
        (c && c.code === k.code ? '<span class="tag">Conseillé</span>' : '') +
        '<small>Charge utile ' + k.charge + ' t' + (t > 0 ? ' · ' + tours + ' tour' + (tours > 1 ? 's' : '') : '') + '</small>' + mini +
        (km() != null ? '<span class="prix">Transport ≈ ' + eur(transportT(k)) + ' HT/t</span>' : '') + '</button>';
    }).join('');
    $('camions').querySelectorAll('.choix').forEach(function (b) {
      b.addEventListener('click', function () { S.camion = b.dataset.k; S.camionManuel = true; rendreCamions(); resume(); sauver(); majGo3(); });
    });
  }
  $('qte').addEventListener('input', function () { S.qte = this.value; rendreCamions(); resume(); sauver(); majGo3(); });
  document.querySelectorAll('.qte-saisie [data-u]').forEach(function (b) {
    b.addEventListener('click', function () { S.unite = b.dataset.u; document.querySelectorAll('.qte-saisie [data-u]').forEach(function (x) { x.classList.toggle('on', x === b); }); rendreCamions(); resume(); sauver(); });
  });
  $('duree').addEventListener('change', function () { S.duree = this.value; resume(); sauver(); });
  $('nb').addEventListener('input', function () { S.nb = Math.max(1, parseInt(this.value, 10) || 1); resume(); sauver(); });
  function calc() {
    var l = parseFloat($('c-l').value), w = parseFloat($('c-w').value), e = parseFloat($('c-e').value);
    if (!(l > 0 && w > 0 && e > 0)) { $('c-res').textContent = ''; return null; }
    var m3 = l * w * e / 100, p = produit(), d = S.service === 'evacuation' ? 1.6 : (p ? p.densite : 1.5);
    var t = Math.ceil(m3 * d * 2) / 2;
    $('c-res').textContent = (l * w).toLocaleString('fr-FR') + ' m² × ' + e + ' cm = ' + m3.toLocaleString('fr-FR', { maximumFractionDigits: 2 }) + ' m³ ≈ ' + t.toLocaleString('fr-FR') + ' t';
    return t;
  }
  ['c-l', 'c-w', 'c-e'].forEach(function (id) { $(id).addEventListener('input', calc); });
  $('c-ok').addEventListener('click', function () {
    var t = calc(); if (!t) return;
    S.qte = t; S.unite = 't'; S.camionManuel = false; rendreE3(); resume(); sauver();
    document.querySelector('details.calc').open = false;
  });
  function majGo3() {
    var ok = S.date && S.creneau;
    if (S.service === 'livraison' || S.service === 'evacuation') ok = ok && tonnes() > 0 && S.camion;
    $('go3').disabled = !ok;
  }
  $('go3').addEventListener('click', function () { aller(4); });

  /* ------------------------------------------------ étape 4 */
  function demande() {
    return { service: S.service, km: km(), produit: S.produit, deblais: S.deblais, tonnes: tonnes(), m3: S.unite === 'm3' ? parseFloat(S.qte) : null,
      camion: S.camion, benne: S.benne, duree: S.duree, nb: S.nb, date: S.date, creneau: S.creneau, adresse: S.adresse };
  }
  function rendreE4() {
    $('recap').innerHTML = '<div class="vide">Calcul de votre prix…</div>';
    fetch(B + '/api/estimer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(demande()) })
      .then(function (r) { return r.json(); }).then(function (e) {
        if (e.erreur) { $('recap').innerHTML = '<div class="message err" style="display:block">' + esc(e.erreur) + '</div>'; return; }
        S.estimation = e; resume();
        var h = '<table class="recap-table"><thead><tr><th>Désignation</th><th>Qté</th><th class="pu">PU HT</th><th>Total HT</th></tr></thead><tbody>';
        e.lignes.forEach(function (l) {
          h += '<tr><td>' + esc(l.nom) + '</td><td>' + l.qte.toLocaleString('fr-FR') + ' ' + esc(l.unite) + '</td><td class="pu">' + eur(l.pu) + '</td><td>' + (l.total == null ? 'sur devis' : eur(l.total)) + '</td></tr>';
        });
        h += '</tbody><tfoot>';
        if (e.ht != null) h += '<tr><td colspan="3">Total HT</td><td>' + eur(e.ht) + '</td></tr><tr><td colspan="3">TVA</td><td>' + eur(e.tva) + '</td></tr><tr class="ttc"><td colspan="3">Total TTC estimé</td><td>' + eur(e.ttc) + '</td></tr>';
        else h += '<tr><td colspan="4">Prix confirmé par notre équipe sous 24 h.</td></tr>';
        h += '</tfoot></table>';
        (e.notes || []).forEach(function (n) { h += '<p class="petit muet" style="margin-top:8px">ℹ ' + esc(n) + '</p>'; });
        if (S.adresse && S.adresse.dans_zone === false) h += '<div class="encart">Votre chantier est hors de notre zone habituelle (' + Math.round(km()) + ' km) : le transport sera confirmé par téléphone.</div>';
        h += '<p class="petit muet" style="margin-top:10px">Estimation indicative, confirmée par Chatel\'Granulats après vérification de l\'accès au chantier et de la disponibilité des camions.</p>';
        $('recap').innerHTML = h;
      }).catch(function () { $('recap').innerHTML = '<div class="message err" style="display:block">Calcul impossible pour le moment. Appelez-nous, nous faisons le devis avec vous.</div>'; });
  }
  $('form-client').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var f = new FormData(this), cl = {};
    f.forEach(function (v, k) { cl[k] = v; });
    var d = demande(); d.client = cl; d.site_web = cl.site_web; d.jeton = CG.jeton;
    var b = $('envoyer'); b.disabled = true; b.textContent = 'Envoi…';
    $('msg').className = 'message';
    fetch(B + '/api/demande', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(d) })
      .then(function (r) { return r.json(); }).then(function (r) {
        if (r.ok) {
          $('numero').textContent = r.numero; S.produit = null; S.qte = null; S.date = null; S.creneau = null; S.estimation = null; sauver(); aller(5);
        } else { $('msg').textContent = r.erreur || 'Envoi impossible.'; $('msg').className = 'message err'; }
      }).catch(function () { $('msg').textContent = 'Envoi impossible, vérifiez votre connexion ou appelez-nous.'; $('msg').className = 'message err'; })
      .then(function () { b.disabled = false; b.textContent = 'Envoyer ma demande de devis'; });
  });

  /* ------------------------------------------------ résumé latéral */
  function resume() {
    var r = [];
    if (S.service) r.push(['Service', NOMS[S.service]]);
    if (S.adresse && S.adresse.label) r.push(['Chantier', S.adresse.label + (km() != null ? ' (' + Math.round(km()) + ' km)' : '')]);
    var p = produit(); if (p && S.service === 'livraison') r.push(['Produit', p.nom]);
    if (S.deblais && S.service === 'evacuation') r.push(['Déblais', S.deblais]);
    if ((S.service === 'livraison' || S.service === 'evacuation') && tonnes() > 0) r.push(['Quantité', tonnes().toLocaleString('fr-FR') + ' t']);
    if (D && S.camion) { var k = D.camions.concat(D.affretement).filter(function (x) { return x.code === S.camion; })[0]; if (k) r.push(['Camion', k.nom]); }
    if (D && S.benne && S.service === 'benne') { var bb = D.bennes.filter(function (x) { return x.code === S.benne; })[0]; if (bb) r.push(['Benne', bb.nom]); }
    if (S.date) r.push(['Date', new Date(S.date + 'T12:00:00').toLocaleDateString('fr-FR', { weekday: 'short', day: '2-digit', month: '2-digit' }) + (S.creneau ? ' · ' + S.creneau : '')]);
    $('resume-dl').innerHTML = r.map(function (x) { return '<dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd>'; }).join('') || '<dd class="muet" style="grid-column:1/-1">Choisissez un service et votre adresse.</dd>';
    var px = '';
    if (etape >= 4 && S.estimation && S.estimation.ht != null) px = eur(S.estimation.ht) + ' HT';
    else if (p && p.min != null && S.service === 'livraison') px = (p.min === p.max ? p.min : p.min + ' – ' + p.max) + ' € HT/t';
    $('resume-prix').textContent = px;
  }

  /* ------------------------------------------------ démarrage */
  majE1(); resume();
  var depart = 1, h = (location.hash.match(/etape(\d)/) || [])[1];
  if (S.service && S.adresse && S.adresse.lat) {
    depart = 2;
    if (h && +h > 2 && +h < 5) depart = +h;
    if (S.service === 'livraison' && q.get('produit')) depart = 3;
  }
  charger().then(function () {
    if (depart >= 3 && S.service === 'livraison' && !produit()) depart = 2;
    if (depart === 4 && $('go3') && !(S.date && S.creneau)) depart = 3;
    aller(depart);
  }).catch(function () { aller(1); });
})();
