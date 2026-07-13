"""Entrypoint for the orchestrator harness (runs in the `repl` kernel).

    from trialpremortem.agent.orchestrator_run import make_dispatch, run
    result = run(host, draft, cached_tools)

`cached_tools` = precomputed numpy tool outputs (score_risk, peer_norms,
find_failed_analogues, simulate_fix). Connectors are called live via host.mcp.
"""
from __future__ import annotations
from . import connectors as CX
from .orchestrator import run_premortem


def make_dispatch(host):
    def dispatch(name, args):
        if name == "drug_mechanism":  return CX.drug_mechanism(host, args["drug_name"])
        if name == "target_disease":  return CX.target_disease(host, args["chembl_id"])
        if name == "literature":      return CX.literature(host, args["query"], args.get("k", 5))
        if name == "similar_trials":  return CX.similar_trials(host, args["condition"], args.get("phase", ""))
        if name == "regulatory_precedent": return CX.regulatory_precedent(host, args["indication"])
        return {"unavailable": f"unknown tool {name}"}
    return dispatch


def run(host, draft, cached_tools, model=None, verbose=True):
    return run_premortem(host, draft, cached_tools, make_dispatch(host), model=model, verbose=verbose)
