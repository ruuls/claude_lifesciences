"""Data contracts for TrialPremortem. Three dataclasses = the three layer boundaries."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class LabeledTrial:
    """Output of L1 (ingest) + L2 (label): one trial with v0 draft + outcome."""
    nct: str
    v0: dict                      # protocolSection at studyVersion==0, outcome-blind
    trajectory: list[dict]        # [{version,date,status,moduleLabels}]
    outcome: str                  # TERMINATED | COMPLETED
    why_stopped: str = ""         # raw free text (empty for completed)
    failure_mode: str = ""        # accrual|safety|efficacy|funding|business|other|""
    y: int = 0                    # 1 = accrual-driven termination (positive class)
    phase: str = ""
    condition: str = ""
    start_year: int = 0
    enrollment: int = 0

    def to_dict(self) -> dict: return asdict(self)


@dataclass
class ProtocolFeatures:
    """Output of L3 (extract): ~25 comparable features from a v0 protocol."""
    nct: str
    # eligibility restrictiveness (load-bearing group)
    n_inclusion: int = 0
    n_exclusion: int = 0
    age_min: float = 0.0
    age_max: float = 120.0
    age_span: float = 120.0
    excl_prior_therapy: bool = False
    excl_comorbidity: bool = False
    excl_count_normalized: float = 0.0
    biomarker_gated: bool = False
    restrictiveness_index: float = 0.0     # composite 0-1, computed in code
    # design burden
    n_arms: int = 1
    n_primary_endpoints: int = 1
    endpoint_horizon_weeks: float = 0.0
    visit_burden: float = 0.0
    enrollment_target: int = 0
    # context (for matching, not prediction)
    phase: str = ""
    condition: str = ""
    start_year: int = 0

    def to_dict(self) -> dict: return asdict(self)


@dataclass
class Neighbor:
    nct: str
    distance: float
    y: int
    outcome: str
    why_stopped: str = ""


@dataclass
class RiskAssessment:
    """Output of L4 (predict): calibrated risk + evidence trail."""
    nct: str
    risk_score: float                       # calibrated P(accrual failure)
    config: str = "C1"                      # C0 | C1 | C2
    neighbors: list[Neighbor] = field(default_factory=list)
    top_drivers: list[str] = field(default_factory=list)
    matched_amendments: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d
