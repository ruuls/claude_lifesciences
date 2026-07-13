"""L0/L2/L3 — the autonomous orchestrator harness.

  Orchestrator: parse -> risk-triage (numpy tool) -> generate failure hypotheses
    SPECIFIC to this draft -> dispatch one investigator per hypothesis, each in an
    ISOLATED context running its own tool-use loop over live connectors -> findings
    written to a shared blackboard -> adversarial critic gates each finding ->
    synthesis into a ranked, evidence-cited failure-mode register.

Design choices for demo-reliability under a deadline:
  - "context isolation" = each investigator is its own fresh host.llm message thread
    (no shared history), not a heavyweight delegated frame. Same isolation property,
    far more reliable on stage, and avoids the per-frame token ceiling.
  - every step is appended to an in-memory trajectory (JSONL-able) for the live viz.
  - the numpy risk engine + cohort retrieval come in PRE-COMPUTED via `cached_tools`
    (they don't need the network); connectors are called live.
"""
from __future__ import annotations
import json


# ---------- tool schemas the investigators can call ----------------------
def investigator_tools():
    # SINGLE dispatcher tool with an `action` selector. This is deliberate: host.llm
    # auto-injects a global-scope prompt-cache marker whenever >=2 tool definitions are
    # present, which then conflicts with the message blocks and 400s. Collapsing all
    # capabilities into one tool keeps us at exactly one tool definition and sidesteps
    # the bug entirely, at every message-thread size.
    return [{
        "name": "investigate",
        "description": ("Call one research capability. `action` selects it; pass its params in the same object. "
                        "Actions: drug_mechanism(drug_name)->ChEMBL MoA+chembl_id; "
                        "target_disease(chembl_id)->Open Targets MoA/target/stage; "
                        "literature(query)->PubMed titles+PMIDs+abstracts; "
                        "similar_trials(condition,phase)->real trials+whyStopped; "
                        "record_finding(supported,claim,evidence,severity)->conclude."),
        "input_schema": {"type": "object", "properties": {
            "action": {"type": "string",
                       "enum": ["drug_mechanism", "target_disease", "literature", "similar_trials", "record_finding"]},
            "drug_name": {"type": "string"}, "chembl_id": {"type": "string"},
            "query": {"type": "string"}, "condition": {"type": "string"}, "phase": {"type": "string"},
            "supported": {"type": "boolean"}, "claim": {"type": "string"}, "evidence": {"type": "string"},
            "severity": {"type": "string", "enum": ["high", "medium", "low"]}},
            "required": ["action"]},
    }]


HYPGEN_SYS = (
    "You are the lead investigator of a clinical-trial pre-mortem. Given a draft protocol and a "
    "quantitative accrual-risk signal, produce the 2-3 MOST IMPORTANT, SPECIFIC failure hypotheses "
    "worth investigating for THIS design — not a generic checklist. Each hypothesis names a concrete "
    "mechanism of failure and which evidence source would confirm/refute it. Tailor to the drug, "
    "condition, endpoint, and eligibility in front of you."
)

INVESTIGATOR_SYS = (
    "You are a specialist investigator testing ONE failure hypothesis about a draft clinical trial. "
    "Use your tools to gather real evidence — call drug_mechanism (returns a chembl_id), then "
    "target_disease with that chembl_id to confirm the mechanism from a second source, plus "
    "literature and similar_trials as needed — then reach a grounded conclusion. Investigate to CONFIRM OR "
    "REFUTE; do not assume. CRITICAL: in record_finding you may ONLY cite PMIDs, NCT numbers, and "
    "ChEMBL mechanisms that literally appeared in a tool result you received this session — copy them "
    "verbatim. Do NOT cite any identifier from memory; if a tool didn't return it, you may not use it. "
    "An adversarial critic will check every identifier against your tool outputs and reject fabrications. "
    "When done, call record_finding. Mark supported=true if the MECHANISM of the risk is established "
    "by evidence (e.g. a drug's onset kinetics, an eligibility bottleneck) even without a paper naming "
    "this exact trial — you are assessing a design risk, not proving a past failure. Absence of a "
    "smoking-gun paper is not evidence the risk is absent."
)

CRITIC_SYS = (
    "You are an adversarial critic. For the finding below, check: (1) are the cited identifiers real "
    "(present in the investigator's tool results)? (2) does the evidence actually support the claim, "
    "or is it overstated? (3) is this a genuine v0-design flaw or a base-rate artifact? Decide a "
    "verdict: 'upheld' (evidence supports it), 'downgraded' (real but overstated — lower severity), "
    "or 'rejected' (unsupported / hallucinated citation). Give a one-sentence reason. Be strict."
)


def _hyp_gen(host, draft, risk, model=None):
    kw = {"model": model} if model else {}
    prompt = (f"Draft protocol:\n{json.dumps(draft, indent=1)}\n\n"
              f"Quantitative accrual-risk signal: {json.dumps(risk)}\n\n"
              "List 2-3 specific failure hypotheses. Return ONLY a JSON array of objects "
              '[{"id":"H1","failure_mode":"...","why_this_design":"...","evidence_to_check":"..."}].')
    prompt += "\nKeep each field to one sentence so the JSON fits. Emit at most 3."
    r = host.llm({"system": HYPGEN_SYS, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 1500, **kw})
    return _parse_hyp_array(r.get("text", ""))


def _parse_hyp_array(txt):
    """Robust parse of a possibly-truncated JSON array of hypothesis objects."""
    import re
    # strip code fences
    txt = txt.replace("```json", "").replace("```", "")
    # find the array start
    start = txt.find("[")
    if start < 0:
        return []
    body = txt[start:]
    try:
        return json.loads(body)
    except Exception:
        pass
    # truncated: extract complete {...} objects individually
    objs = []
    depth = 0; buf = ""
    for ch in body[1:]:
        if ch == "{":
            depth += 1
        if depth > 0:
            buf += ch
        if ch == "}":
            depth -= 1
            if depth == 0 and buf:
                try:
                    objs.append(json.loads(buf))
                except Exception:
                    pass
                buf = ""
    return objs


def _run_investigator(host, draft, hyp, dispatch, traj, model=None, max_steps=5):
    kw = {"model": model} if model else {}
    tools = investigator_tools()
    messages = [{"role": "user", "content":
                 f"{INVESTIGATOR_SYS}\n\nDraft:\n{json.dumps(draft)}\n\nHypothesis to test ({hyp['id']}): "
                 f"{hyp['failure_mode']}\nWhy relevant: {hyp.get('why_this_design','')}\n"
                 f"Evidence to check: {hyp.get('evidence_to_check','')}\n\nInvestigate and record_finding."}]
    finding = None
    retrieved = {}   # id -> short label, from ACTUAL tool outputs (real by construction)
    for step in range(max_steps):
        r = host.llm({"messages": messages, "tools": tools,
                      "max_tokens": 1000, **kw})
        content = r.get("content") or []
        calls = []
        for i, b in enumerate(content):
            if b.get("type") == "tool_use":
                b.setdefault("id", f"{hyp['id']}_{step}_{i}"); calls.append(b)
        messages.append({"role": "assistant", "content": content})
        if not calls:
            messages.append({"role": "user", "content": "Call a tool or record_finding."}); continue
        results = []
        for c in calls:
            # single dispatcher tool: the capability is in input['action']
            action = c["input"].get("action") if c["name"] == "investigate" else c["name"]
            if action == "record_finding":
                finding = c["input"]
                results.append({"type": "tool_result", "tool_use_id": c["id"], "content": "recorded"})
            else:
                obs = dispatch(action, c["input"])
                _collect_sources(action, obs, retrieved)
                traj.append({"hyp": hyp["id"], "step": step, "tool": action,
                             "args": c["input"], "obs_preview": json.dumps(obs)[:200]})
                results.append({"type": "tool_result", "tool_use_id": c["id"],
                                "content": json.dumps(obs)[:1800]})
        messages.append({"role": "user", "content": results})
        if finding is not None:
            break
        # running low on budget — tell the agent to wrap up
        if step == max_steps - 2:
            messages.append({"role": "user", "content":
                             "You have gathered enough evidence. Call record_finding now with your conclusion."})
    # budget exhausted without a finding -> force one final structured call
    if finding is None:
        messages.append({"role": "user", "content":
                         "Stop investigating. Call investigate with action='record_finding' now, "
                         "citing the specific evidence you already gathered."})
        r = host.llm({"messages": messages, "tools": tools,
                      "tool_choice": {"type": "tool", "name": "investigate"},
                      "max_tokens": 700, **kw})
        for b in (r.get("content") or []):
            if b.get("type") == "tool_use" and b.get("input", {}).get("action") == "record_finding":
                finding = b["input"]
    return finding, [m for m in messages], retrieved


def _critic(host, hyp, finding, investigator_msgs, model=None):
    kw = {"model": model} if model else {}
    # give critic the finding + a compact view of what tools actually returned
    tool_obs = [str(m["content"])[:600] for m in investigator_msgs
                if m["role"] == "user" and isinstance(m["content"], list)]
    prompt = (f"Hypothesis: {hyp['failure_mode']}\n\n"
              f"Investigator finding:\n{json.dumps(finding, indent=1)}\n\n"
              f"Tool observations the investigator saw:\n{chr(10).join(tool_obs)[:2000]}\n\n"
              'Return ONLY JSON {"verdict":"upheld|downgraded|rejected","reason":"...","final_severity":"high|medium|low"}.')
    r = host.llm({"system": CRITIC_SYS, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 300, **kw})
    import re
    m = re.search(r"\{.*\}", r.get("text", ""), re.S)
    try:
        return json.loads(m.group(0)) if m else {"verdict": "downgraded", "reason": "unparseable", "final_severity": "low"}
    except Exception:
        return {"verdict": "downgraded", "reason": "unparseable", "final_severity": "low"}


import re as _re

_ID_PATTERNS = [
    (_re.compile(r"\bPMID[:\s]*?(\d{6,9})\b", _re.I), "PMID"),
    (_re.compile(r"\b(NCT\d{8})\b"), "NCT"),
    (_re.compile(r"\b(CHEMBL\d+)\b", _re.I), "CHEMBL"),
]


def _extract_ids(text):
    ids = set()
    for pat, _ in _ID_PATTERNS:
        for m in pat.findall(text or ""):
            ids.add(m.upper() if not m.isdigit() else m)
    return ids


def _collect_sources(tool_name, obs, retrieved):
    """Record the real identifiers + labels returned by a tool call, keyed by id.
    These are real by construction — used to build the register's citation list."""
    if not isinstance(obs, dict):
        return
    if tool_name == "literature":
        for a in obs.get("articles", []):
            if a.get("pmid"):
                retrieved[f"PMID:{a['pmid']}"] = (a.get("title") or "")[:120]
    elif tool_name == "similar_trials":
        for t in obs.get("trials", []):
            if t.get("nct"):
                lbl = (t.get("title") or "")[:80]
                if t.get("status"):
                    lbl += f" [{t['status']}]"
                retrieved[t["nct"]] = lbl
    elif tool_name == "drug_mechanism":
        mech = obs.get("mechanisms") or []
        if obs.get("chembl_id") and mech and mech[0].get("mechanism"):
            retrieved[obs["chembl_id"]] = mech[0]["mechanism"]
    elif tool_name == "target_disease":
        # only count as a real source if Open Targets actually returned mechanism data;
        # an empty {mechanisms: []} record (e.g. a wrong chembl_id) is NOT evidence
        mech = obs.get("mechanisms") or []
        if obs.get("chembl_id") and mech and mech[0].get("mechanism"):
            retrieved[obs["chembl_id"]] = mech[0]["mechanism"]


def _normalize_retrieved(retrieved):
    """Turn the retrieved-sources dict (keys like 'PMID:22008735','NCT..','CHEMBL..')
    into the bare-id set that _extract_ids produces from prose, for comparison."""
    seen = set()
    for k in retrieved:
        if k.upper().startswith("PMID:"):
            seen.add(k.split(":", 1)[1])
        else:
            seen.add(k.upper())
    return seen


def _verify_citations(finding, retrieved):
    """Verify identifiers the LLM typed into its finding prose against the set of
    identifiers ACTUALLY returned by tools (real by construction). Any id the LLM
    cited that was never retrieved is fabricated and gets stripped from the prose.
    Returns (verified_ids, fabricated_ids, scrubbed_finding)."""
    seen = _normalize_retrieved(retrieved)
    cited = _extract_ids(finding.get("evidence", "")) | _extract_ids(finding.get("claim", ""))
    fabricated = {c for c in cited if c not in seen}
    verified = cited & seen
    f = dict(finding)
    if fabricated:
        note = " [CITATION GATE: removed unverified id(s) " + ", ".join(sorted(fabricated)) + \
               " — never returned by any tool]"
        ev = f.get("evidence", "")
        for fab in fabricated:
            ev = _re.sub(_re.escape(fab), "[unverified-removed]", ev)
        f["evidence"] = ev + note
    f["_verified_ids"] = sorted(verified)
    f["_fabricated_ids"] = sorted(fabricated)
    return verified, fabricated, f


def run_premortem(host, draft, cached_tools, dispatch, model=None, verbose=True):
    """Full pipeline. `cached_tools` = precomputed numpy outputs (score_risk, peer_norms,
    find_failed_analogues, simulate_fix). `dispatch(name, args)` runs a live connector tool."""
    trajectory = []
    risk = cached_tools["score_risk"]
    if verbose: print(f"[triage] ML accrual risk = {risk['risk_score']} | {risk['drivers'][0][:70]}")
    hyps = _hyp_gen(host, draft, risk, model=model)
    if verbose:
        print(f"[hypotheses] generated {len(hyps)}:")
        for h in hyps: print(f"   {h['id']}: {h['failure_mode'][:80]}")
    blackboard = []
    for h in hyps:
        if verbose: print(f"\n[investigate {h['id']}] {h['failure_mode'][:70]}")
        finding, msgs, retrieved = _run_investigator(host, draft, h, dispatch, trajectory, model=model)
        if finding is None:
            if verbose: print(f"   (no conclusion)")
            continue
        # PROGRAMMATIC CITATION GATE — verify LLM-typed ids against what tools actually returned
        verified, fabricated, finding = _verify_citations(finding, retrieved)
        crit = _critic(host, h, finding, msgs, model=model)
        # sources = real identifiers the investigator ACTUALLY retrieved (real by construction).
        # A finding ships only if the LLM's prose cited >=1 id that was genuinely retrieved
        # (verified) — i.e. its stated evidence is grounded, not merely that some tool ran.
        sources = [{"id": k, "label": v} for k, v in retrieved.items()]
        citation_ok = len(verified) > 0
        if verbose:
            fab_note = f" [!{len(fabricated)} fabricated id(s) stripped]" if fabricated else ""
            print(f"   finding: {'SUPPORTED' if finding.get('supported') else 'not supported'} "
                  f"({finding.get('severity')}) -> critic: {crit['verdict'].upper()} ({crit.get('final_severity')})"
                  f" | {len(verified)} verified / {len(sources)} retrieved{fab_note}")
            print(f"   claim: {finding.get('claim','')[:100]}")
        blackboard.append({"hypothesis": h, "finding": finding, "critic": crit,
                           "citation_ok": citation_ok, "sources": sources})
    # synthesis: keep upheld/downgraded, drop rejected AND drop findings with no verified citation
    order = {"high": 0, "medium": 1, "low": 2}
    kept = [b for b in blackboard if b["critic"]["verdict"] != "rejected"
            and b["finding"].get("supported") and b["citation_ok"]]
    kept.sort(key=lambda b: order.get(b["critic"].get("final_severity", "low"), 3))
    register = []
    for rank, b in enumerate(kept, 1):
        register.append({
            "rank": rank, "failure_mode": b["hypothesis"]["failure_mode"],
            "severity": b["critic"].get("final_severity"),
            "claim": b["finding"]["claim"], "reasoning": b["finding"]["evidence"],
            # sources are real by construction — captured from actual tool outputs, not LLM text
            "sources": b["sources"],
            "critic_verdict": b["critic"]["verdict"], "critic_reason": b["critic"]["reason"],
        })
    rejected = [b for b in blackboard if b["critic"]["verdict"] == "rejected"]
    return {"draft": draft, "ml_risk": risk, "hypotheses": hyps,
            "register": register, "rejected_findings": rejected,
            "counterfactual": cached_tools.get("simulate_fix"),
            "trajectory": trajectory}
