"""End-to-end: draft protocol -> structured features -> ML risk (tool) -> retrieval
-> 5 persona red team -> ranked failure-mode register.

Usage (inside a kernel with `host`):
    from trialpremortem.run_demo import run_premortem
    register = run_premortem(draft_dict, host, engine, bg_retriever)
"""
from __future__ import annotations
import json
from .present.redteam import (PERSONAS, build_persona_prompt, emit_finding_tool,
                              moderator_prompt)


def draft_to_summary(d: dict) -> str:
    return (f"Condition: {d['cond']} | Phase: {d.get('phase','NA')}\n"
            f"Eligibility: {d['n_incl']} inclusion, {d['n_excl']} exclusion criteria\n"
            f"Age range span: {d.get('age_span','?')} years | Enrollment target: {d.get('enroll_target','?')}\n"
            f"Arms: {d.get('n_arms',1)} | Primary endpoint: {d.get('endpoint','?')}\n"
            f"Notes: {d.get('notes','')}")


def run_premortem(draft, host, engine, precedent_fn):
    """precedent_fn(draft)->list[str] returns cited precedent lines."""
    # 1. ML risk (the tool call)
    risk = engine.score(draft)
    # 2. precedent retrieval
    prec = precedent_fn(draft)
    summary = draft_to_summary(draft)
    # 3. five personas in parallel
    tool = emit_finding_tool()
    reqs = [{"messages": [{"role": "user", "content": build_persona_prompt(desc, summary, risk, prec)}],
             "tools": [tool], "tool_choice": {"type": "tool", "name": "emit_finding"},
             "max_tokens": 400} for desc in PERSONAS.values()]
    res = host.llm(reqs, max_concurrency=5)
    findings = {}
    for role, rr in zip(PERSONAS.keys(), res):
        f = {}
        for b in (rr.get("content") or []):
            if isinstance(b, dict) and b.get("type") == "tool_use":
                f = b.get("input"); break
        findings[role] = f
    # 4. moderator synthesis
    mod = host.llm(moderator_prompt(findings, risk))
    return {"risk": risk, "precedent": prec, "findings": findings,
            "register": mod.get("text", "")}
