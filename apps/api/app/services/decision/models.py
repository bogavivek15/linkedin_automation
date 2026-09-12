from uuid import UUID
from pydantic import BaseModel, Field

class ApplicationContext(BaseModel):
    application_url: str | None = None
    execution_mode: str = "USER_HANDOFF"
    sensitive_signals: list[str] = Field(default_factory=list)

class CandidateAutomationPolicy(BaseModel):
    preferred_work_modes: list[str] | None = None
    employment_types: list[str] | None = None
    minimum_salary: float | None = None
    excluded_locations: list[str] | None = None
    auto_apply_enabled: bool = False
    require_user_approval: bool = True

class Decision(BaseModel):
    id: UUID
    overall_score: float
    match_score: float
    trust_score: float
    risk_level: str
    hard_constraints_passed: bool
    application_mode: str
    action: str
    blocking_conditions: list[str]
    policy_version: str

class DecisionResult(BaseModel):
    final_score: float
    outcome: str
    reasons: list[str]
    policy_version: str
