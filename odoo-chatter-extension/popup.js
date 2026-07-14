/* Odoo Chatter Manager — popup de réglages */

const DEFAULTS = {
  fullwidth: true,
  chatter: "side",
  chatterWidth: 35,
  fab: true,
};

const $fullwidth = document.getElementById("fullwidth");
const $fab = document.getElementById("fab");
const $width = document.getElementById("chatterWidth");
const $widthValue = document.getElementById("width-value");
const $widthRow = document.getElementById("width-row");

function radios() {
  return Array.from(document.querySelectorAll('input[name="chatter"]'));
}

function refreshWidthRow(chatter) {
  $widthRow.classList.toggle("disabled", chatter !== "side");
}

async function save(patch) {
  // Les scripts de contenu écoutent chrome.storage.onChanged :
  // l'application est immédiate dans tous les onglets Odoo ouverts.
  await chrome.storage.sync.set(patch);
}

chrome.storage.sync.get(DEFAULTS, (s) => {
  $fullwidth.checked = s.fullwidth;
  $fab.checked = s.fab;
  $width.value = s.chatterWidth;
  $widthValue.textContent = s.chatterWidth;
  for (const r of radios()) r.checked = r.value === s.chatter;
  refreshWidthRow(s.chatter);
});

$fullwidth.addEventListener("change", () =>
  save({ fullwidth: $fullwidth.checked })
);

$fab.addEventListener("change", () => save({ fab: $fab.checked }));

$width.addEventListener("input", () => {
  $widthValue.textContent = $width.value;
});
$width.addEventListener("change", () =>
  save({ chatterWidth: Number($width.value) })
);

for (const r of radios()) {
  r.addEventListener("change", () => {
    if (r.checked) {
      refreshWidthRow(r.value);
      save({ chatter: r.value });
    }
  });
}
