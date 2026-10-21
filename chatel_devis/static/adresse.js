/* Autocomplétion d'adresse (Base Adresse Nationale, api-adresse.data.gouv.fr) + distance depuis Le Pautron. */
(function () {
  var BASE = document.documentElement.dataset.base || '/devis';
  var DEPART = [46.7798, 0.5483];

  function lireStock(k) { try { return JSON.parse(sessionStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function ecrireStock(k, v) { try { sessionStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  /* champ : <input>, boite : <div class="suggestions">, info : élément pour « 23 km », rappel(adresse) */
  window.Adresse = function (champ, boite, info, rappel) {
    var minuteur = null, liste = [], sel = -1, req = 0;
    function fermer() { boite.classList.remove('ouvert'); boite.innerHTML = ''; sel = -1; }
    function choisir(f) {
      var p = f.properties, a = {
        label: p.label, rue: p.name, cp: p.postcode, ville: p.city,
        lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1]
      };
      champ.value = p.label; fermer();
      if (info) { info.textContent = 'Calcul de la distance…'; info.classList.remove('hors'); }
      fetch(BASE + '/api/distance?lat=' + a.lat + '&lon=' + a.lon).then(function (r) { return r.json(); }).then(function (d) {
        a.km = d.km; a.dans_zone = d.dans_zone;
        ecrireStock('cg_adresse', a);
        if (info) {
          info.textContent = d.dans_zone ? ('✓ ' + Math.round(d.km) + ' km de notre carrière du Pautron')
            : ('⚠ ' + Math.round(d.km) + ' km : hors de notre zone de livraison habituelle, nous vous rappelons pour un prix.');
          info.classList.toggle('hors', !d.dans_zone);
        }
        rappel && rappel(a);
      }).catch(function () { if (info) info.textContent = 'Distance indisponible, nous la vérifierons.'; a.km = null; rappel && rappel(a); });
    }
    function afficher() {
      boite.innerHTML = '';
      liste.forEach(function (f, i) {
        var b = document.createElement('button'); b.type = 'button'; b.textContent = f.properties.label;
        if (i === sel) b.className = 'sel';
        b.addEventListener('mousedown', function (e) { e.preventDefault(); choisir(f); });
        boite.appendChild(b);
      });
      boite.classList.toggle('ouvert', liste.length > 0);
    }
    champ.setAttribute('autocomplete', 'off');
    champ.addEventListener('input', function () {
      clearTimeout(minuteur);
      var q = champ.value.trim();
      if (q.length < 4) { fermer(); return; }
      minuteur = setTimeout(function () {
        var n = ++req;
        fetch('https://api-adresse.data.gouv.fr/search/?limit=5&autocomplete=1&lat=' + DEPART[0] + '&lon=' + DEPART[1] + '&q=' + encodeURIComponent(q))
          .then(function (r) { return r.json(); }).then(function (j) {
            if (n !== req) return;
            liste = j.features || []; sel = -1; afficher();
          }).catch(fermer);
      }, 180);
    });
    champ.addEventListener('keydown', function (e) {
      if (!boite.classList.contains('ouvert')) return;
      if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, liste.length - 1); afficher(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); afficher(); e.preventDefault(); }
      else if (e.key === 'Enter' && liste.length) { choisir(liste[Math.max(sel, 0)]); e.preventDefault(); }
      else if (e.key === 'Escape') fermer();
    });
    champ.addEventListener('blur', function () { setTimeout(fermer, 150); });
    var a = lireStock('cg_adresse');
    if (a && a.label && !champ.value) {
      champ.value = a.label;
      if (info && a.km != null) {
        info.textContent = a.dans_zone ? ('✓ ' + Math.round(a.km) + ' km de notre carrière du Pautron') : ('⚠ ' + Math.round(a.km) + ' km : hors zone habituelle');
        info.classList.toggle('hors', !a.dans_zone);
      }
    }
    return { adresse: function () { return lireStock('cg_adresse'); } };
  };
  window.cgStock = { lire: lireStock, ecrire: ecrireStock };
})();
