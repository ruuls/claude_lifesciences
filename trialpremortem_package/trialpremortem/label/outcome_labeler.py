"""L2 LABEL — classify a terminated trial's whyStopped text into a failure mode.

Positive class (y=1) = accrual-driven termination: the failure our predictor targets.
Rule-based first pass (fast, transparent); an LLM tie-breaker is available for
ambiguous/empty text via label_llm(). Order matters: accrual first (an accrual
failure is still an accrual failure even if funding is mentioned); business before
funding (a strategic sponsor decision is business, not money running out).
"""
from __future__ import annotations
import re

_RULES = [
    ("accrual", re.compile(
        r"\b(accru|enrol|recruit|slow|insufficient|inadequate|"
        r"low\s+(patient|subject|participant|enrol)|"
        r"lack of (patient|subject|eligible|participant|enrol)|poor accrual|"
        r"unable to (enroll|recruit)|did not (enroll|accrue)|"
        r"failure to (recruit|enroll|accrue)|"
        r"difficult(y|ies)? (recruiting|enrolling)|no (patients|subjects) enrolled)", re.I)),
    ("safety", re.compile(
        r"\b(safety|toxicit|adverse event|serious adverse|SAE|"
        r"tolerab|side effect|risk[- ]benefit|DSMB|"
        r"data (and )?safety monitoring)", re.I)),
    ("efficacy", re.compile(
        r"\b(efficacy|futility|futile|lack of (efficacy|benefit|response)|"
        r"did not (meet|show)|no (significant )?(benefit|effect|improvement)|"
        r"interim analysis|primary endpoint (not|was not) met|"
        r"unlikely to (meet|achieve)|fail(ed|ure)? to meet)", re.I)),
    ("business", re.compile(
        r"\b(business|strategic|company (decision|priorit)|portfolio|"
        r"commercial|drug supply|manufactur|product (discontinu|withdraw)|"
        r"reprioriti|merger|acqui|sponsor.{0,15}(decision|priorit))", re.I)),
    ("funding", re.compile(
        r"\b(fund|financ|budget|grant|resource|money|monetary|"
        r"lack of (support|resources))", re.I)),
]


def classify(why: str) -> tuple[str, float]:
    """Return (failure_mode, confidence). Empty text -> ('unknown', 0.0)."""
    t = (why or "").strip()
    if not t:
        return ("unknown", 0.0)
    for mode, pat in _RULES:
        if pat.search(t):
            return (mode, 0.9)
    return ("other", 0.5)


def is_accrual_failure(why: str) -> int:
    return int(classify(why)[0] == "accrual")


def label_llm(why: str, host) -> tuple[str, float]:
    """LLM tie-breaker for ambiguous cases. host = the kernel host object."""
    prompt = (
        "Classify why this clinical trial was terminated into exactly one category: "
        "accrual (recruitment/enrollment problems), safety, efficacy (futility/no benefit), "
        "funding (money ran out), business (strategic/company/supply decision), or other. "
        f'Reason given: "{why}". '
        "Answer with only the single category word."
    )
    r = host.llm(prompt)
    ans = r["text"].strip().lower().split()[0] if r.get("text") else "other"
    valid = {"accrual", "safety", "efficacy", "funding", "business", "other"}
    return (ans if ans in valid else "other", 0.7)
