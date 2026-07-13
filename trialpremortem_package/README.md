# TrialPremortem

**An AI agent that stress-tests a draft clinical trial protocol *before* it's finalized — and predicts, from the first draft alone, whether it will fail to recruit patients.**

Built for *Built with Claude: Life Sciences*.

---

## The headline (validated, leak-free)

> **On real ClinicalTrials.gov history, TrialPremortem reads a trial's *original v0 draft* — with the outcome hidden — and foresees accrual failure at AUC 0.67. At a top-quartile risk threshold it flags 43% of trials that later died of poor recruitment while flagging only 21% of trials that completed.**

This is not a forward-looking guess validated against opinions. It is **backtested against the actual version history of real trials**: we recover each protocol's first-registered draft, hide what happened, predict, then check the recorded outcome.

---

## Why this problem is worth solving

- **76% of protocols are amended** (up from 57% a decade ago), averaging **3.3 amendments each**.
- A single substantial amendment costs a median **$141K (Phase 2)** to **$535K (Phase 3)**.
- Only **~16% of amendments are regulator-requested** — the rest are self-inflicted design flaws.
- **Insufficient accrual is the #1 cause of trial termination (~39%)**, and **eligibility is the most-amended element (~53%)**.

The experts already run 5–7 review layers. They still miss these flaws — not from incompetence, but because **no reviewer has the base rates**: nobody remembers what happened to the thousand similar trials that came before. The feedback loop (design → outcome) takes 12–24 months and is broken.

**TrialPremortem doesn't replace the experts. It gives them the memory of every trial that came before, and what happened to it.**

---

## Run the demo (offline, zero setup)

Two ways to watch the same recorded run — pick the one that fits the room.

```bash
tar xzf trialpremortem_package.tar.gz && cd trialpremortem_package

# 1) Web UI — the screen-share demo: an animated "instrument readout" that plays
#    the run back stage by stage (risk gauge, live tool-call stream, verified
#    register, counterfactual bars). Builds a single self-contained HTML file.
python -m trialpremortem.demo --web              # writes data/trialpremortem_demo.html and opens it

# 2) Terminal — the same run as a paced, colorized CLI walkthrough (~13s).
python -m trialpremortem.demo --replay
```

Both read a genuine recorded run (`data/agentic_harness_demo.json`) — **no network, no API keys** — so the demo is deterministic on stage. The web page is one file with everything inlined (no external assets, no build step); double-click it or serve it anywhere. To run the agent for real against live connectors, from a Claude Science `repl` cell: `from trialpremortem.demo import live; live(host)`.

### Presenting the project (the story)

`story.html` is a standalone, scrollable explainer for walking an audience through **the intuition and the build** — the problem, the backtest-against-version-history bet, the five-layer architecture, how we kept the numbers honest (the enrollment leak, the citation gate), and the evidence. Open it directly in a browser; it links straight to the demo.

## The agentic architecture (the harness)

TrialPremortem is not five fixed prompts — it is an **autonomous tool-use agent** with a real reasoning loop:

```
PremortemAgent (ReAct controller)
  ├─ decides which tool to call, reads the result, iterates
  ├─ tools it orchestrates:
  │    • score_risk         → validated ML engine (GBM, AUC 0.67) — ONE tool
  │    • retrieve_precedent → BM25 over real trials w/ known outcomes (failed|completed)
  │    • base_rate          → empirical accrual-failure prior for similar trials
  │    • simulate_fix       → counterfactual design edits + risk deltas
  │    • conclude           → structured verdict
  └─ forms a failure hypothesis, then uses tools to CONFIRM OR REFUTE it

MultiAgentDebate (on the same toolbox)
  Proposer (argues it fails) → Critic (challenges each claim) → Judge (calibrated verdict + confidence)
```

The agent **decides its own investigation path**. On the demo obesity draft it ran 6 tool calls in a self-chosen order (base_rate → score_risk → retrieve precedent → retrieve precedent → simulate_fix → re-verify precedent), discovered the condition itself has a 67% accrual-failure base rate, and the debate layer's Judge *downgraded* the Proposer's "high risk" to a calibrated MODERATE (confidence 0.72) after the Critic exposed a "3× criteria ≠ 3× filtering" logical flaw. That is genuine multi-agent reasoning, grounded in tool results — no invented numbers.

**Run it live:**
```python
from trialpremortem.agent.run import premortem
result = premortem(draft, host, engine, cohort, with_debate=True, verbose=True)
```

## What it does

1. **Ingest** — recovers the original v0 draft from ClinicalTrials.gov version history (outcome-blind by construction).
2. **Score** — a validated ML risk engine rates accrual-failure risk, using each design's restrictiveness *relative to peer trials* (7,161-trial background corpus).
3. **Red-team** — an agentic layer: five reviewer personas (biostatistician, regulatory, site coordinator, patient advocate, safety physician), each grounded in the risk score and **real retrieved precedent trials with their outcomes**, produce findings; a moderator synthesizes a **ranked failure-mode register**.
4. **Prescribe** — a counterfactual what-if engine simulates design edits and reports the risk reduction of each, so the output is a fix, not just a diagnosis.

The shipped product is an **agent-as-tool hybrid**: the agent runs the review and calls the ML risk engine as a tool — so it is agentic in interface *and* ML-grade in accuracy.

---

## The evidence

### Two complementary backtests (both v0-only, both leak-free)

| Evaluation | What it isolates | Result |
|---|---|---|
| **Natural distribution** (N=927, 19% base rate) | Deployment reality | **AUC 0.669**, flags **43%** of failures vs **21%** of completed |
| **Matched cohort** (140 pairs, condition+phase) | Design-intrinsic signal, base rates removed | **C1 ML 0.61 > C2 agentic 0.55 > C0 base 0.50** |

### The agentic finding (honest)

We measured whether zero-shot frontier reasoning foresees trial failure from a draft. **Engineered features still win** (0.61 vs 0.55 on the hard matched test). That's why the product uses the agent *as an interface over* the ML engine, not instead of it. This is a real capability-eval result, not a marketing claim.

### Rigor

- Custom gradient-boosted trees, BM25/RRF retrieval, isotonic calibration — all numpy, no sklearn.
- Peer-relative features (restrictiveness *vs. what similar trials did*).
- Corrected rank-based AUC (caught and fixed a tie-handling bug inflating a feature to 0.81).
- Caught and removed **outcome leakage** (the API returns *achieved* enrollment for terminated trials — a consequence of failure). All reported numbers use v0 ESTIMATED enrollment only.
- Ensemble weights chosen by **nested cross-validation** (no eval-set tuning).

---

## Worked examples: real trials, real flaws, real money

We took **43 real trials that actually died of poor recruitment**, fed the tool only their v0 draft, and it flagged the design flaw in every one.

| Trial | Condition | v0 risk | What actually happened |
|---|---|---|---|
| NCT01638585 | Diabetic Foot (Ph3) | 0.67 | Target 211 → enrolled 34 |
| NCT00627471 | Type 2 Diabetes (Ph4) | 0.59 | Target 200 → enrolled 9 |
| NCT02353949 | Mild Cognitive Impairment (Ph3) | 0.42 | Target 160 → enrolled 11 |
| NCT04899349 | Breast Cancer (Ph2) | 0.37 | Target 132 → enrolled 2 |

Across all 43, these trials recruited an average of **26% of target** before dying.

**Cost avoided** (using the amendment/per-patient figures above):
- Conservative (1 amendment/trial): **$7.8M** (~$182K/trial)
- Realistic ceiling (sunk cost of patients run before collapse): **$36.0M** (~$837K/trial)

*Caveat: these 43 are true positives from known failures — they show the tool catches real flaws. The false-positive discipline is the separate 21%-of-completed figure. Present both together.*

---

## Demo: the counterfactual in action

On a deliberately over-restrictive NSCLC Phase 2 draft (22 exclusions vs peer median 9, target 40):

- **Baseline risk: 0.345** — driver: *"22 exclusion criteria vs 9 typical — 13 more gates for patients to clear."*
- Retrieved precedent includes a real NSCLC Ph2 trial **terminated for "projected enrollment rate not feasible."**
- **What-if:** cutting exclusions to the peer median drops risk to **0.185 (−46%)**; combined redesign → **0.148**.

---

## Repository layout

```
trialpremortem/
  ingest/ctgov_client.py     # v0-draft recovery from CT.gov history (0-indexed)
  label/outcome_labeler.py   # accrual-failure labeling (79% prec / 83% recall)
  extract/protocol_parser.py # eligibility -> structured features
  predict/
    bm25.py                  # pure-python Okapi BM25 + RRF
    gbm.py                   # gradient-boosted trees (numpy)
    risk_model.py            # shrinkage scorer + isotonic calibration
    predictor.py             # RiskEngine — the tool the agent calls
    whatif.py                # counterfactual design-edit simulator
  present/redteam.py         # 5-persona agentic red team + moderator
  eval/metrics.py            # ROC/PR/AUC (rank-based)/calibration, numpy
  run_demo.py                # end-to-end pre-mortem
```

Run with `PYTHONPATH=.`. All ML is numpy-only (no sklearn dependency).

---

## Honest limitations

- **AUC 0.67 is a real, solid result — not 0.9.** Foreseeing trial failure from a first draft is genuinely hard. We ship a true 0.67 over a leaky 0.82.
- Site-count and sponsor features are weak because v0 drafts often don't list sites yet.
- Labeling uses validated regex rules (79/83 on accrual); a small fraction of ambiguous stop-reasons are edge cases.
- Cost figures are literature-based ranges, not per-trial accounting.
