/* Odoo Chatter Manager — popup de réglages */

const DEFAULTS = {
  fullwidth: true,
  chatter: "side",
  chatterWidth: 35,
  fab: true,
};

const extpay = ExtPay(OCX_EXTPAY_ID);

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
  await chrome.storage.local.set(patch);
}

chrome.storage.local.get(DEFAULTS, (s) => {
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

/* ---------- Premium (ExtensionPay) ---------- */

const $badge = document.getElementById("premium-badge");
const $premiumBox = document.getElementById("premium-box");
const $premiumText = document.getElementById("premium-text");
const $btnPay = document.getElementById("btn-pay");
const $btnTrial = document.getElementById("btn-trial");
const $btnLogin = document.getElementById("btn-login");
const $trialInfo = document.getElementById("trial-info");

$btnPay.addEventListener("click", () => extpay.openPaymentPage());
$btnTrial.addEventListener("click", () => extpay.openTrialPage("7 jours"));
$btnLogin.addEventListener("click", () => extpay.openLoginPage());

const $widthHint = document.getElementById("width-premium-hint");

function refreshPremiumUI(status) {
  const premium = !!(status && status.premium);
  isPremium = premium;
  $fullwidth.disabled = !premium;
  $badge.hidden = premium;
  $premiumBox.hidden = premium;
  $widthHint.hidden = premium;
  $width.min = premium ? 5 : 20;

  if (!premium) {
    $fullwidth.checked = false;
    if (Number($width.value) < 20) {
      $width.value = 20;
      $widthValue.textContent = 20;
    }
    if (status && status.trialStartedAt && !status.trialActive) {
      // Essai déjà consommé
      $btnTrial.hidden = true;
      $premiumText.innerHTML =
        "Essai gratuit terminé — débloquez les fonctions <strong>Premium</strong> :";
    }
    return;
  }

  // Premium via essai en cours : afficher le temps restant
  if (status.trialActive && !status.paid) {
    const days = Math.max(
      1,
      Math.ceil(
        (status.trialStartedAt + OCX_TRIAL_MS - Date.now()) / 86400000
      )
    );
    $trialInfo.textContent = `Essai gratuit : ${days} jour${days > 1 ? "s" : ""} restant${days > 1 ? "s" : ""}.`;
    $trialInfo.hidden = false;
  }
}

chrome.runtime.sendMessage({ type: "ocx-get-status" }, (status) => {
  if (chrome.runtime.lastError) return;
  refreshPremiumUI(status);
  // Recharger l'état réel de la case une fois le statut connu
  if (status && status.premium) {
    chrome.storage.local.get(DEFAULTS, (s) => {
      $fullwidth.checked = s.fullwidth;
    });
  }
});

$fab.addEventListener("change", () => save({ fab: $fab.checked }));

let isPremium = false;

$width.addEventListener("input", () => {
  $widthValue.textContent = $width.value;
});
$width.addEventListener("change", () => {
  let value = Number($width.value);
  if (!isPremium && value < 20) {
    // Chatter ultra-fin (< 20 %) : fonction Premium
    value = 20;
    $width.value = 20;
    $widthValue.textContent = 20;
    extpay.openPaymentPage();
  }
  save({ chatterWidth: value });
});

for (const r of radios()) {
  r.addEventListener("change", () => {
    if (r.checked) {
      refreshWidthRow(r.value);
      save({ chatter: r.value });
    }
  });
}
