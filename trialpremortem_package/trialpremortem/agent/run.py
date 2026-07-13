"""Live demo entrypoint — autonomous agentic pre-mortem.

Usage (inside a kernel where `host` is available):
    from trialpremortem.agent.run import premortem
    result = premortem(draft, host, engine, cohort, with_debate=True, verbose=True)

`draft` = {cond, phase, n_incl, n_excl, age_span, enroll_target, n_arms, notes}
"""
from __future__ import annotations
import json
from .tools import ToolBox
from .harness import run_agent, debate


def premortem(draft, host, engine, cohort, with_debate=True, verbose=True, model=None):
    tb = ToolBox(engine, cohort)
    tr = (lambda s: print(s)) if verbose else None
    if verbose:
        print("=" * 68); print("AUTONOMOUS PRE-MORTEM AGENT"); print("=" * 68)
    verdict, transcript = run_agent(draft, host, tb, model=model, trace=tr)
    out = {"draft": draft, "verdict": verdict,
           "tool_calls": [c[0] for c in tb.call_log], "transcript": transcript}
    if with_debate:
        if verbose:
            print("\n" + "=" * 68); print("MULTI-AGENT DEBATE"); print("=" * 68)
        out["debate"] = debate(draft, host, tb, model=model)
        if verbose:
            print("JUDGE:\n", out["debate"]["judge"][:800])
    if verbose:
        print("\n" + "=" * 68)
        print("FINAL VERDICT:", verdict.get("verdict"), "| risk", verdict.get("overall_risk"))
        print("=" * 68)
    return out
