#!/usr/bin/env python3
"""Odoo migration verification tool (V18 -> V19) for maquignon.odoo.com.

This tool introspects an Odoo database over the standard external API
(XML-RPC, the same protocol used by the OCR webhook) and produces a
JSON *snapshot* of the customisations that matter for this project:

  * Studio custom fields (x_studio_*) and other manual fields
  * Computed fields (and whether they are stored)
  * Server actions (ir.actions.server)
  * Automation / automated-action rules (base.automation), if installed
  * Reports (ir.actions.report)
  * Studio / custom views (ir.ui.view with state='manual' or studio arch)

Workflow:

  1. BEFORE the upgrade, snapshot the production V18 database::

         python verify_migration.py snapshot --out snapshot_v18.json

  2. AFTER Odoo provisions the V19 *test* database, snapshot it::

         python verify_migration.py snapshot \
             --url https://maquignon-test.odoo.com \
             --out snapshot_v19.json

  3. Diff the two snapshots to get an objective list of what changed::

         python verify_migration.py compare snapshot_v18.json snapshot_v19.json

The exit code of ``compare`` is non-zero when regressions (missing
fields, actions or reports) are detected, so it can gate a CI check.

Credentials are read from CLI flags or environment variables:
``ODOO_URL``, ``ODOO_DB``, ``ODOO_USER``, ``ODOO_PASSWORD`` (use an
API key as the password on recent SaaS instances).
"""

import argparse
import json
import os
import sys
import xmlrpc.client
from datetime import datetime, timezone
from typing import Any

# Models whose fields the OCR webhook relies on. Override with --models.
DEFAULT_MODELS: list[str] = [
    "x_project_task_worksheet_template_1_line",
    "project.task",
    "sale.order.line",
    "sale.order",
]

# Fields the webhook reads/writes today (app.py). Used to flag critical losses.
WEBHOOK_CRITICAL_FIELDS: dict[str, list[str]] = {
    "x_project_task_worksheet_template_1_line": [
        "x_studio_numero_bon", "x_studio_client_pesee", "x_studio_transporteur",
        "x_studio_produit_pesee", "x_studio_chantier_pesee", "x_studio_vehicule",
        "x_studio_pesee1_poids", "x_studio_pesee1_ticket", "x_studio_pesee2_poids",
        "x_studio_pesee2_ticket", "x_studio_poids_net", "x_studio_date_bon",
        "x_studio_ocr_statut", "x_studio_date", "x_studio_immat_tracteur",
        "x_studio_photo_bon", "x_project_task_id",
    ],
    "project.task": ["sale_line_id"],
    "sale.order.line": ["order_id", "display_type", "sequence", "product_id"],
}


def connect(url: str, db: str, user: str, password: str) -> tuple[Any, int]:
    """Authenticate and return (models_proxy, uid)."""
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise SystemExit(
            "Authentification Odoo echouee. Verifie ODOO_DB / ODOO_USER / "
            "ODOO_PASSWORD (utilise une cle API en SaaS si la 2FA est active)."
        )
    version = common.version()
    print(f"  -> Connecte a {url} (db={db}, uid={uid}, "
          f"serveur={version.get('server_version', '?')})")
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return models, uid


def _search_read(models, db, uid, password, model, domain, fields):
    """Thin wrapper around execute_kw search_read."""
    return models.execute_kw(
        db, uid, password, model, "search_read", [domain], {"fields": fields}
    )


def snapshot_fields(models, db, uid, password, target_models: list[str]) -> dict:
    """Introspect ir.model.fields for the target models."""
    domain = [("model", "in", target_models)]
    fields = ["model", "name", "field_description", "ttype", "relation",
              "compute", "store", "related", "required", "readonly", "state"]
    rows = _search_read(models, db, uid, password, "ir.model.fields", domain, fields)

    result: dict[str, dict] = {}
    for r in rows:
        model = r["model"]
        result.setdefault(model, {})
        result[model][r["name"]] = {
            "label": r.get("field_description"),
            "type": r.get("ttype"),
            "relation": r.get("relation") or None,
            "computed": bool(r.get("compute")),
            "stored": bool(r.get("store")),
            "related": r.get("related") or None,
            "required": bool(r.get("required")),
            "readonly": bool(r.get("readonly")),
            # 'manual' == created via Studio/UI ; 'base' == defined in code
            "manual": r.get("state") == "manual",
        }
    return result


def snapshot_server_actions(models, db, uid, password, target_models) -> list[dict]:
    """List server actions bound to the target models."""
    domain = [("model_name", "in", target_models)]
    fields = ["name", "model_name", "state", "usage"]
    try:
        rows = _search_read(models, db, uid, password,
                            "ir.actions.server", domain, fields)
    except xmlrpc.client.Fault:
        # Older field name fallback
        rows = _search_read(models, db, uid, password, "ir.actions.server",
                            [], ["name", "state"])
    return sorted(rows, key=lambda r: (r.get("model_name", ""), r["name"]))


def snapshot_automations(models, db, uid, password, target_models) -> list[dict]:
    """List automation rules (base.automation) if the module is installed."""
    try:
        rows = _search_read(
            models, db, uid, password, "base.automation",
            [("model_name", "in", target_models)],
            ["name", "model_name", "trigger", "active"],
        )
    except xmlrpc.client.Fault:
        return []  # module base_automation not installed / model differs
    return sorted(rows, key=lambda r: r["name"])


def snapshot_reports(models, db, uid, password, target_models) -> list[dict]:
    """List QWeb/PDF reports bound to the target models."""
    domain = [("model", "in", target_models)]
    fields = ["name", "model", "report_name", "report_type"]
    rows = _search_read(models, db, uid, password,
                        "ir.actions.report", domain, fields)
    return sorted(rows, key=lambda r: (r["model"], r["name"]))


def snapshot_views(models, db, uid, password, target_models) -> list[dict]:
    """List custom/Studio views bound to the target models."""
    domain = [("model", "in", target_models), ("type", "in",
              ["form", "list", "tree", "kanban", "search"])]
    fields = ["name", "model", "type", "inherit_id"]
    rows = _search_read(models, db, uid, password, "ir.ui.view", domain, fields)
    return sorted(rows, key=lambda r: (r["model"], r["type"], r["name"]))


def do_snapshot(args) -> None:
    """Build and write a full snapshot JSON."""
    url = args.url or os.environ.get("ODOO_URL")
    db = args.db or os.environ.get("ODOO_DB")
    user = args.user or os.environ.get("ODOO_USER")
    password = args.password or os.environ.get("ODOO_PASSWORD")
    if not all([url, db, user, password]):
        raise SystemExit("URL / DB / USER / PASSWORD requis (flags ou env vars).")

    target_models = args.models or DEFAULT_MODELS
    print(f"Snapshot de {db} pour les modeles : {', '.join(target_models)}")
    models, uid = connect(url, db, user, password)

    snapshot = {
        "meta": {
            "url": url,
            "db": db,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "models": target_models,
        },
        "fields": snapshot_fields(models, db, uid, password, target_models),
        "server_actions": snapshot_server_actions(models, db, uid, password, target_models),
        "automations": snapshot_automations(models, db, uid, password, target_models),
        "reports": snapshot_reports(models, db, uid, password, target_models),
        "views": snapshot_views(models, db, uid, password, target_models),
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, indent=2)

    n_fields = sum(len(v) for v in snapshot["fields"].values())
    print(f"  -> {n_fields} champs, {len(snapshot['server_actions'])} actions "
          f"serveur, {len(snapshot['automations'])} regles d'automatisation, "
          f"{len(snapshot['reports'])} rapports, {len(snapshot['views'])} vues.")
    print(f"Snapshot ecrit dans {args.out}")


def _diff_fields(old: dict, new: dict) -> tuple[list[str], list[str]]:
    """Return (regressions, warnings) comparing field snapshots."""
    regressions: list[str] = []
    warnings: list[str] = []

    for model, old_fields in old.items():
        new_fields = new.get(model, {})
        if not new_fields:
            regressions.append(f"[MODELE MANQUANT] '{model}' absent en v19 "
                               f"(renommage Studio probable).")
            continue
        for fname, fmeta in old_fields.items():
            critical = fname in WEBHOOK_CRITICAL_FIELDS.get(model, [])
            if fname not in new_fields:
                tag = "CHAMP CRITIQUE MANQUANT" if critical else "champ manquant"
                regressions.append(f"[{tag}] {model}.{fname}")
                continue
            nmeta = new_fields[fname]
            if fmeta["type"] != nmeta["type"]:
                warnings.append(f"[type change] {model}.{fname}: "
                                f"{fmeta['type']} -> {nmeta['type']}")
            if fmeta["computed"] != nmeta["computed"]:
                warnings.append(f"[compute change] {model}.{fname}: "
                                f"computed {fmeta['computed']} -> {nmeta['computed']}")
            if fmeta["stored"] != nmeta["stored"]:
                warnings.append(f"[store change] {model}.{fname}: "
                                f"stored {fmeta['stored']} -> {nmeta['stored']}")
            if fmeta.get("relation") != nmeta.get("relation"):
                warnings.append(f"[relation change] {model}.{fname}: "
                                f"{fmeta.get('relation')} -> {nmeta.get('relation')}")
    return regressions, warnings


def _diff_named(old: list[dict], new: list[dict], key: str,
                label: str) -> list[str]:
    """Compare lists of records keyed by `key`, report disappearances."""
    old_keys = {r.get(key) for r in old}
    new_keys = {r.get(key) for r in new}
    missing = sorted(k for k in old_keys - new_keys if k)
    return [f"[{label} manquant] {k}" for k in missing]


def do_compare(args) -> None:
    """Diff two snapshots and report regressions."""
    with open(args.old, encoding="utf-8") as fh:
        old = json.load(fh)
    with open(args.new, encoding="utf-8") as fh:
        new = json.load(fh)

    print("=" * 72)
    print(f"COMPARAISON MIGRATION : {args.old} (v18)  ->  {args.new} (v19)")
    print("=" * 72)

    regressions, warnings = _diff_fields(old["fields"], new["fields"])
    regressions += _diff_named(old["server_actions"], new["server_actions"],
                               "name", "Action serveur")
    regressions += _diff_named(old["reports"], new["reports"],
                               "name", "Rapport")
    warnings += _diff_named(old.get("automations", []),
                            new.get("automations", []), "name",
                            "Regle d'automatisation")
    warnings += _diff_named(old.get("views", []), new.get("views", []),
                            "name", "Vue")

    if not regressions and not warnings:
        print("\n✅ Aucune difference detectee. Personnalisations conservees.")
        sys.exit(0)

    if regressions:
        print(f"\n🔴 REGRESSIONS A CORRIGER ({len(regressions)}) :")
        for line in regressions:
            print(f"   - {line}")
    if warnings:
        print(f"\n🟡 AVERTISSEMENTS A VERIFIER ({len(warnings)}) :")
        for line in warnings:
            print(f"   - {line}")

    print("\n" + "=" * 72)
    # Non-zero exit only on hard regressions, so this can gate CI.
    sys.exit(1 if regressions else 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    snap = sub.add_parser("snapshot", help="Capturer l'etat d'une base Odoo.")
    snap.add_argument("--url", help="URL Odoo (defaut: env ODOO_URL).")
    snap.add_argument("--db", help="Base de donnees (defaut: env ODOO_DB).")
    snap.add_argument("--user", help="Utilisateur (defaut: env ODOO_USER).")
    snap.add_argument("--password", help="Mot de passe / cle API "
                                          "(defaut: env ODOO_PASSWORD).")
    snap.add_argument("--models", nargs="+", help="Modeles a inspecter "
                                                  "(defaut: liste webhook).")
    snap.add_argument("--out", required=True, help="Fichier JSON de sortie.")
    snap.set_defaults(func=do_snapshot)

    cmp_ = sub.add_parser("compare", help="Comparer deux snapshots (v18 vs v19).")
    cmp_.add_argument("old", help="Snapshot v18 (avant).")
    cmp_.add_argument("new", help="Snapshot v19 (apres).")
    cmp_.set_defaults(func=do_compare)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
