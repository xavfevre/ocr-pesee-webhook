/* Odoo Chatter Manager — configuration de la monétisation.
 *
 * OCX_EXTPAY_ID doit correspondre à l'identifiant de l'extension déclaré
 * sur https://extensionpay.com (compte gratuit, paiements via Stripe).
 * Voir la section « Monétisation » du README pour la mise en route.
 */
const OCX_EXTPAY_ID = "odoo-chatter-manager";

/* Durée de l'essai gratuit de la fonction Premium (pleine largeur). */
const OCX_TRIAL_MS = 7 * 24 * 60 * 60 * 1000; // 7 jours
