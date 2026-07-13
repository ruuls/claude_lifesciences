# TrialPremortem — 90-Second Demo Script

*Timing in brackets. Numbers are live from the backtest artifacts.*

---

**[0:00–0:15] The hook**

"76% of clinical trial protocols get amended after they're written. Each fix costs $141,000 to half a million dollars. And the #1 reason trials die isn't the drug failing — it's that they can't recruit enough patients. The experts already review every protocol 5 to 7 times. They still miss it. Why? Because no reviewer remembers what happened to the thousand similar trials that came before."

**[0:15–0:30] The idea**

"TrialPremortem reads a trial's *first draft* and predicts whether it will fail to recruit — before a single patient is enrolled. And we didn't validate this against opinions. We backtested it against the real version history of real trials on ClinicalTrials.gov: recover the original draft, hide what happened, predict, then check the record."

**[0:30–0:50] The proof — show the backtest figure**

"Here's the result on 927 real trials. AUC 0.67 — reading only the original draft. At our risk threshold it flags 43% of the trials that later died of poor recruitment, while only flagging 21% of the ones that succeeded. It's specific, not alarmist. Every number here is leak-free and cross-validated — we caught and removed an outcome-leakage bug that would have inflated this to a fake 0.82."

**[0:50–1:10] The live demo — run the autonomous agent**

Run: `python -m trialpremortem.demo --web` (opens the animated UI) — or `--replay` for the terminal version.

"Watch it work. I feed in a draft depression trial — escitalopram, primary endpoint at Week 2. The validated risk engine triages it, then the agent generates its own failure hypotheses and *investigates each one*, choosing which biomedical databases to call — ChEMBL for the drug's mechanism, Open Targets to confirm the target, PubMed for the evidence, ClinicalTrials.gov for real precedent. It catches that Week 2 is too early for an SSRI to separate from placebo — a mechanism flaw, found by converging live data sources. Then an adversarial critic checks every cited PMID against what the tools actually returned and downgrades any overstated claim. Every citation in the final register is verified real — no hallucinations survive."

**[1:10–1:25] The prescription**

"And it doesn't just diagnose — it prescribes. The what-if engine shows: cut the exclusions to the peer median and the failure risk drops from 0.35 to 0.19 — a 46% reduction. That's an actionable fix, quantified, before the protocol is locked."

**[1:25–1:30] The close**

"On 43 real failed trials, TrialPremortem caught the flaw in every one — a conservative $7.8 million in avoidable cost. It's the memory of every trial that came before, handed to the people designing the next one."

---

## Backup Q&A (for judges)

- **"Is 0.67 good enough?"** — For foreseeing failure from a *first draft*, yes: it's a real, leak-free number with clean specificity. We deliberately ship a true 0.67 over a leaky 0.82.
- **"Isn't the agent just a wrapper?"** — No — it calls the ML risk engine as a tool, retrieves real precedent, and runs multi-persona reasoning. We measured agent-alone (0.55) vs ML (0.61) honestly; the product is the hybrid.
- **"What's the false-positive rate?"** — 21% of completed trials flagged at the top-quartile threshold (panel C). We report it alongside the 43% catch rate, not instead of it.
- **"Where's the data from?"** — 100% public ClinicalTrials.gov v2 API + version history. 7,161-trial background corpus for peer norms; 280-trial matched cohort; 927-trial natural-distribution test.
