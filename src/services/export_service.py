"""CSV / Excel-compatible exports (SRS xlv).

Output is UTF-8 with a BOM so Excel opens it with the right encoding, and every
cell that starts with = + - @ is prefixed with an apostrophe (CSV formula injection).
"""
from __future__ import annotations

import csv
import io

DANGEROUS = ("=", "+", "-", "@", "\t", "\r")


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    text = str(value)
    return "'" + text if text.startswith(DANGEROUS) else text


def to_csv(header: list, rows) -> str:
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(header)
    for row in rows:
        w.writerow([_cell(v) for v in row])
    return buf.getvalue()


def claims_csv(claims) -> str:
    header = ["Claim ID", "Status", "Submitted", "Customer", "Product ID", "Product", "Category", "Serial",
              "Fault", "Damage type", "Final decision", "Rule", "Risk", "Python class", "Python P(valid)",
              "Python P(invalid)", "Python P(manual)", "GTM class", "GTM P(valid)", "GTM P(invalid)",
              "GTM P(manual)", "Confidence diff", "Consistency", "Python model", "GTM model", "Reviewer",
              "Duplicate", "Contradiction", "Missing docs"]

    def row(c):
        e = c.model_evaluation
        return [c.claim_id, c.status, c.claim_submission_date, c.claimant.full_name, c.product.product_id,
                c.product.product_name, c.product.category, c.product.serial_number, c.fault_category,
                c.damage_type, c.final_decision, c.decision_rule_id, c.risk_level,
                e and e.python_predicted_class, e and e.python_conf_valid, e and e.python_conf_invalid,
                e and e.python_conf_manual, e and e.gtm_predicted_class, e and e.gtm_conf_valid,
                e and e.gtm_conf_invalid, e and e.gtm_conf_manual, e and e.top_confidence_difference,
                e and e.model_consistency_status, e and e.python_model_version, e and e.gtm_model_version,
                c.assigned_reviewer.full_name if c.assigned_reviewer else "", int(bool(c.is_duplicate_flag)),
                int(bool(c.contradiction_flag)), int(bool(c.missing_document_flag))]
    return to_csv(header, (row(c) for c in claims))


def products_csv(products) -> str:
    header = ["Product ID", "Owner", "Name", "Category", "Brand", "Model", "Serial", "Purchase date", "Price",
              "Retailer", "Invoice", "Service center", "Warranty status", "Warranty expiry", "Repairs"]
    return to_csv(header, ([p.product_id, p.owner.full_name, p.product_name, p.category, p.brand, p.model_number,
                            p.serial_number, p.purchase_date, p.purchase_price, p.retailer, p.invoice_number,
                            p.service_center.name if p.service_center else "",
                            p.warranty.status if p.warranty else "No warranty",
                            p.warranty.expiry_date if p.warranty else "", len(p.repair_records)] for p in products))


def warranties_csv(products) -> str:
    header = ["Warranty ID", "Product ID", "Product", "Provider", "Start", "Expiry", "Months", "Extended",
              "Days left", "Status", "Service center"]
    return to_csv(header, ([w.warranty_id, p.product_id, p.product_name, w.warranty_provider, w.start_date,
                            w.expiry_date, w.duration_months, int(bool(w.is_extended)), w.remaining_days(), w.status,
                            w.service_center_name] for p in products if (w := p.warranty)))


def analytics_csv(data: dict) -> str:
    """Flatten the analytics payload into section / metric / value rows."""
    rows = []

    def walk(prefix, value):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(f"{prefix} / {k}" if prefix else str(k), v)
        elif isinstance(value, (list, tuple)):
            rows.append([prefix, ", ".join(map(str, value))])
        else:
            rows.append([prefix, value])
    walk("", data)
    return to_csv(["Metric", "Value"], rows)


def audit_csv(logs) -> str:
    header = ["Time (UTC)", "Action", "Actor", "Role", "Entity", "Entity ID", "IP", "Details"]
    return to_csv(header, ([l.timestamp, l.action, l.actor.email if l.actor else "system", l.user_role,
                            l.entity_type, l.entity_id, l.ip_address, l.details_json] for l in logs))
