"""L3 EXTRACT — v0 protocol -> ProtocolFeatures.

Division of labor (the 'system not a prompt' principle):
  * CODE computes every deterministic feature it can directly from the structured
    protocolSection (age bounds, arm count, enrollment target, criteria counts).
  * The LLM is used ONLY for the parse that code cannot do reliably: reading free-text
    eligibility criteria into boolean design flags (prior-therapy bar, comorbidity
    exclusions, biomarker gate) and estimating endpoint horizon / visit burden.
  * restrictiveness_index is then a deterministic function over those parsed flags.
"""
from __future__ import annotations
import re, json
from ..schemas import ProtocolFeatures


def _split_criteria(text: str) -> tuple[list[str], list[str]]:
    """Split an eligibilityCriteria blob into (inclusion, exclusion) bullet lists."""
    if not text:
        return [], []
    t = re.sub(r"<[^>]+>", "\n", text)  # strip HTML tags -> newlines
    t = re.sub(r"\n+", "\n", t)
    low = t.lower()
    incl_i = low.find("inclusion")
    excl_i = low.find("exclusion")
    def bullets(seg):
        items = [re.sub(r"^[\-\*\u2022\d\.\)\s]+", "", ln).strip()
                 for ln in seg.split("\n")]
        return [i for i in items if len(i) > 8]
    if excl_i > incl_i >= 0:
        return bullets(t[incl_i:excl_i]), bullets(t[excl_i:])
    if incl_i >= 0:
        return bullets(t[incl_i:]), []
    return bullets(t), []


def code_features(nct: str, ps: dict) -> ProtocolFeatures:
    """Everything computable directly from the structured protocolSection."""
    elig = ps.get("eligibilityModule", {})
    design = ps.get("designModule", {})
    arms = ps.get("armsInterventionsModule", {})
    outcomes = ps.get("outcomesModule", {})
    cond = ps.get("conditionsModule", {})
    status = ps.get("statusModule", {})

    incl, excl = _split_criteria(elig.get("eligibilityCriteria", ""))

    def age_val(s, default):
        m = re.search(r"(\d+)", s or "")
        return float(m.group(1)) if m else default
    age_min = age_val(elig.get("minimumAge", ""), 0.0)
    age_max = age_val(elig.get("maximumAge", ""), 120.0)

    sd = status.get("startDateStruct", {}).get("date", "")
    start_year = int(sd[:4]) if sd[:4].isdigit() else 0

    f = ProtocolFeatures(
        nct=nct,
        n_inclusion=len(incl),
        n_exclusion=len(excl),
        age_min=age_min,
        age_max=age_max,
        age_span=max(age_max - age_min, 0.0),
        excl_count_normalized=len(excl) / max(len(incl) + len(excl), 1),
        n_arms=len(arms.get("armGroups", []) or []) or 1,
        n_primary_endpoints=len(outcomes.get("primaryOutcomes", []) or []) or 1,
        enrollment_target=(design.get("enrollmentInfo", {}) or {}).get("count", 0) or 0,
        phase=";".join(design.get("phases", []) or []),
        condition=(cond.get("conditions", [""]) or [""])[0],
        start_year=start_year,
    )
    return f, incl, excl


_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "excl_prior_therapy": {"type": "boolean"},
        "excl_comorbidity": {"type": "boolean"},
        "biomarker_gated": {"type": "boolean"},
        "endpoint_horizon_weeks": {"type": "number"},
        "visit_burden": {"type": "number"},
    },
    "required": ["excl_prior_therapy", "excl_comorbidity", "biomarker_gated",
                 "endpoint_horizon_weeks", "visit_burden"],
}


def llm_prompt(incl: list[str], excl: list[str], ps: dict) -> str:
    outs = ps.get("outcomesModule", {}).get("primaryOutcomes", []) or []
    prim = "; ".join((o.get("measure","") + " @ " + o.get("timeFrame","")) for o in outs[:3])
    return (
        "You are extracting structured design flags from a clinical trial protocol draft. "
        "Given the eligibility criteria and primary endpoint(s), return JSON with:\n"
        "- excl_prior_therapy: true if exclusions bar patients with prior treatment/therapy lines\n"
        "- excl_comorbidity: true if exclusions bar common comorbidities (autoimmune, other malignancy, organ dysfunction, infection)\n"
        "- biomarker_gated: true if enrollment REQUIRES a specific molecular/genetic biomarker\n"
        "- endpoint_horizon_weeks: weeks from enrollment to primary endpoint readout (estimate from timeFrame)\n"
        "- visit_burden: estimated number of distinct on-study assessment visits (integer as number)\n\n"
        f"INCLUSION:\n" + "\n".join("- "+c for c in incl[:20]) + "\n\n"
        f"EXCLUSION:\n" + "\n".join("- "+c for c in excl[:25]) + "\n\n"
        f"PRIMARY ENDPOINT(S): {prim}\n\n"
        "Return only the JSON object."
    )


def restrictiveness_index(f: ProtocolFeatures) -> float:
    """Deterministic composite in [0,1] from parsed flags. Higher = more restrictive."""
    import math
    # normalized exclusion count (saturating), plus severity flags, plus age-span penalty
    excl_term = 1 - math.exp(-f.n_exclusion / 12.0)          # 0..~1, saturates ~24 exclusions
    flags = (int(f.excl_prior_therapy) + int(f.excl_comorbidity) + int(f.biomarker_gated)) / 3.0
    age_pen = 1 - min(f.age_span, 100.0) / 100.0             # narrow age window -> higher
    idx = 0.5 * excl_term + 0.35 * flags + 0.15 * age_pen
    return round(min(max(idx, 0.0), 1.0), 4)
