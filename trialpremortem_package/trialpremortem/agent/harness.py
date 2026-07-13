"""Autonomous agentic harness for protocol pre-mortem.

Architecture (this is the 'agentic framework', not five fixed prompts):

  PremortemAgent — a ReAct-style controller with a real tool loop:
    the LLM decides which tool to call (score_risk, retrieve_precedent,
    base_rate, simulate_fix), reads the result, and iterates until it has
    enough evidence to emit a structured verdict. No fixed script.

  debate() — a proposer/critic loop: a Proposer argues the trial WILL fail
    (with evidence), a Critic challenges each claim, and a Judge scores the
    exchange. Runs on top of the same toolbox. This is the multi-agent layer.

Everything is grounded in tool calls against real data; the LLM orchestrates,
it does not invent numbers.
"""
from __future__ import annotations
import json


def tool_schemas():
    return [
        {"name": "score_risk",
         "description": "Run the validated ML risk engine on a draft protocol. Returns accrual-failure risk (0-1), the top human-readable drivers, and how the design compares to peer trials. Input is the draft dict.",
         "input_schema": {"type": "object", "properties": {
             "draft": {"type": "object", "description": "Draft with n_excl,n_incl,age_span,enroll_target,n_arms,cond,phase"}},
             "required": ["draft"]}},
        {"name": "retrieve_precedent",
         "description": "Retrieve similar historical trials (with their real outcomes) via BM25. outcome_filter: 'any'|'failed'|'completed'. Use 'failed' to find cautionary precedent, 'completed' to find what worked.",
         "input_schema": {"type": "object", "properties": {
             "query": {"type": "string"}, "k": {"type": "integer"},
             "outcome_filter": {"type": "string", "enum": ["any", "failed", "completed"]}},
             "required": ["query"]}},
        {"name": "base_rate",
         "description": "Get the empirical accrual-failure base rate among similar trials (by condition/phase). Grounds any risk claim in a prior.",
         "input_schema": {"type": "object", "properties": {
             "condition": {"type": "string"}, "phase": {"type": "string"}},
             "required": ["condition"]}},
        {"name": "simulate_fix",
         "description": "Counterfactual: simulate design edits (cut exclusions, raise enrollment, widen age) and return the risk reduction of each. Use to turn a diagnosis into a prescription.",
         "input_schema": {"type": "object", "properties": {
             "draft": {"type": "object"}}, "required": ["draft"]}},
        {"name": "conclude",
         "description": "Emit the final pre-mortem verdict once you have gathered enough evidence. Call this last.",
         "input_schema": {"type": "object", "properties": {
             "overall_risk": {"type": "number"},
             "verdict": {"type": "string", "enum": ["high risk", "moderate risk", "low risk"]},
             "primary_failure_mode": {"type": "string"},
             "evidence": {"type": "string", "description": "cite specific tool results / precedent NCTs"},
             "top_recommendation": {"type": "string"},
             "expected_risk_after_fix": {"type": "number"}},
             "required": ["overall_risk", "verdict", "primary_failure_mode", "evidence", "top_recommendation"]}},
    ]


CONTROLLER_SYSTEM = (
    "You are an autonomous clinical-trial pre-mortem agent. Given a draft protocol, your job is to "
    "determine whether it will FAIL TO RECRUIT patients, and why, BEFORE it is finalized.\n\n"
    "You have tools. Use them deliberately: check the base rate, score the ML risk, retrieve real "
    "precedent (both failed and completed), and simulate fixes. Form a hypothesis about the most likely "
    "failure mode, then use tools to CONFIRM OR REFUTE it — don't stop at the first signal. When you have "
    "enough grounded evidence, call `conclude`. Cite specific tool results and precedent NCT numbers. "
    "Never invent numbers; every quantitative claim must come from a tool result."
)


def _dispatch(tb, name, inp):
    if name == "score_risk":       return tb.score_risk(inp["draft"])
    if name == "retrieve_precedent": return tb.retrieve_precedent(inp["query"], inp.get("k", 6), inp.get("outcome_filter", "any"))
    if name == "base_rate":        return tb.base_rate(inp["condition"], inp.get("phase", ""))
    if name == "simulate_fix":     return tb.simulate_fix(inp["draft"])
    return {"error": f"unknown tool {name}"}


def run_agent(draft, host, tb, max_steps=8, model=None, trace=None):
    """The autonomous ReAct loop. Returns (verdict_dict, transcript)."""
    tools = tool_schemas()
    draft_json = json.dumps(draft, indent=1)
    messages = [{"role": "user", "content":
                 f"Draft protocol to pre-mortem:\n{draft_json}\n\nInvestigate and conclude."}]
    transcript = []
    kw = {"model": model} if model else {}
    for step in range(max_steps):
        r = host.llm({"system": CONTROLLER_SYSTEM, "messages": messages,
                      "tools": tools, "max_tokens": 1200, **kw})
        content = r.get("content") or []
        # assign ids to tool_use blocks (host.llm omits them)
        calls = []
        for i, b in enumerate(content):
            if b.get("type") == "tool_use":
                b.setdefault("id", f"t{step}_{i}")
                calls.append(b)
        if r.get("text") and trace:
            trace(f"[think] {r['text'][:200]}")
        messages.append({"role": "assistant", "content": content})
        if not calls:  # model spoke without a tool — nudge it
            messages.append({"role": "user", "content": "Use a tool or call conclude."})
            continue
        results = []
        concluded = None
        for c in calls:
            if c["name"] == "conclude":
                concluded = c["input"]
                results.append({"type": "tool_result", "tool_use_id": c["id"],
                                "content": "verdict recorded"})
            else:
                out = _dispatch(tb, c["name"], c["input"])
                if trace: trace(f"[tool] {c['name']}({json.dumps(c['input'])[:80]}) -> {json.dumps(out)[:120]}")
                transcript.append({"step": step, "tool": c["name"], "input": c["input"], "result": out})
                results.append({"type": "tool_result", "tool_use_id": c["id"],
                                "content": json.dumps(out)[:2000]})
        messages.append({"role": "user", "content": results})
        if concluded is not None:
            return concluded, transcript
    return {"verdict": "inconclusive", "note": "max steps reached"}, transcript


# ---- multi-agent debate ---------------------------------------------------
def debate(draft, host, tb, model=None, rounds=2):
    """Proposer (will-fail) vs Critic (challenges), Judge scores. Grounded in tools."""
    kw = {"model": model} if model else {}
    # ground both sides in the same evidence
    risk = tb.score_risk(draft)
    prec_fail = tb.retrieve_precedent(f"{draft.get('cond')} {draft.get('phase','')}", k=5, outcome_filter="failed")
    prec_ok = tb.retrieve_precedent(f"{draft.get('cond')} {draft.get('phase','')}", k=5, outcome_filter="completed")
    base = tb.base_rate(draft.get("cond", ""), draft.get("phase", ""))
    evidence = json.dumps({"ml_risk": risk, "base_rate": base,
                           "failed_precedent": prec_fail["precedent"],
                           "completed_precedent": prec_ok["precedent"]}, indent=1)[:3000]

    prop = host.llm({"system": "You are the PROPOSER. Argue, with specific evidence, that this trial WILL fail to recruit. Cite NCTs and numbers from the evidence. Be rigorous, not alarmist.",
                     "messages": [{"role": "user", "content": f"Draft:\n{json.dumps(draft)}\n\nEvidence:\n{evidence}\n\nMake the strongest evidence-based case that it fails."}],
                     "max_tokens": 600, **kw})["text"]
    crit = host.llm({"system": "You are the CRITIC. Challenge the proposer's case point by point using the SAME evidence. Where is it overstated? What does the completed-precedent show? Concede what's valid.",
                     "messages": [{"role": "user", "content": f"Evidence:\n{evidence}\n\nProposer's case:\n{prop}\n\nChallenge it."}],
                     "max_tokens": 600, **kw})["text"]
    judge = host.llm({"system": "You are the JUDGE. Given the evidence, the proposer, and the critic, deliver a calibrated verdict. Return: risk level (high/moderate/low), the single most defensible failure mode, and confidence (0-1).",
                      "messages": [{"role": "user", "content": f"Evidence:\n{evidence}\n\nProposer:\n{prop}\n\nCritic:\n{crit}\n\nVerdict?"}],
                      "max_tokens": 400, **kw})["text"]
    return {"ml_risk": risk["risk_score"], "base_rate": base["base_rate"],
            "proposer": prop, "critic": crit, "judge": judge}
