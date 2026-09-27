"""Verdict screen data: the stored evaluation payload, the reviewer override and the agreement-meter geometry.

Nothing here runs a model: the page and /api/claims/<id>/evaluation read what was stored at evaluation time,
so an updated model or policy never changes a past verdict (SRS xlviii).
"""
from __future__ import annotations

import json
import math

CLASS_ORDER = ("Valid Claim", "Invalid Claim", "Manual Review")
CONSISTENCY_TONE = {"Strong Match": "valid", "Acceptable Match": "valid", "Weak Match": "review",
                    "Model Disagreement": "invalid", "Uncertain Result": "invalid"}
TONE_VAR = {"valid": "--valid", "review": "--review-mark", "invalid": "--invalid"}
REVIEWER_STAMP = {"Approved": ("Approved by reviewer", "valid"), "Rejected": ("Rejected by reviewer", "invalid"),
                  "Closed": ("Closed by reviewer", "none")}
CX, CY, R_OUT, R_IN, NEEDLE = 160, 160, 140, 104, 118
DETAILS_KEY = "show_model_details_to_customers"


def _legacy_payload(ev) -> dict:
    """Payload for evaluations stored before payload_json existed (built from the row's own columns)."""
    def block(avail, version, cls, scores, err):
        return {"available": bool(avail), "error": err, "version": (version or "").split("+")[0] or None,
                "predicted": cls, "top": max(scores.values()) if scores else None, "scores": scores}
    rules = ev.claim.rule_validation.rules if ev.claim.rule_validation else []
    return {
        "claim_id": ev.claim.claim_id, "state": "decided", "evaluation_id": ev.evaluation_id,
        "stages": [], "total_ms": ev.latency_ms,
        "python": {**block(ev.python_available, ev.python_model_version, ev.python_predicted_class, ev.python_scores(),
                           ev.model_errors.get("python")), "contributions": []},
        "gtm": {**block(ev.gtm_available, ev.gtm_model_version, ev.gtm_predicted_class, ev.gtm_scores(), ev.model_errors.get("gtm")),
                "card_url": f"/claims/{ev.claim.claim_id}/card.png?evaluation={ev.evaluation_id}", "occlusion": []},
        "consistency": {"status": ev.model_consistency_status, "difference": ev.top_confidence_difference,
                        "match": ev.is_class_match, "explanation": ev.thresholds.get("explanation", ""),
                        "thresholds": {k: ev.thresholds.get(k) for k in ("min_confidence", "strong_max_diff", "acceptable_max_diff")}},
        "decision": {"value": ev.decision, "rule_id": ev.decision_rule_id, "reason": ev.claim.decision_reason,
                     "policy_version": ev.decision_policy_version, "trace": ev.decision_trace},
        "rules": {"passed": [r for r in rules if not r["fired"]],
                  "warnings": [r for r in rules if r["fired"] and r["severity"] == "warning"],
                  "review": [r for r in rules if r["fired"] and r["severity"] == "manual_review"],
                  "failed": [r for r in rules if r["fired"] and r["severity"] == "hard_fail"]},
        "contradictions": ev.claim.rule_validation.contradictions if ev.claim.rule_validation else [],
        "duplicates": ev.claim.rule_validation.duplicate_flags if ev.claim.rule_validation else [],
        "evidence_needed": [], "override": None,
    }


def stored_payload(ev) -> dict:
    return json.loads(ev.payload_json) if ev.payload_json else _legacy_payload(ev)


def override_for(claim) -> dict | None:
    """The latest reviewer decision that settled the claim (Approved / Rejected / Closed)."""
    settled = [a for a in claim.reviewer_actions if a.reviewer_decision in REVIEWER_STAMP]
    if not settled:
        return None
    a = max(settled, key=lambda x: (x.timestamp, x.id))
    label, tone = REVIEWER_STAMP[a.reviewer_decision]
    return {"decision": a.reviewer_decision, "label": label, "tone": tone, "is_override": bool(a.is_override),
            "reviewer": a.reviewer.full_name, "reason": a.override_reason or a.comments,
            "at": a.timestamp.strftime("%d %b %Y %H:%M"), "previous_recommendation": a.previous_recommendation}


def _point(v: float, r: float) -> tuple[float, float]:
    theta = math.pi * (1 - v)
    return round(CX + r * math.cos(theta), 2), round(CY - r * math.sin(theta), 2)


def _sector(v1: float, v2: float) -> str:
    """Annulus sector between two values on the 180° scale (SVG path)."""
    a, b = sorted((max(0.0, min(1.0, v1)), max(0.0, min(1.0, v2))))
    if b - a < 0.004:
        b = min(1.0, a + 0.004)
    (x1, y1), (x2, y2) = _point(a, R_OUT), _point(b, R_OUT)
    (x3, y3), (x4, y4) = _point(b, R_IN), _point(a, R_IN)
    return f"M{x1} {y1} A{R_OUT} {R_OUT} 0 0 1 {x2} {y2} L{x3} {y3} A{R_IN} {R_IN} 0 0 0 {x4} {y4} Z"


def meter(payload: dict) -> dict:
    """Geometry for the 180° agreement gauge (server-rendered SVG; JS only animates it)."""
    py, gtm, cons = payload["python"], payload["gtm"], payload["consistency"]
    min_conf = cons["thresholds"].get("min_confidence") or 0.6
    ticks = []
    for v in (0.25, 0.5, min_conf, 0.75):
        (x1, y1), (x2, y2) = _point(v, R_OUT + 4), _point(v, R_OUT + 14)
        lx, ly = _point(v, R_IN - 16) if v == min_conf else _point(v, R_OUT + 26)   # threshold label sits inside the arc
        ticks.append({"v": v, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "lx": lx, "ly": ly, "min": v == min_conf,
                      "label": f"min {v:.2f}" if v == min_conf else f"{v:.2f}"})
    tone = CONSISTENCY_TONE.get(cons["status"], "invalid")
    needles = []
    for key, cls in (("python", "py"), ("gtm", "gtm")):
        m = payload[key]
        if m.get("available") and m.get("top") is not None:
            needles.append({"cls": cls, "angle": round(-90 + 180 * m["top"], 2), "value": m["top"],
                            "dashed": cls == "gtm" and cons.get("match") is False})
    arc = _sector(py["top"], gtm["top"]) if len(needles) == 2 else None
    track = _sector(0, 1)
    both = len(needles) == 2
    sentence = []
    for label, m in (("Python model", py), ("Teachable Machine", gtm)):
        sentence.append(f"{label}: {m['predicted']} at {m['top']:.2f}." if m.get("available") else f"{label}: unavailable.")
    if cons.get("difference") is not None:
        sentence.append(f"Difference {cons['difference']:.2f}, {cons['status']}.")
    else:
        sentence.append(f"{cons['status']}.")
    caption = (f"Python chose {py['predicted']}; Teachable Machine chose {gtm['predicted']}."
               if both and cons.get("match") is False else cons.get("explanation", ""))
    return {"track": track, "arc": arc, "tone": tone, "tone_var": TONE_VAR[tone], "ticks": ticks, "needles": needles,
            "needle_len": NEEDLE, "label": " ".join(sentence), "caption": caption, "cx": CX, "cy": CY}


def show_model_details(user) -> bool:
    """Reviewers, staff and admins always see probabilities and rule IDs; customers only when the admin allows it."""
    from src.models.entities import SystemSetting
    if user is None:
        return False
    if user.role != "customer":
        return True
    return SystemSetting.get_val(DETAILS_KEY, "1") == "1"


def view(claim, *, fresh: bool = False) -> dict | None:
    ev = claim.model_evaluation
    if ev is None:
        return None
    p = stored_payload(ev)
    p["override"] = override_for(claim)
    return {"p": p, "meter": meter(p), "fresh": fresh, "decision_kind": {"Likely Valid": "valid", "Likely Invalid": "invalid",
            "Manual Review Required": "review"}.get(p["decision"]["value"], "none")}


def api_payload(claim) -> dict:
    """Body of GET /api/claims/<id>/evaluation: stored verdict, or the pipeline's pending state."""
    if claim.model_evaluation is None:
        state = "pending" if claim.status in ("Submitted", "Under Evaluation") else "not_evaluated"
        return {"claim_id": claim.claim_id, "state": state,
                "stages": [{"name": n, "status": "waiting", "ms": None} for n in ("preprocess", "python", "card", "gtm", "rules")]}
    p = stored_payload(claim.model_evaluation)
    p["override"] = override_for(claim)
    return p
