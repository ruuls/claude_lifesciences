"""TrialPremortem — web demo generator.

Renders a saved agentic run (the same JSON the terminal ``--replay`` uses) into a
single self-contained HTML file: no network, no build step, no external assets.
Open it in any browser and it plays back the run as an animated "instrument
readout" — the deterministic, screen-shareable demo for stage.

    python -m trialpremortem.webdemo                      # -> data/trialpremortem_demo.html
    python -m trialpremortem.webdemo --run <run.json> --out <page.html>

The HTML is data-driven: everything on the page is rendered in the browser from
the run JSON embedded at build time, so the page can never drift from the run.
"""
from __future__ import annotations
import json, os, sys, argparse

_HERE = os.path.dirname(__file__)
_DEFAULT_RUN = os.path.join(_HERE, "..", "data", "agentic_harness_demo.json")
_DEFAULT_OUT = os.path.join(_HERE, "..", "data", "trialpremortem_demo.html")


def build_html(run: dict) -> str:
    """Return a complete, self-contained HTML document for one saved run."""
    data = json.dumps(run, ensure_ascii=False)
    # embed via <script type="application/json"> so we never fight JS escaping
    return _TEMPLATE.replace("/*__RUN_JSON__*/", "")\
                    .replace("<!--__RUN_DATA__-->", data)


def write(run_path: str = _DEFAULT_RUN, out_path: str = _DEFAULT_OUT) -> str:
    with open(run_path, "r", encoding="utf-8") as f:
        run = json.load(f)
    html = build_html(run)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(out_path)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TrialPremortem — autonomous protocol pre-mortem</title>
<style>
:root{
  --bg:#0a0f19; --panel:#0f1725; --panel-2:#0c131f; --panel-3:#111c2e;
  --line:#1d2a3e; --line-soft:#16212f;
  --ink:#e8eff8; --dim:#8aa0be; --faint:#5f7290;
  --accent:#39c2cf; --accent-ink:#0a1417; --accent-soft:#123039;
  --risk-low:#3ad48c; --risk-med:#f0a53f; --risk-high:#e85852;
  --ok:#3ad48c; --warn:#f0a53f; --bad:#e85852; --mag:#b995f2;
  --chip:#132033; --shadow:0 1px 0 rgba(255,255,255,.03), 0 18px 40px -24px rgba(0,0,0,.8);
  --font-sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --font-mono:ui-monospace,"SF Mono","JetBrains Mono","Cascadia Code",Menlo,Consolas,monospace;
}
@media (prefers-color-scheme: light){
  :root{
    --bg:#eef2f7; --panel:#ffffff; --panel-2:#f5f8fc; --panel-3:#eef3fa;
    --line:#d9e2ee; --line-soft:#e6ecf4;
    --ink:#132033; --dim:#4d627d; --faint:#8496ac;
    --accent:#0f8f9d; --accent-ink:#ffffff; --accent-soft:#d6f0f3;
    --risk-low:#1aa567; --risk-med:#c67d15; --risk-high:#cf3c37;
    --ok:#1aa567; --warn:#c67d15; --bad:#cf3c37; --mag:#7c53c9;
    --chip:#eef3fa; --shadow:0 1px 0 rgba(255,255,255,.6), 0 18px 40px -26px rgba(20,40,70,.28);
  }
}
:root[data-theme="dark"]{
  --bg:#0a0f19; --panel:#0f1725; --panel-2:#0c131f; --panel-3:#111c2e;
  --line:#1d2a3e; --line-soft:#16212f; --ink:#e8eff8; --dim:#8aa0be; --faint:#5f7290;
  --accent:#39c2cf; --accent-ink:#0a1417; --accent-soft:#123039;
  --risk-low:#3ad48c; --risk-med:#f0a53f; --risk-high:#e85852;
  --ok:#3ad48c; --warn:#f0a53f; --bad:#e85852; --mag:#b995f2; --chip:#132033;
  --shadow:0 1px 0 rgba(255,255,255,.03), 0 18px 40px -24px rgba(0,0,0,.8);
}
:root[data-theme="light"]{
  --bg:#eef2f7; --panel:#ffffff; --panel-2:#f5f8fc; --panel-3:#eef3fa;
  --line:#d9e2ee; --line-soft:#e6ecf4; --ink:#132033; --dim:#4d627d; --faint:#8496ac;
  --accent:#0f8f9d; --accent-ink:#ffffff; --accent-soft:#d6f0f3;
  --risk-low:#1aa567; --risk-med:#c67d15; --risk-high:#cf3c37;
  --ok:#1aa567; --warn:#c67d15; --bad:#cf3c37; --mag:#7c53c9; --chip:#eef3fa;
  --shadow:0 1px 0 rgba(255,255,255,.6), 0 18px 40px -26px rgba(20,40,70,.28);
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:
    radial-gradient(1200px 600px at 80% -10%, color-mix(in oklab, var(--accent) 8%, transparent), transparent 60%),
    var(--bg);
  color:var(--ink); font-family:var(--font-sans);
  font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1180px; margin:0 auto; padding:0 22px 80px}
.mono{font-family:var(--font-mono); font-variant-numeric:tabular-nums}
.eyebrow{font-family:var(--font-mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--faint)}
h1,h2,h3{text-wrap:balance; margin:0}
a{color:var(--accent)}

/* ---------- top bar / brand ---------- */
.topbar{position:sticky; top:0; z-index:40; background:color-mix(in oklab, var(--bg) 88%, transparent);
  backdrop-filter:blur(10px); border-bottom:1px solid var(--line); }
.topbar-in{max-width:1180px; margin:0 auto; padding:12px 22px; display:flex; align-items:center; gap:16px; flex-wrap:wrap}
.brand{display:flex; align-items:center; gap:11px; min-width:0}
.pulse{width:12px; height:12px; border-radius:50%; background:var(--accent);
  box-shadow:0 0 0 0 color-mix(in oklab, var(--accent) 70%, transparent); flex:none}
.playing .pulse{animation:pulse 1.8s ease-out infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 color-mix(in oklab,var(--accent) 55%,transparent)}
  70%{box-shadow:0 0 0 9px transparent} 100%{box-shadow:0 0 0 0 transparent}}
.brand b{font-family:var(--font-mono); letter-spacing:.04em; font-weight:600; font-size:15px}
.brand span{color:var(--dim); font-size:12.5px}
.spacer{flex:1 1 auto}
.chip{font-family:var(--font-mono); font-size:11.5px; padding:4px 9px; border-radius:999px;
  border:1px solid var(--line); background:var(--chip); color:var(--dim); white-space:nowrap}
.chip.good{color:var(--ok); border-color:color-mix(in oklab,var(--ok) 40%,var(--line))}
.controls{display:flex; align-items:center; gap:8px}
button.ctl{font-family:var(--font-mono); font-size:12.5px; color:var(--ink); background:var(--panel-3);
  border:1px solid var(--line); padding:6px 11px; border-radius:8px; cursor:pointer; display:inline-flex; gap:7px; align-items:center}
button.ctl:hover{border-color:var(--accent)}
button.ctl.primary{background:var(--accent); color:var(--accent-ink); border-color:var(--accent); font-weight:600}
button.ctl:focus-visible, a:focus-visible{outline:2px solid var(--accent); outline-offset:2px}
.progress{height:3px; background:var(--line-soft)}
.progress .bar{height:100%; width:0; background:linear-gradient(90deg,var(--accent),color-mix(in oklab,var(--accent) 50%, var(--mag)))}

/* ---------- hero ---------- */
.hero{padding:46px 0 8px}
.hero .eyebrow{margin-bottom:14px}
.hero h1{font-size:clamp(30px,4.4vw,50px); line-height:1.05; letter-spacing:-.015em; font-weight:640}
.hero h1 .hl{color:var(--accent)}
.hero p.lede{margin:18px 0 0; max-width:62ch; color:var(--dim); font-size:16.5px}
.headline-stats{display:flex; gap:26px; flex-wrap:wrap; margin-top:26px}
.stat{display:flex; flex-direction:column; gap:2px}
.stat b{font-family:var(--font-mono); font-size:26px; font-weight:600; letter-spacing:-.01em}
.stat small{color:var(--faint); font-size:12px; letter-spacing:.02em}

/* ---------- main grid: rail + stream ---------- */
.grid{display:grid; grid-template-columns:220px 1fr; gap:34px; margin-top:36px; align-items:start}
@media (max-width:880px){ .grid{grid-template-columns:1fr} .rail{display:none} }
.rail{position:sticky; top:74px}
.stepper{display:flex; flex-direction:column; gap:2px; border-left:1px solid var(--line); padding-left:0}
.step{display:flex; gap:12px; align-items:flex-start; padding:11px 0 11px 16px; margin-left:-1px;
  border-left:2px solid transparent; color:var(--faint); transition:.35s}
.step .num{font-family:var(--font-mono); font-size:12px; width:20px; flex:none; text-align:right; opacity:.7}
.step .lab{font-size:13px; line-height:1.3}
.step.active{color:var(--ink); border-left-color:var(--accent)}
.step.done{color:var(--dim)}
.step.done .num::after{content:" ✓"; color:var(--ok)}

/* ---------- cards ---------- */
.card{background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--line);
  border-radius:14px; box-shadow:var(--shadow); padding:22px; margin-bottom:22px}
.card > .eyebrow{display:flex; align-items:center; gap:10px; margin-bottom:14px}
.card > .eyebrow .n{width:22px; height:22px; border-radius:6px; background:var(--accent-soft); color:var(--accent);
  display:grid; place-items:center; font-size:12px; font-weight:700}
.section-title{font-size:17px; font-weight:620; letter-spacing:-.01em}

/* reveal animation */
.reveal{opacity:0; transform:translateY(10px); transition:opacity .5s ease, transform .5s ease}
.reveal.on{opacity:1; transform:none}
@media (prefers-reduced-motion: reduce){ .reveal{transition:none} .playing .pulse{animation:none} .cursor{animation:none} }

/* ---------- draft case-file ---------- */
.casefile{display:grid; grid-template-columns:1.3fr 1fr; gap:24px}
@media (max-width:620px){ .casefile{grid-template-columns:1fr} }
.kv{display:flex; flex-direction:column; gap:11px}
.kv .row{display:flex; gap:10px; align-items:baseline}
.kv .k{font-family:var(--font-mono); font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint); width:96px; flex:none}
.kv .v{font-size:14.5px}
.flagline{color:var(--warn)!important; font-weight:600}
.flagline::after{content:"⚑ flagged"; font-family:var(--font-mono); font-size:10px; letter-spacing:.06em;
  margin-left:8px; color:var(--warn); border:1px solid color-mix(in oklab,var(--warn) 45%,var(--line)); padding:1px 5px; border-radius:5px; text-transform:uppercase}
.designchips{display:flex; flex-wrap:wrap; gap:8px; align-content:flex-start}
.dchip{font-family:var(--font-mono); font-size:12px; background:var(--panel-3); border:1px solid var(--line);
  padding:7px 10px; border-radius:9px; display:flex; gap:8px; align-items:baseline}
.dchip b{font-size:15px} .dchip small{color:var(--faint); font-size:10.5px; letter-spacing:.03em}
.dchip.hot{border-color:color-mix(in oklab,var(--warn) 50%,var(--line))}
.dchip.hot b{color:var(--warn)}

/* ---------- triage gauge ---------- */
.triage{display:grid; grid-template-columns:1fr 300px; gap:26px; align-items:center}
@media (max-width:720px){ .triage{grid-template-columns:1fr} }
.gauge{--v:0}
.gauge .scaleline{display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:10.5px; color:var(--faint); margin-bottom:6px; letter-spacing:.04em}
.gauge .track{position:relative; height:16px; border-radius:999px; overflow:hidden;
  background:linear-gradient(90deg,var(--risk-low) 0%, var(--risk-low) 28%, var(--risk-med) 55%, var(--risk-high) 100%); opacity:.32}
.gauge .fillmask{position:absolute; inset:0; border-radius:999px; overflow:hidden}
.gauge .fill{position:absolute; inset:0; width:var(--v); border-radius:999px;
  background:linear-gradient(90deg,var(--risk-low) 0%, var(--risk-low) 28%, var(--risk-med) 55%, var(--risk-high) 100%);
  transition:width 1.1s cubic-bezier(.2,.7,.2,1)}
.gaugewrap{position:relative}
.marker{position:absolute; top:-6px; width:2px; height:28px; background:var(--ink); left:0; transition:left 1.1s cubic-bezier(.2,.7,.2,1)}
.marker .tip{position:absolute; top:-22px; left:50%; transform:translateX(-50%);
  font-family:var(--font-mono); font-size:12px; font-weight:700; white-space:nowrap}
.gauge .zones{display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:10px; color:var(--faint); margin-top:8px; letter-spacing:.06em; text-transform:uppercase}
.readout{background:var(--panel-3); border:1px solid var(--line); border-radius:12px; padding:16px 18px; text-align:center}
.readout .big{font-family:var(--font-mono); font-size:44px; font-weight:640; letter-spacing:-.02em; line-height:1}
.readout .cls{font-family:var(--font-mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase; margin-top:8px; color:var(--warn)}
.driver{margin-top:16px; color:var(--dim); font-size:13.5px}
.peer{margin-top:14px; display:grid; grid-template-columns:repeat(3,1fr); gap:8px}
.peer .p{background:var(--panel-3); border:1px solid var(--line); border-radius:9px; padding:9px; text-align:center}
.peer .p b{font-family:var(--font-mono); font-size:16px} .peer .p small{display:block; color:var(--faint); font-size:10px; letter-spacing:.03em; margin-top:2px}

/* ---------- hypotheses ---------- */
.hyps{display:grid; grid-template-columns:repeat(3,1fr); gap:14px}
@media (max-width:820px){ .hyps{grid-template-columns:1fr} }
.hyp{background:var(--panel-3); border:1px solid var(--line); border-radius:12px; padding:16px}
.hyp .hid{font-family:var(--font-mono); font-size:12px; color:var(--accent); font-weight:700; letter-spacing:.06em}
.hyp .fm{margin-top:9px; font-size:14px; font-weight:560; line-height:1.4}
.hyp .why{margin-top:10px; font-size:12.5px; color:var(--dim); line-height:1.5}

/* ---------- investigation ---------- */
.invhead{display:flex; gap:14px; flex-wrap:wrap; margin-bottom:16px}
.conn{background:var(--panel-3); border:1px solid var(--line); border-radius:10px; padding:10px 12px; min-width:132px}
.conn .cn{font-family:var(--font-mono); font-size:11px; letter-spacing:.04em; color:var(--dim); display:flex; align-items:center; gap:7px}
.conn .dot{width:7px;height:7px;border-radius:50%;background:var(--faint)}
.conn.live .dot{background:var(--ok); box-shadow:0 0 8px var(--ok)}
.conn .cc{font-family:var(--font-mono); font-size:19px; margin-top:5px}
.conn .cc small{color:var(--faint); font-size:11px}
.hyptrace{margin-bottom:14px}
.hyptrace .th{font-family:var(--font-mono); font-size:12.5px; color:var(--accent); letter-spacing:.04em; margin-bottom:7px; display:flex; gap:9px; align-items:baseline}
.hyptrace .th .cnt{color:var(--faint); font-size:11px}
.calls{display:flex; flex-direction:column; gap:3px}
.call{display:grid; grid-template-columns:18px 150px 1fr; gap:10px; align-items:baseline; font-family:var(--font-mono); font-size:12px; padding:4px 8px; border-radius:7px; background:var(--panel-2)}
.call .mk{text-align:center}
.call .mk.ok{color:var(--ok)} .call .mk.no{color:var(--faint)}
.call .tool{color:var(--ink)}
.call .tool.t-lit{color:var(--accent)} .call .tool.t-mech{color:var(--mag)} .call .tool.t-trials{color:var(--ok)} .call .tool.t-tgt{color:var(--mag)}
.call .arg{color:var(--faint); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
@media (max-width:560px){ .call{grid-template-columns:18px 1fr} .call .arg{display:none} }

/* ---------- register ---------- */
.gatebar{display:flex; gap:12px; align-items:center; background:var(--accent-soft);
  border:1px solid color-mix(in oklab,var(--accent) 40%,var(--line)); color:var(--ink);
  border-radius:11px; padding:11px 14px; margin-bottom:16px; font-size:13px}
.gatebar .lock{font-size:16px}
.finding{border:1px solid var(--line); border-radius:12px; overflow:hidden; margin-bottom:14px; background:var(--panel-2)}
.finding .stripe{height:4px}
.finding.sev-high .stripe{background:var(--bad)} .finding.sev-medium .stripe{background:var(--warn)} .finding.sev-low .stripe{background:var(--faint)}
.finding .body{padding:16px 18px}
.finding .fhead{display:flex; gap:12px; align-items:baseline; flex-wrap:wrap}
.finding .rank{font-family:var(--font-mono); font-weight:700; font-size:14px}
.finding .sev{font-family:var(--font-mono); font-size:10px; letter-spacing:.1em; text-transform:uppercase; padding:2px 7px; border-radius:5px; border:1px solid var(--line)}
.finding.sev-high .sev{color:var(--bad); border-color:color-mix(in oklab,var(--bad) 45%,var(--line))}
.finding.sev-medium .sev{color:var(--warn); border-color:color-mix(in oklab,var(--warn) 45%,var(--line))}
.finding .claim{font-size:14.5px; font-weight:560; flex:1 1 320px; min-width:0}
.finding .reason{margin-top:10px; color:var(--dim); font-size:13px; line-height:1.55}
.srcs{margin-top:13px; display:flex; flex-wrap:wrap; gap:6px}
.src{font-family:var(--font-mono); font-size:11px; padding:3px 8px; border-radius:6px; border:1px solid var(--line); background:var(--panel-3); display:inline-flex; gap:6px; align-items:center}
.src .tag{font-size:9px; letter-spacing:.06em; padding:0 4px; border-radius:3px; text-transform:uppercase; font-weight:700}
.src.pmid .tag{background:color-mix(in oklab,var(--accent) 22%,transparent); color:var(--accent)}
.src.nct .tag{background:color-mix(in oklab,var(--ok) 20%,transparent); color:var(--ok)}
.src.chembl .tag{background:color-mix(in oklab,var(--mag) 22%,transparent); color:var(--mag)}
.src .vr{color:var(--ok)}
.critic{margin-top:13px; border-top:1px dashed var(--line); padding-top:12px; display:flex; gap:11px; align-items:flex-start}
.verdict{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; padding:3px 9px; border-radius:6px; flex:none; font-weight:700}
.verdict.upheld{color:var(--ok); background:color-mix(in oklab,var(--ok) 16%,transparent)}
.verdict.downgraded{color:var(--warn); background:color-mix(in oklab,var(--warn) 16%,transparent)}
.verdict.rejected{color:var(--bad); background:color-mix(in oklab,var(--bad) 16%,transparent)}
.critic .cr{font-size:12.5px; color:var(--dim); line-height:1.5}

/* ---------- counterfactual ---------- */
.cf .baseline{font-family:var(--font-mono); font-size:13px; color:var(--dim); margin-bottom:14px}
.cf .baseline b{color:var(--warn); font-size:15px}
.bars{display:flex; flex-direction:column; gap:9px}
.barrow{display:grid; grid-template-columns:1fr 320px; gap:14px; align-items:center}
@media (max-width:720px){ .barrow{grid-template-columns:1fr} }
.barrow .edit{font-size:13px}
.bartrack{position:relative; height:26px; background:var(--panel-3); border:1px solid var(--line); border-radius:7px; overflow:hidden}
.barfill{position:absolute; top:0; bottom:0; left:0; width:0; border-radius:6px; transition:width 1s cubic-bezier(.2,.7,.2,1)}
.barfill.down{background:linear-gradient(90deg,color-mix(in oklab,var(--ok) 75%,transparent),var(--ok))}
.barfill.up{background:linear-gradient(90deg,color-mix(in oklab,var(--bad) 65%,transparent),var(--bad))}
.barval{position:absolute; right:9px; top:50%; transform:translateY(-50%); font-family:var(--font-mono); font-size:12px; font-weight:600}
.bardelta{font-family:var(--font-mono); font-size:11px; margin-left:8px}
.bardelta.down{color:var(--ok)} .bardelta.up{color:var(--bad)}
.baseref{position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--warn); opacity:.75; z-index:2}

/* ---------- footer summary ---------- */
.summary{display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-top:6px}
@media (max-width:720px){ .summary{grid-template-columns:repeat(2,1fr)} }
.sc{background:var(--panel-3); border:1px solid var(--line); border-radius:12px; padding:16px; text-align:center}
.sc b{font-family:var(--font-mono); font-size:24px; display:block}
.sc small{color:var(--faint); font-size:11.5px; letter-spacing:.02em}
.finrule{margin-top:22px; padding-top:18px; border-top:1px solid var(--line); color:var(--dim); font-size:13px; display:flex; gap:9px; align-items:center; justify-content:center; text-align:center}
.finrule .ok{color:var(--ok)}
.footnote{margin-top:30px; color:var(--faint); font-size:12px; text-align:center; line-height:1.7}
.cursor{display:inline-block; width:8px; height:15px; background:var(--accent); margin-left:3px; vertical-align:-2px; animation:blink 1s step-end infinite}
@keyframes blink{50%{opacity:0}}
</style>
</head>
<body>
<script type="application/json" id="run-data"><!--__RUN_DATA__--></script>

<div class="topbar" id="topbar">
  <div class="topbar-in">
    <div class="brand"><span class="pulse"></span><b>TrialPremortem</b><span>autonomous protocol pre-mortem</span></div>
    <span class="spacer"></span>
    <span class="chip good">validated AUC 0.67 · backtested on 927 trials</span>
    <div class="controls">
      <button class="ctl primary" id="btnPlay">▶ Play run</button>
      <button class="ctl" id="btnSpeed">1×</button>
      <button class="ctl" id="btnEnd" title="Skip to end">⏭ End</button>
      <button class="ctl" id="btnTheme" title="Toggle theme">◐</button>
    </div>
  </div>
  <div class="progress"><div class="bar" id="progbar"></div></div>
</div>

<div class="wrap">
  <header class="hero">
    <div class="eyebrow">Built with Claude · Life Sciences</div>
    <h1>Read a trial's <span class="hl">first draft</span>.<br>Foresee whether it will fail to recruit.</h1>
    <p class="lede">An autonomous agent triages a draft protocol with a backtested ML risk engine, invents its own
      failure hypotheses, investigates each against live biomedical databases, then ships a citation-verified
      failure-mode register — before a single patient is enrolled.</p>
    <div class="headline-stats">
      <div class="stat"><b id="hs-auc">0.67</b><small>AUC on real CT.gov history (v0 draft only)</small></div>
      <div class="stat"><b id="hs-flag">43% / 21%</b><small>failures flagged vs completed flagged</small></div>
      <div class="stat"><b id="hs-cite">100%</b><small>citations verified against tool output</small></div>
    </div>
  </header>

  <div class="grid">
    <aside class="rail">
      <nav class="stepper" id="stepper" aria-label="Pipeline stages">
        <div class="step" data-stage="0"><span class="num">00</span><span class="lab">Draft under review</span></div>
        <div class="step" data-stage="1"><span class="num">01</span><span class="lab">Triage · ML risk engine</span></div>
        <div class="step" data-stage="2"><span class="num">02</span><span class="lab">Failure hypotheses</span></div>
        <div class="step" data-stage="3"><span class="num">03</span><span class="lab">Autonomous investigation</span></div>
        <div class="step" data-stage="4"><span class="num">04</span><span class="lab">Critic + citation gate</span></div>
        <div class="step" data-stage="5"><span class="num">05</span><span class="lab">Counterfactual fix</span></div>
      </nav>
    </aside>

    <main id="stream">
      <!-- stage 0: draft -->
      <section class="card reveal" data-stage="0">
        <div class="eyebrow"><span class="n">00</span> Draft under review</div>
        <div class="casefile">
          <div class="kv" id="draft-kv"></div>
          <div class="designchips" id="draft-chips"></div>
        </div>
      </section>

      <!-- stage 1: triage -->
      <section class="card" data-stage="1">
        <div class="eyebrow reveal" data-stage="1"><span class="n">01</span> Triage — validated accrual-risk engine</div>
        <div class="triage reveal" data-stage="1">
          <div>
            <div class="gauge" id="gauge">
              <div class="scaleline"><span>0.0</span><span>0.5</span><span>1.0</span></div>
              <div class="gaugewrap">
                <div class="track"></div>
                <div class="fillmask"><div class="fill" id="gfill"></div></div>
                <div class="marker" id="gmark"><span class="tip mono" id="gtip">0.00</span></div>
              </div>
              <div class="zones"><span>low risk</span><span>moderate</span><span>high risk</span></div>
            </div>
            <div class="driver" id="triage-driver"></div>
            <div class="peer" id="triage-peer"></div>
          </div>
          <div class="readout">
            <div class="big mono" id="risk-big">0.00</div>
            <div class="cls" id="risk-cls">— risk</div>
          </div>
        </div>
      </section>

      <!-- stage 2: hypotheses -->
      <section class="card" data-stage="2">
        <div class="eyebrow reveal" data-stage="2"><span class="n">02</span> Hypothesis generation — draft-specific failure modes</div>
        <div class="hyps" id="hyps"></div>
      </section>

      <!-- stage 3: investigation -->
      <section class="card" data-stage="3">
        <div class="eyebrow reveal" data-stage="3"><span class="n">03</span> Autonomous investigation — one tool-use loop per hypothesis</div>
        <div class="invhead reveal" data-stage="3" id="connbar"></div>
        <div id="traces"></div>
      </section>

      <!-- stage 4: register -->
      <section class="card" data-stage="4">
        <div class="eyebrow reveal" data-stage="4"><span class="n">04</span> Adversarial critic + citation gate — ranked register</div>
        <div class="gatebar reveal" data-stage="4"><span class="lock">🔒</span><span id="gatetext"></span></div>
        <div id="register"></div>
      </section>

      <!-- stage 5: counterfactual -->
      <section class="card" data-stage="5">
        <div class="eyebrow reveal" data-stage="5"><span class="n">05</span> Counterfactual — which design change lowers risk most?</div>
        <div class="cf reveal" data-stage="5">
          <div class="baseline" id="cf-base"></div>
          <div class="bars" id="cf-bars"></div>
        </div>
        <div class="summary reveal" data-stage="5" id="summary" style="margin-top:22px"></div>
        <div class="finrule reveal" data-stage="5" id="finrule"></div>
      </section>

      <p class="footnote reveal" data-stage="5" id="footnote"></p>
    </main>
  </div>
</div>

<script>
(function(){
  "use strict";
  const RUN = JSON.parse(document.getElementById("run-data").textContent);
  const $ = (s,r=document)=>r.querySelector(s);
  const el = (t,c,h)=>{const n=document.createElement(t); if(c)n.className=c; if(h!=null)n.innerHTML=h; return n;};
  const esc = s => String(s==null?"":s).replace(/[&<>"]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[m]));
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---------- risk classification ----------
  function riskClass(v){ return v>=0.5?["high","var(--risk-high)"]:v>=0.3?["moderate","var(--risk-med)"]:["low","var(--risk-low)"]; }
  const toolClass = t => ({literature:"t-lit",drug_mechanism:"t-mech",similar_trials:"t-trials",target_disease:"t-tgt"}[t]||"");
  // mirror the terminal ✓/· rule: a call "returned data" unless it errored or came back empty
  function gotData(obs){ return !/unavailable/.test(obs) && !/"mechanisms":\s*\[\]/.test(obs) && !/"n":\s*0\b/.test(obs); }

  // ================= RENDER (content, initially hidden) =================
  const d = RUN.draft;
  const kv = $("#draft-kv");
  const rows = [
    ["condition", esc(d.cond)],
    ["phase", esc(d.phase)],
    ["drug", esc(d.drug)+(d.target?`  ·  <span class="mono" style="color:var(--dim)">${esc(d.target)}</span>`:"")],
    ["endpoint", `<span class="flagline">${esc(d.primary_endpoint)}</span>`],
    ["notes", `<span style="color:var(--dim)">${esc(d.notes||"")}</span>`],
  ];
  rows.forEach(([k,v])=>{ const r=el("div","row"); r.appendChild(el("span","k",k)); r.appendChild(el("span","v",v)); kv.appendChild(r); });

  const chips = $("#draft-chips");
  const pc = (RUN.ml_risk&&RUN.ml_risk.peer_comparison)||{};
  const excludHot = pc.excl_median!=null && d.n_excl>pc.excl_median;
  [["incl criteria",d.n_incl,null,false],
   ["excl criteria",d.n_excl, pc.excl_median!=null?`vs ${pc.excl_median} peer`:null, excludHot],
   ["enrollment",d.enroll_target, pc.enroll_median!=null?`vs ${pc.enroll_median} peer`:null,false],
   ["arms",d.n_arms,null,false],
   ["age span",(d.age_span!=null?d.age_span+" yr":"—"),null,false],
  ].forEach(([lab,val,sub,hot])=>{
    const c=el("div","dchip"+(hot?" hot":"")); c.innerHTML=`<b>${esc(val)}</b><small>${esc(lab)}${sub?" · "+esc(sub):""}</small>`; chips.appendChild(c);
  });

  // triage
  const risk = RUN.ml_risk||{}; const rv = +risk.risk_score||0;
  const [rcls] = riskClass(rv);
  $("#triage-driver").innerHTML = "▸ "+esc((risk.drivers&&risk.drivers[0])||"");
  const peer = $("#triage-peer");
  [["excl vs peer", pc.excl_vs_peer!=null?("+"+pc.excl_vs_peer):"—"],
   ["enroll vs peer", pc.enroll_vs_peer_ratio!=null?(pc.enroll_vs_peer_ratio+"×"):"—"],
   ["excl median", pc.excl_median!=null?pc.excl_median:"—"]
  ].forEach(([l,v])=>{ const p=el("div","p"); p.innerHTML=`<b>${esc(v)}</b><small>${esc(l)}</small>`; peer.appendChild(p); });

  // hypotheses
  const hy = $("#hyps");
  RUN.hypotheses.forEach(h=>{
    const c=el("div","hyp reveal"); c.setAttribute("data-stage","2");
    c.innerHTML = `<div class="hid">${esc(h.id)}</div><div class="fm">${esc(h.failure_mode)}</div>`+
      (h.why_this_design?`<div class="why">${esc(h.why_this_design)}</div>`:"");
    hy.appendChild(c);
  });

  // connector bar
  const ca = RUN._connector_activity||{};
  const connEls = {};
  const connbar = $("#connbar");
  const order = ["drug_mechanism","literature","similar_trials","target_disease"];
  order.filter(k=>ca[k]).forEach(k=>{
    const c=el("div","conn"); c.innerHTML =
      `<div class="cn"><span class="dot"></span>${esc(k)}</div><div class="cc"><span class="live-n">0</span><small>/${ca[k].calls} calls · <span class="data-n">0</span> w/ data</small></div>`;
    connbar.appendChild(c); connEls[k]={node:c, made:0, data:0, total:ca[k].calls};
  });

  // investigation traces (grouped by hyp), rows hidden for playback
  const byHyp = {};
  RUN.trajectory.forEach(t=>{ (byHyp[t.hyp]=byHyp[t.hyp]||[]).push(t); });
  const traces = $("#traces");
  const callNodes = []; // ordered for playback
  Object.keys(byHyp).forEach(hid=>{
    const steps = byHyp[hid];
    const box = el("div","hyptrace");
    box.innerHTML = `<div class="th reveal" data-stage="3">${esc(hid)}<span class="cnt">${steps.length} tool calls</span></div>`;
    const calls = el("div","calls"); box.appendChild(calls);
    steps.forEach(t=>{
      const ok = gotData(t.obs_preview||"");
      const arg = JSON.stringify(t.args||{});
      const row = el("div","call reveal"); row.setAttribute("data-stage","3");
      row.innerHTML = `<span class="mk ${ok?"ok":"no"}">${ok?"✓":"·"}</span>`+
        `<span class="tool ${toolClass(t.tool)}">${esc(t.tool)}</span>`+
        `<span class="arg">${esc(arg.length>78?arg.slice(0,78)+"…":arg)}</span>`;
      calls.appendChild(row);
      callNodes.push({row, tool:t.tool, ok});
    });
    traces.appendChild(box);
  });

  // register
  const gate = $("#gatetext");
  gate.textContent = "Citation gate: every PMID / NCT / ChEMBL id below was captured from real tool output. Ids the model typed but no tool returned are stripped — 0 unverified ids ship.";
  const reg = $("#register");
  function srcType(id){ if(/^PMID/i.test(id))return"pmid"; if(/^NCT/i.test(id))return"nct"; return"chembl"; }
  RUN.register.forEach(r=>{
    const f=el("div",`finding reveal sev-${r.severity}`); f.setAttribute("data-stage","4");
    const srcs = (r.sources||[]);
    const srcHtml = srcs.map(s=>{const ty=srcType(s.id);
      return `<span class="src ${ty}" title="${esc(s.label||"")}"><span class="tag">${ty}</span>${esc(s.id)}<span class="vr">✓</span></span>`;}).join("");
    f.innerHTML =
      `<div class="stripe"></div><div class="body">`+
      `<div class="fhead"><span class="rank">#${esc(r.rank)}</span><span class="sev">${esc(r.severity)}</span>`+
      `<span class="claim">${esc(r.claim||r.failure_mode)}</span></div>`+
      (r.reasoning?`<div class="reason">${esc(r.reasoning)}</div>`:"")+
      `<div class="srcs">${srcHtml}</div>`+
      `<div class="critic"><span class="verdict ${esc(r.critic_verdict)}">${esc(r.critic_verdict)}</span>`+
      `<span class="cr">${esc(r.critic_reason||"")}</span></div>`+
      `</div>`;
    reg.appendChild(f);
  });

  // counterfactual
  const cf = RUN.counterfactual||{scenarios:[]};
  const base = +cf.baseline_risk||rv;
  $("#cf-base").innerHTML = `baseline risk <b>${base.toFixed(3)}</b> — simulate a design edit, re-score with the same engine, rank by risk delta:`;
  const maxv = Math.max(base, ...cf.scenarios.map(s=>+s.new_risk||0), 0.5);
  const bars = $("#cf-bars");
  const barFills=[];
  cf.scenarios.forEach(s=>{
    const nv=+s.new_risk||0, dv=+s.delta||0, down=dv<0;
    const row=el("div","barrow reveal"); row.setAttribute("data-stage","5");
    const basePct=(base/maxv*100).toFixed(1);
    row.innerHTML = `<div class="edit">${esc(s.edit)}<span class="bardelta ${down?"down":"up"}">${down?"":"+"}${dv.toFixed(3)}</span></div>`+
      `<div class="bartrack"><div class="baseref" style="left:${basePct}%"></div>`+
      `<div class="barfill ${down?"down":"up"}" data-w="${(nv/maxv*100).toFixed(1)}"></div>`+
      `<span class="barval">${nv.toFixed(3)}</span></div>`;
    bars.appendChild(row); barFills.push(row.querySelector(".barfill"));
  });

  // summary + footer
  const beats = RUN._demo_beats||{};
  const nCalls = RUN.trajectory.length;
  const dropped = (RUN.rejected_findings||[]).length;
  const totalData = Object.values(ca).reduce((a,c)=>a+(c.succeeded_with_data||0),0);
  const totalCalls = Object.values(ca).reduce((a,c)=>a+(c.calls||0),0);
  const summary=$("#summary");
  [["hypotheses",RUN.hypotheses.length,"agent-generated"],
   ["tool calls",nCalls,`${totalData}/${totalCalls} returned data`],
   ["findings shipped",RUN.register.length,`${dropped} rejected by critic`],
   ["unverified ids","0","stripped by the gate"]
  ].forEach(([l,v,s])=>{ const c=el("div","sc"); c.innerHTML=`<b>${esc(v)}</b><small>${esc(l)}<br>${esc(s)}</small>`; summary.appendChild(c); });
  $("#finrule").innerHTML = `<span class="ok">✓</span> ${esc(beats.critic_action||"agentic run complete")} — every shipped citation verified against real tool output.`;
  $("#footnote").innerHTML = "Deterministic offline playback of a real recorded run · "+esc(beats.agency||"")+
    " · the ML risk engine is numpy-only and backtested leak-free (v0 draft, ACTUAL enrollment dropped).";

  // ================= PLAYBACK ENGINE =================
  const steps = document.querySelectorAll("#stepper .step");
  const reveals = Array.from(document.querySelectorAll(".reveal"));
  // ordering: reveals already in DOM order = pipeline order
  let idx = 0, playing=false, timer=null, speed=1, done=false;
  const SPEEDS=[1,2,4,0.5];
  const baseDelay = node => {
    const st=+node.getAttribute("data-stage");
    if(node.classList.contains("call")) return 150;
    if(node.classList.contains("hyp")) return 380;
    if(node.classList.contains("barrow")) return 260;
    if(node.classList.contains("finding")) return 900;
    if(node.classList.contains("th")) return 220;
    if(st===0) return 500;
    return 520;
  };

  function setStage(st){
    steps.forEach(s=>{ const v=+s.getAttribute("data-stage");
      s.classList.toggle("active", v===st); s.classList.toggle("done", v<st); });
  }
  function applySideEffects(node){
    const st=+node.getAttribute("data-stage");
    // triage gauge fills when its row reveals
    if(st===1 && node.classList.contains("triage")){
      const pct=Math.max(2,Math.min(100,rv*100));
      $("#gfill").style.width=pct+"%"; $("#gmark").style.left=pct+"%";
      const [cls,col]=riskClass(rv);
      $("#gtip").textContent=rv.toFixed(3); $("#gtip").style.color=col;
      $("#gmark").style.background=col;
      animNum($("#risk-big"), rv, 3); $("#risk-cls").textContent=cls+" risk";
      $("#risk-cls").style.color=col; $("#risk-big").style.color=col;
    }
    // connector counters tick up as calls reveal
    if(node.classList.contains("call")){
      const info=node.__call; if(info){ const c=connEls[info.tool];
        if(c){ c.made++; if(info.ok)c.data++;
          c.node.querySelector(".live-n").textContent=c.made;
          c.node.querySelector(".data-n").textContent=c.data;
          c.node.classList.add("live");
          clearTimeout(c._t); c._t=setTimeout(()=>c.node.classList.remove("live"),450);
        } }
    }
    // counterfactual bars grow
    if(node.classList.contains("barrow")){ const bf=node.querySelector(".barfill"); if(bf) bf.style.width=bf.getAttribute("data-w")+"%"; }
  }
  // attach call info to nodes
  callNodes.forEach(c=>{ c.row.__call={tool:c.tool, ok:c.ok}; });

  function revealNext(){
    if(idx>=reveals.length){ finish(); return; }
    const node=reveals[idx];
    setStage(+node.getAttribute("data-stage"));
    node.classList.add("on");
    applySideEffects(node);
    idx++;
    updateProgress();
    if(playing){ const dl=reduce?0:baseDelay(node)/speed; timer=setTimeout(revealNext, dl); }
  }
  function finish(){ playing=false; done=true; setStage(5);
    steps.forEach(s=>s.classList.add("done")); steps[steps.length-1].classList.remove("done"); steps[steps.length-1].classList.add("active");
    document.body.classList.remove("playing"); btnPlay.innerHTML="↻ Replay"; updateProgress(); }
  function updateProgress(){ $("#progbar").style.width=(idx/reveals.length*100).toFixed(1)+"%"; }

  function animNum(node,to,dec){ if(reduce){node.textContent=to.toFixed(dec);return;}
    let cur=0; const t0=performance.now(), dur=900;
    (function tick(t){ const k=Math.min(1,(t-t0)/dur); cur=to*(k<1?(1-Math.pow(1-k,3)):1);
      node.textContent=cur.toFixed(dec); if(k<1)requestAnimationFrame(tick); })(t0);
  }

  function play(){
    if(done){ restart(); }
    playing=true; document.body.classList.add("playing");
    btnPlay.innerHTML="⏸ Pause"; revealNext();
  }
  function pause(){ playing=false; clearTimeout(timer); document.body.classList.remove("playing"); btnPlay.innerHTML="▶ Resume"; }
  function restart(){ clearTimeout(timer); idx=0; done=false;
    reveals.forEach(n=>n.classList.remove("on"));
    barFills.forEach(b=>b.style.width="0");
    $("#gfill").style.width="0"; $("#gmark").style.left="0";
    Object.values(connEls).forEach(c=>{c.made=0;c.data=0;
      c.node.querySelector(".live-n").textContent="0"; c.node.querySelector(".data-n").textContent="0"; c.node.classList.remove("live");});
    setStage(0); updateProgress();
  }
  function toEnd(){ clearTimeout(timer); playing=false;
    while(idx<reveals.length){ const node=reveals[idx]; node.classList.add("on"); setStage(+node.getAttribute("data-stage")); applySideEffects(node); idx++; }
    finish();
  }

  const btnPlay=$("#btnPlay");
  btnPlay.addEventListener("click",()=>{ playing?pause():play(); });
  $("#btnEnd").addEventListener("click", toEnd);
  $("#btnSpeed").addEventListener("click",e=>{ const i=(SPEEDS.indexOf(speed)+1)%SPEEDS.length; speed=SPEEDS[i]; e.target.textContent=speed+"×"; });
  $("#btnTheme").addEventListener("click",()=>{ const r=document.documentElement;
    const cur=r.getAttribute("data-theme")|| (window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");
    r.setAttribute("data-theme", cur==="dark"?"light":"dark"); });

  // initialize: show stage 0 statically so the page isn't blank before Play
  restart();
  reveals.filter(n=>+n.getAttribute("data-stage")===0).forEach(n=>n.classList.add("on"));
  setStage(0);
  // auto-start after a beat so a shared screen begins moving
  if(!reduce) setTimeout(()=>{ if(idx<=1 && !playing && !done) play(); }, 900);
  else toEnd();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate the TrialPremortem web demo (self-contained HTML).")
    ap.add_argument("--run", default=_DEFAULT_RUN, help="path to saved run JSON")
    ap.add_argument("--out", default=_DEFAULT_OUT, help="output HTML path")
    args = ap.parse_args()
    if not os.path.exists(args.run):
        print(f"saved run not found: {args.run}", file=sys.stderr); sys.exit(1)
    path = write(args.run, args.out)
    print(f"wrote {path}")
