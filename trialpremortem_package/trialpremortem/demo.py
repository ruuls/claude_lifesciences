"""TrialPremortem — live demo CLI.

Two modes:
  --replay   Play back a saved agentic run instantly (no network / no API keys).
             This is the demo-day path: deterministic, ~10s, works offline.
  --live     Run the autonomous harness for real against live connectors + LLM
             (needs `host` in scope, i.e. run inside the Claude Science repl kernel).

Usage:
    python -m trialpremortem.demo --replay
    python -m trialpremortem.demo --replay --run data/agentic_harness_demo.json
    # live (from a repl cell):  from trialpremortem.demo import live; live(host)
"""
from __future__ import annotations
import json, sys, time, argparse, os

# ---- tiny ANSI helpers (degrade to plain text if not a tty) ----------------
_TTY = sys.stdout.isatty()
def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s
def bold(s):  return _c("1", s)
def dim(s):   return _c("2", s)
def cyan(s):  return _c("36", s)
def green(s): return _c("32", s)
def yellow(s):return _c("33", s)
def red(s):   return _c("31", s)
def mag(s):   return _c("35", s)

def _pause(sec, fast):
    if not fast:
        time.sleep(sec)

def _rule(char="─", n=68):
    print(dim(char * n))


def render(run, fast=False):
    """Render a saved agentic run as a watchable terminal demo."""
    draft = run["draft"]
    print()
    _rule("━")
    print(bold("  TRIALPREMORTEM — autonomous protocol pre-mortem"))
    _rule("━")
    print(f"  {bold('Draft under review:')} {draft.get('cond')} / {draft.get('phase','')}")
    print(f"  Drug: {draft.get('drug','?')}  |  Primary endpoint: {draft.get('primary_endpoint','?')}")
    print(f"  Design: {draft.get('n_incl','?')} incl / {draft.get('n_excl','?')} excl criteria, "
          f"n={draft.get('enroll_target','?')}, {draft.get('n_arms','?')} arms")
    _pause(1.2, fast)

    # 1. triage
    print()
    print(bold("① TRIAGE — validated ML accrual-risk engine (backtested AUC 0.67)"))
    risk = run["ml_risk"]
    print(f"   risk score: {yellow(str(risk['risk_score']))}   {dim(risk['drivers'][0][:64])}")
    _pause(1.2, fast)

    # 2. hypotheses
    print()
    print(bold(f"② HYPOTHESIS GENERATION — {len(run['hypotheses'])} draft-specific failure modes"))
    for h in run["hypotheses"]:
        print(f"   {cyan(h['id'])}: {h['failure_mode'][:70]}")
        _pause(0.4, fast)
    _pause(0.8, fast)

    # 3. investigation trajectory (the agency beat)
    print()
    print(bold("③ AUTONOMOUS INVESTIGATION — each hypothesis gets its own tool-use loop"))
    print(dim("   (the agent chooses which biomedical connectors to call, and when)"))
    by_hyp = {}
    for t in run["trajectory"]:
        by_hyp.setdefault(t["hyp"], []).append(t)
    tool_color = {"drug_mechanism": mag, "target_disease": mag,
                  "literature": cyan, "similar_trials": green, "regulatory_precedent": yellow}
    for hid, steps in by_hyp.items():
        print(f"\n   {cyan(hid)} — {len(steps)} tool calls:")
        for t in steps:
            col = tool_color.get(t["tool"], dim)
            args = json.dumps(t["args"])
            args = args[:52] + "…" if len(args) > 52 else args
            ok = "unavailable" not in t["obs_preview"] and '"mechanisms": []' not in t["obs_preview"] and '"n": 0' not in t["obs_preview"]
            mark = green("✓") if ok else dim("·")
            print(f"     {mark} {col(t['tool']):<28} {dim(args)}")
            _pause(0.18, fast)
    _pause(0.8, fast)

    # 4. critic + register (the trust beat)
    print()
    print(bold("④ ADVERSARIAL CRITIC + CITATION GATE → ranked failure-mode register"))
    print(dim("   (every cited PMID/NCT/ChEMBL id is verified present in real tool output)"))
    beats = run.get("_demo_beats", {})
    if beats.get("critic_action"):
        print(dim(f"   {beats['critic_action']}"))
    print()
    for r in run["register"]:
        sev = {"high": red, "medium": yellow, "low": dim}.get(r["severity"], dim)
        print(f"   {bold('#'+str(r['rank']))} [{sev(r['severity'].upper())}] {r['failure_mode'][:60]}")
        reasoning = r.get("reasoning") or r.get("evidence", "")
        print(f"      {dim(reasoning[:150])}")
        srcs = r.get("sources", [])
        src_ids = ", ".join(s["id"] for s in srcs[:4])
        more = f" +{len(srcs)-4} more" if len(srcs) > 4 else ""
        print(f"      {green('sources:')} {len(srcs)} real  {dim(src_ids+more)}")
        print(f"      {mag('critic:')} {r['critic_verdict']} — {dim((r.get('critic_reason') or '')[:70])}")
        print()
        _pause(0.6, fast)

    # 5. counterfactual
    cf = run.get("counterfactual")
    if cf and cf.get("scenarios"):
        print(bold("⑤ COUNTERFACTUAL — what design change lowers the risk most?"))
        base = cf.get("baseline_risk")
        best = cf["scenarios"][0]
        print(f"   baseline risk {yellow(str(base))} → {green(str(best['new_risk']))}  "
              f"via: {best['edit']}")
        print()
    _rule("━")
    dropped = len(run.get("rejected_findings", []))
    print(f"  {green('✓')} agentic run complete — "
          f"{len(run['hypotheses'])} hypotheses investigated, "
          f"{len(run['register'])} shipped, {dropped} rejected by critic")
    _rule("━")
    print()


def replay(path="data/agentic_harness_demo.json", fast=False):
    run = json.load(open(path))
    render(run, fast=fast)
    return run


def live(host, draft=None, path="data/agentic_harness_demo.json"):
    """Run the harness for real (needs host in scope). Falls back to replay-render at the end."""
    import gzip, pickle
    from .predict.predictor import RiskEngine
    from .predict.whatif import whatif
    from .agent.tools import ToolBox  # noqa
    from .agent.orchestrator_run import run as run_harness
    # locate risk model + cohort as artifacts if paths not local
    eng = RiskEngine(host.artifact_path("b3aaba30-d03b-45f2-b4d0-0440129eaa48"))
    if draft is None:
        draft = json.load(open(path))["draft"]
    # precompute numpy tool outputs
    with gzip.open(host.artifact_path("0152f48d-eb76-4c2f-a041-83d34b6bafde"), "rb") as f:
        cohort = pickle.load(f)
    tb = ToolBox(eng, cohort)
    cached = {"draft": draft, "score_risk": tb.score_risk(draft),
              "peer_norms": tb.base_rate(draft["cond"], draft.get("phase", "")),
              "simulate_fix": whatif(eng, draft)}
    run = run_harness(host, draft, cached, verbose=True)
    render(run, fast=True)
    return run


def web(run_path="data/agentic_harness_demo.json", out_path=None, open_browser=True):
    """Build the self-contained HTML web demo from a saved run and (optionally) open it.

    This is the polished, screen-shareable playback: an animated 'instrument readout'
    of the same run the terminal --replay renders. Fully offline, no external assets.
    """
    from . import webdemo
    if out_path is None:
        out_path = os.path.join(os.path.dirname(run_path) or ".", "trialpremortem_demo.html")
    path = webdemo.write(run_path, out_path)
    print(f"{green('✓')} web demo written: {path}")
    print(f"  open it in any browser: file://{path}")
    if open_browser:
        try:
            import webbrowser
            webbrowser.open(f"file://{path}")
        except Exception:
            pass
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="TrialPremortem demo — terminal replay or web UI.")
    ap.add_argument("--replay", action="store_true", help="play back a saved run in the terminal (offline)")
    ap.add_argument("--web", action="store_true", help="build the animated HTML web demo and open it")
    ap.add_argument("--out", default=None, help="output path for --web (default: alongside the run JSON)")
    ap.add_argument("--no-open", action="store_true", help="with --web, don't try to open a browser")
    ap.add_argument("--fast", action="store_true", help="no pauses (terminal replay)")
    ap.add_argument("--run", default="data/agentic_harness_demo.json", help="path to saved run JSON")
    args = ap.parse_args()
    if not os.path.exists(args.run):
        print(f"saved run not found: {args.run}", file=sys.stderr); sys.exit(1)
    if args.web:
        web(args.run, args.out, open_browser=not args.no_open)
    else:  # default to terminal replay when invoked directly
        replay(args.run, fast=args.fast)
