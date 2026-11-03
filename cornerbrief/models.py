"""Shared result types. Agent output schemas forbid extra fields, so an agent cannot add a limit."""
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

RuleResult = Literal["limit exceeded", "no conflict found", "unknown", "not applicable"]
Label = Literal["measured", "assumed", "missing", "stale"]
Status = Literal["probably standard", "probably custom", "unknown"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceItem(BaseModel):
    key: str
    ramp_id: Optional[str] = None
    field: str
    value: Any = None
    unit: Optional[str] = None
    unit_documented: bool = False
    label: Label
    source: str
    date: Optional[str] = None
    reason: str = ""


class RuleOutcome(BaseModel):
    rule_id: str
    title: str
    ramp_id: Optional[str] = None
    parameter: Optional[str] = None
    value: Any = None
    value_unit: Optional[str] = None
    limit_text: str = ""
    result: RuleResult
    preview: Optional[RuleResult] = None
    math: str = ""
    reason: str = ""
    authority_type: str = ""
    section: Optional[str] = None
    url: Optional[str] = None
    quote: Optional[str] = None


class Decision(BaseModel):
    rule_id: str
    title: str
    jurisdiction: str
    applies: bool
    forced_unknown: bool = False
    reason: str
    precedence_id: str
    source_section: str = ""
    url: str = ""
    status: str = ""


class Conflict(BaseModel):
    parameter: str
    rules: list[dict]
    stricter_min: Optional[float] = None
    stricter_max: Optional[float] = None
    unit: str = "percent"
    warning: str
    decision: str = "Engineer decides"


# Agent outputs
class RecordLabel(Strict):
    key: str
    label: Label
    note: str = ""


class RecordsOutput(Strict):
    summary: str
    labels: list[RecordLabel]


class Constraint(Strict):
    text: str
    evidence_keys: list[str] = Field(default_factory=list)


class RampOption(Strict):
    ramp_type: Literal["C1 perpendicular", "C2 directional", "C3 parallel", "C4 shared parallel", "C5 blended transition"]
    rationale: str
    evidence_keys: list[str] = Field(default_factory=list)


class SiteAnalystOutput(Strict):
    constraints: list[Constraint]
    options: list[RampOption]


class Challenge(Strict):
    claim: str
    issue: str
    severity: Literal["note", "rework"]


class SkepticOutput(Strict):
    verdict: Literal["pass", "rework"]
    challenges: list[Challenge] = Field(default_factory=list)


class BriefWriterOutput(Strict):
    summary: str
    findings_narrative: str
    engineer_note: str = ""
