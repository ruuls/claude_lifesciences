"""Tool backends the autonomous agent calls. Each returns a JSON-serializable dict.

These are the *capabilities* the agent orchestrates — it decides which to call,
in what order, and when it has enough evidence to conclude. The validated ML
risk engine is ONE tool here, not the whole system.
"""
from __future__ import annotations
import re
from ..predict.bm25 import BM25, tokenize
from ..predict.whatif import whatif


class ToolBox:
    def __init__(self, engine, cohort):
        self.engine = engine
        self.cohort = cohort
        self._docs, self._meta = [], []
        for t in cohort:
            v0 = t["v0"]
            elig = re.sub(r"<[^>]+>", " ", v0.get("eligibilityModule", {}).get("eligibilityCriteria", "") or "")
            self._docs.append(tokenize(f"{t['condition']} {t['phase']} {elig[:1200]}"))
            self._meta.append(t)
        self._bm25 = BM25(self._docs)
        self.call_log = []

    def score_risk(self, draft: dict) -> dict:
        r = self.engine.score(draft)
        self.call_log.append(("score_risk", draft.get("cond"), r["risk_score"]))
        return {"risk_score": r["risk_score"], "drivers": r["top_drivers"],
                "peer_comparison": {k: (round(v, 2) if isinstance(v, float) else v)
                                    for k, v in r["peer_comparison"].items()}}

    def retrieve_precedent(self, query: str, k: int = 6, outcome_filter: str = "any") -> dict:
        top = self._bm25.topk(tokenize(query), k + 8)
        out = []
        for idx, sc in top:
            m = self._meta[idx]
            if outcome_filter == "failed" and str(m["y"]) != "1": continue
            if outcome_filter == "completed" and m["outcome"] != "COMPLETED": continue
            out.append({"nct": m["nct"], "condition": m["condition"], "phase": m["phase"],
                        "outcome": m["outcome"],
                        "failure_mode": m["failure_mode"] if m["outcome"] == "TERMINATED" else None,
                        "why_stopped": (m["why_stopped"] or "")[:90],
                        "enrollment": m["enrollment"], "bm25": round(sc, 2)})
            if len(out) >= k: break
        self.call_log.append(("retrieve_precedent", query[:40], len(out)))
        return {"query": query, "n": len(out), "precedent": out}

    def base_rate(self, condition: str, phase: str = "") -> dict:
        c = condition.lower()[:12]
        hits = [m for m in self._meta if m["condition"].lower()[:12] == c]
        if phase:
            hits = [m for m in hits if phase.split(";")[0] in (m["phase"] or "")] or hits
        n = len(hits)
        if n == 0:
            hits = self._meta; n = len(hits)
        fails = sum(1 for m in hits if str(m["y"]) == "1")
        self.call_log.append(("base_rate", condition, f"{fails}/{n}"))
        return {"condition": condition, "phase": phase, "n_similar": n,
                "accrual_failures": fails, "base_rate": round(fails / n, 3)}

    def simulate_fix(self, draft: dict) -> dict:
        wi = whatif(self.engine, draft)
        self.call_log.append(("simulate_fix", draft.get("cond"), len(wi["scenarios"])))
        return wi
