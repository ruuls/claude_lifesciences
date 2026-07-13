"""L5b PRESENT — agentic red-team over a draft protocol.

The shipped product (agent-as-tool hybrid): a controller agent that
  1. parses the draft into structured features,
  2. calls the ML RiskEngine as a TOOL (the C1 engine — ML-grade accuracy),
  3. retrieves real precedent trials (with their outcomes) via BM25,
  4. runs five reviewer personas, each grounded in the risk score + cited precedent,
  5. a moderator synthesizes a ranked failure-mode register.

Personas narrate a validated signal; they are not the claim.
"""
from __future__ import annotations
import json

PERSONAS = {
    "biostatistician": "a trial biostatistician who scrutinizes power, enrollment feasibility, endpoint timing, and estimand coherence",
    "regulatory": "an FDA/regulatory reviewer who scrutinizes endpoint justification, safety monitoring adequacy, and ICH compliance",
    "site_coordinator": "a clinical site coordinator who scrutinizes visit burden, screening logistics, and operational feasibility",
    "patient_advocate": "a patient advocate focused on eligibility restrictiveness, equity, and representativeness of the enrolled population",
    "safety_physician": "a safety physician who scrutinizes adverse-event monitoring, stopping rules, and risk to participants",
}


def build_persona_prompt(role_desc, draft_summary, risk_result, precedent):
    prec = "\n".join(precedent) if precedent else "(no close precedent found)"
    drivers = "; ".join(risk_result.get("top_drivers", [])) or "none flagged by the model"
    return (
        f"You are {role_desc}, reviewing a DRAFT clinical trial protocol before it is finalized. "
        f"Your job is a pre-mortem: assume it has already failed and identify the most likely design reason, "
        f"from YOUR perspective only.\n\n"
        f"DRAFT DESIGN:\n{draft_summary}\n\n"
        f"QUANTITATIVE RISK ENGINE OUTPUT (validated ML model, AUC 0.67 on held-out trials):\n"
        f"- Accrual-failure risk score: {risk_result.get('risk_score')}\n"
        f"- Model-flagged drivers: {drivers}\n\n"
        f"SIMILAR HISTORICAL TRIALS AND HOW THEY ENDED:\n{prec}\n\n"
        f"Return the single most important issue you see, grounded in the risk score and the precedent above. "
        f"Cite specific precedent where possible. If you see no serious issue from your angle, say so. "
        f"Be concrete and brief (2-3 sentences)."
    )


def emit_finding_tool():
    return {"name": "emit_finding", "description": "Emit one red-team finding.",
            "input_schema": {"type": "object", "properties": {
                "issue": {"type": "string"},
                "severity": {"type": "string", "enum": ["high", "medium", "low", "none"]},
                "evidence": {"type": "string"},
                "recommendation": {"type": "string"},
            }, "required": ["issue", "severity", "evidence", "recommendation"]}}


def moderator_prompt(findings, risk_result):
    fj = json.dumps(findings, indent=1)
    return (
        "You are the moderator of a clinical-trial protocol red team. Below are findings from five "
        "reviewer personas, each grounded in a validated risk model and real precedent. Synthesize them "
        "into a RANKED failure-mode register: order by severity and evidence strength, merge duplicates, "
        "and for each give: the failure mode, why it matters, severity, and the concrete design change to consider. "
        f"The overall model accrual-failure risk score is {risk_result.get('risk_score')}.\n\n"
        f"PERSONA FINDINGS:\n{fj}\n\n"
        "Return a concise ranked register (markdown), highest-severity first."
    )
