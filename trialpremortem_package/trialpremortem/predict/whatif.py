"""Counterfactual what-if — turns diagnosis into prescription.

Given a draft and its risk score, simulate design edits (relax exclusions, raise
enrollment target, widen age band) and report the risk delta for each. The agent
uses this to recommend the single highest-leverage change.
"""
from __future__ import annotations
import copy


def plain_driver(peer, draft):
    """Human-readable risk drivers (replaces the awkward 'N more than median (M)')."""
    out = []
    ex = draft.get("n_excl", 0); em = peer["excl_median"]
    if ex - em >= 3:
        out.append(f"{ex} exclusion criteria vs {int(em)} typical for this condition/phase "
                   f"— {ex-int(em)} more gates for patients to clear")
    elif ex > 15:
        out.append(f"{ex} exclusion criteria is high in absolute terms (peers ~{int(em)})")
    r = peer["enroll_vs_peer_ratio"]
    if r < 0.7 and draft.get("enroll_target", 0) > 0:
        out.append(f"enrollment target {draft['enroll_target']} is only {r:.0%} of the peer "
                   f"median ({int(peer['enroll_median'])}) — little buffer for screen-fail attrition")
    if draft.get("age_span", 100) < 40:
        out.append(f"age window spans only {draft.get('age_span')} years — narrow eligible pool")
    return out or ["no dominant single driver; risk is diffuse across the design"]


def whatif(engine, draft):
    """Return baseline risk + a ranked list of {edit, new_risk, delta}."""
    base = engine.score(draft)["risk_score"]
    scenarios = []

    def sim(label, mutator):
        d = copy.deepcopy(draft); mutator(d)
        r = engine.score(d)["risk_score"]
        scenarios.append({"edit": label, "new_risk": round(r, 3), "delta": round(r - base, 3)})

    ex = draft.get("n_excl", 0)
    if ex > 8:
        sim(f"Cut exclusions from {ex} to {max(ex-5, 6)} (drop lowest-value gates)",
            lambda d: d.update(n_excl=max(ex-5, 6)))
        sim(f"Cut exclusions from {ex} to peer median",
            lambda d: d.update(n_excl=8))
    tgt = draft.get("enroll_target", 0)
    if tgt > 0:
        sim(f"Raise enrollment target from {tgt} to {int(tgt*1.5)} (attrition buffer)",
            lambda d: d.update(enroll_target=int(tgt*1.5)))
    asp = draft.get("age_span", 100)
    if asp < 50:
        sim(f"Widen age band by 15 years (span {asp}->{asp+15})",
            lambda d: d.update(age_span=asp+15))
    # combined best-practice redesign
    sim("Combined: cut exclusions to median + 1.5x enrollment buffer",
        lambda d: d.update(n_excl=8, enroll_target=int(max(tgt,1)*1.5)))

    scenarios.sort(key=lambda s: s["delta"])  # most risk-reducing first
    return {"baseline_risk": round(base, 3), "scenarios": scenarios}
