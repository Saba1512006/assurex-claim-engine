"""Dashboard metrics and analytics (SRS xl, xli, xliii).

Every function takes an already-scoped claim query (guards.scoped_claims), so a
metric can never count records the viewer is not allowed to see.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from datetime import date, timedelta
from statistics import mean

from config.config import Config
from src.core.vocab import CATEGORIES, CONSISTENCY_STATUSES, DECISIONS
from src.models.entities import Claim, Product, ProductWarranty, RepairHistory


def apply_filters(query, *, category: str | None = None, start: date | None = None, end: date | None = None,
                  status: str | None = None):
    """Shared dashboard filters (category, submission date range, status)."""
    if category in CATEGORIES:
        query = query.join(Product, Claim.product_id == Product.id).filter(Product.category == category)
    if start:
        query = query.filter(Claim.claim_submission_date >= start)
    if end:
        query = query.filter(Claim.claim_submission_date <= end)
    if status in Config.ALL_CLAIM_STATUSES:
        query = query.filter(Claim.status == status)
    return query


def _evaluations(claims):
    return [c.model_evaluation for c in claims if c.model_evaluation is not None]


def overview(claim_query) -> dict:
    """SRS xli: totals, decision mix, pending, duplicates, disagreements, average confidences, trend."""
    claims = claim_query.all()
    submitted = [c for c in claims if c.status != Config.STATUS_DRAFT]
    evals = _evaluations(submitted)
    by_decision = Counter(c.final_decision for c in submitted if c.final_decision)
    py = [e.python_top for e in evals if e.python_top is not None]
    gtm = [e.gtm_top for e in evals if e.gtm_top is not None]
    diffs = [e.top_confidence_difference for e in evals if e.top_confidence_difference is not None]
    compared = [e for e in evals if e.is_class_match is not None]
    return {
        "total": len(submitted),
        "drafts": len(claims) - len(submitted),
        "likely_valid": by_decision.get("Likely Valid", 0),
        "likely_invalid": by_decision.get("Likely Invalid", 0),
        "manual_review": by_decision.get("Manual Review Required", 0),
        "pending": sum(1 for c in submitted if c.status in (Config.STATUS_SUBMITTED, Config.STATUS_UNDER_EVALUATION,
                                                             Config.STATUS_MANUAL_REVIEW, Config.STATUS_ADDITIONAL_INFO)),
        "in_queue": sum(1 for c in submitted if c.status == Config.STATUS_MANUAL_REVIEW),
        "duplicates": sum(1 for c in submitted if c.is_duplicate_flag),
        "contradictions": sum(1 for c in submitted if c.contradiction_flag),
        "disagreements": sum(1 for e in compared if not e.is_class_match),
        "compared": len(compared),
        "gtm_missing": sum(1 for e in evals if not e.gtm_available),
        "avg_python_conf": round(mean(py), 3) if py else None,
        "avg_gtm_conf": round(mean(gtm), 3) if gtm else None,
        "avg_conf_diff": round(mean(diffs), 3) if diffs else None,
        "status_counts": OrderedDict((s, sum(1 for c in claims if c.status == s)) for s in Config.ALL_CLAIM_STATUSES),
        "decision_counts": OrderedDict((d, by_decision.get(d, 0)) for d in DECISIONS),
        "trend": weekly_trend(submitted),
    }


def weekly_trend(claims, weeks: int = 12) -> dict:
    today = date.today()
    start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    labels = [start + timedelta(weeks=i) for i in range(weeks)]
    series = {d: [0] * weeks for d in DECISIONS}
    for c in claims:
        if not c.claim_submission_date or not c.final_decision or c.claim_submission_date < start:
            continue
        idx = min(weeks - 1, (c.claim_submission_date - start).days // 7)
        series[c.final_decision][idx] += 1
    return {"labels": [d.strftime("%d %b") for d in labels], "series": [[d, series[d]] for d in DECISIONS]}


def full(claim_query, product_query) -> dict:
    """SRS xliii: outcomes, faults, rejection reasons, categories, expirations, repairs, models, manual review."""
    claims = [c for c in claim_query.all() if c.status != Config.STATUS_DRAFT]
    evals = _evaluations(claims)
    products = product_query.all()

    rejected_reasons = Counter()
    manual_reasons = Counter()
    for c in claims:
        log = c.rule_validation
        if log is None:
            continue
        if c.final_decision == "Likely Invalid":
            for r in log.of("hard_fail"):
                rejected_reasons[r["rule_id"].replace("_", " ").capitalize()] += 1
        if c.final_decision == "Manual Review Required":
            e = c.model_evaluation
            if log.contradictions:
                manual_reasons["Contradictions"] += 1
            if log.duplicate_flags:
                manual_reasons["Duplicate indicators"] += 1
            if log.missing_documents:
                manual_reasons["Missing documents"] += 1
            if e and e.model_consistency_status in ("Model Disagreement", "Weak Match"):
                manual_reasons["Models disagree / weak match"] += 1
            if e and e.model_consistency_status == "Uncertain Result":
                manual_reasons["Low confidence or model unavailable"] += 1
            if log.of("manual_review"):
                manual_reasons["Policy review rule"] += 1

    today = date.today()
    warranties = [p.warranty for p in products if p.warranty]
    expiring_by_month = Counter()
    for w in warranties:
        if today <= w.expiry_date <= today + timedelta(days=365):
            expiring_by_month[w.expiry_date.strftime("%Y-%m")] += 1
    repairs = RepairHistory.query.filter(RepairHistory.product_id.in_([p.id for p in products])).all() if products else []

    compared = [e for e in evals if e.is_class_match is not None]
    return {
        "outcomes": OrderedDict((s, sum(1 for c in claims if c.status == s)) for s in Config.ALL_CLAIM_STATUSES[1:]),
        "faults": OrderedDict(Counter(c.fault_category for c in claims).most_common(8)),
        "damage": OrderedDict(Counter(c.damage_type for c in claims).most_common()),
        "rejection_reasons": OrderedDict(rejected_reasons.most_common()),
        "categories": OrderedDict((cat, {
            "products": sum(1 for p in products if p.category == cat),
            "claims": sum(1 for c in claims if c.product.category == cat),
            "invalid": sum(1 for c in claims if c.product.category == cat and c.final_decision == "Likely Invalid"),
        }) for cat in CATEGORIES),
        "warranty_status": OrderedDict((s, sum(1 for w in warranties if w.status == s))
                                       for s in ("Active", "Expiring soon", "Expired", "Not started")),
        "expiring_by_month": OrderedDict(sorted(expiring_by_month.items())),
        "repairs": {"total": len(repairs), "authorised": sum(1 for r in repairs if r.is_authorized_center),
                    "unauthorised": sum(1 for r in repairs if not r.is_authorized_center),
                    "avg_cost": round(mean(r.repair_cost for r in repairs), 2) if repairs else None,
                    "outcomes": OrderedDict(Counter(r.outcome for r in repairs).most_common())},
        "models": {"evaluations": len(evals),
                   "consistency": OrderedDict((s, sum(1 for e in evals if e.model_consistency_status == s))
                                              for s in CONSISTENCY_STATUSES),
                   "agreement_rate": round(sum(1 for e in compared if e.is_class_match) / len(compared), 3) if compared else None,
                   "python_classes": OrderedDict(Counter(e.python_predicted_class for e in evals if e.python_available)),
                   "gtm_classes": OrderedDict(Counter(e.gtm_predicted_class for e in evals if e.gtm_available)),
                   "avg_latency_ms": round(mean(e.latency_ms for e in evals if e.latency_ms is not None), 1)
                   if any(e.latency_ms is not None for e in evals) else None},
        "manual_review": {"count": sum(1 for c in claims if c.final_decision == "Manual Review Required"),
                          "rate": round(sum(1 for c in claims if c.final_decision == "Manual Review Required")
                                        / len(claims), 3) if claims else None,
                          "reasons": OrderedDict(manual_reasons.most_common())},
    }


def warranty_buckets(product_query) -> dict:
    """Customer dashboard (SRS iv, xl): active / expiring / expired counts for the viewer's products."""
    out = Counter()
    for p in product_query.all():
        out[p.warranty.status if p.warranty else "No warranty"] += 1
    return out


def expiring_list(product_query, days: int) -> list:
    today = date.today()
    return (ProductWarranty.query.join(Product)
            .filter(Product.id.in_(product_query.with_entities(Product.id)),
                    ProductWarranty.expiry_date >= today, ProductWarranty.expiry_date <= today + timedelta(days=days))
            .order_by(ProductWarranty.expiry_date).all())


CONF_BINS = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0001)]


def dashboard_extras(claim_query) -> dict:
    """Operations KPIs and the extra charts on the admin overview (same scoped, filtered query as overview())."""
    submitted = [c for c in claim_query.all() if c.status != Config.STATUS_DRAFT]
    evals = _evaluations(submitted)
    decided_auto = [c for c in submitted if c.final_decision in ("Likely Valid", "Likely Invalid")]
    actions = [a for c in submitted for a in c.reviewer_actions if a.reviewer_decision in ("Approved", "Rejected")]
    overrides = [a for a in actions if a.is_override]
    latencies = [e.latency_ms for e in evals if e.latency_ms is not None]
    compared = [e for e in evals if e.is_class_match is not None]

    def hist(values):
        return [sum(1 for v in values if lo <= v < hi) for lo, hi in CONF_BINS]
    by_cat = {cat: Counter(c.final_decision for c in submitted if c.product.category == cat and c.final_decision) for cat in CATEGORIES}
    return {
        "automation_rate": round(len(decided_auto) / len(submitted), 4) if submitted else None,
        "agreement_rate": round(sum(1 for e in compared if e.is_class_match) / len(compared), 4) if compared else None,
        "override_rate": round(len(overrides) / len(actions), 4) if actions else None,
        "overrides": len(overrides), "reviewed": len(actions),
        "median_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else None,
        "consistency_counts": OrderedDict((s, sum(1 for e in evals if e.model_consistency_status == s)) for s in CONSISTENCY_STATUSES),
        "confidence_hist": {"labels": [f"{lo:.1f}–{min(hi, 1):.1f}" for lo, hi in CONF_BINS],
                            "Python model": hist([e.python_top for e in evals if e.python_top is not None]),
                            "Teachable Machine": hist([e.gtm_top for e in evals if e.gtm_top is not None])},
        "category_decisions": {"labels": list(CATEGORIES),
                               "series": [[d, [by_cat[cat].get(d, 0) for cat in CATEGORIES]] for d in DECISIONS]},
    }
