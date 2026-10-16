from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Action(str, Enum):
    APPROVE = "approve"
    SELECT = "select"
    CUSTOMIZE = "customize"
    REJECT = "reject"
    DEFER = "defer"


class PageContext(StrictModel):
    url: str
    title: str | None = None
    context: str


class Violation(StrictModel):
    id: str
    criterion: str
    element: str
    description: str
    severity: str
    current_value: str | float | None = None
    required_value: str | float | None = None


class VisualSettings(StrictModel):
    text_scale: float = Field(ge=1.0, le=2.0)
    line_height: float = Field(ge=1.2, le=2.0)
    letter_spacing_em: float = Field(ge=0.0, le=0.12)
    target_contrast_ratio: float = Field(ge=4.5, le=21.0)
    target_size_px: int = Field(ge=24, le=48)
    high_contrast: bool


class CapabilityBounds(StrictModel):
    text_scale_min: float = 1.0
    text_scale_max: float = 2.0
    line_height_min: float = 1.2
    line_height_max: float = 2.0
    letter_spacing_em_min: float = 0.0
    letter_spacing_em_max: float = 0.12
    contrast_ratio_min: float = 4.5
    contrast_ratio_max: float = 21.0
    target_size_px_min: int = 24
    target_size_px_max: int = 48


class CandidatePlan(StrictModel):
    id: str
    name: str
    description: str
    changes: list[str] = Field(default_factory=list)
    resulting_settings: VisualSettings
    predicted_benefit: float = Field(ge=0.0, le=1.0)
    regression_risk: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    visual_change_cost: float = Field(ge=0.0, le=1.0)
    reversible: bool


class DecisionPackage(StrictModel):
    scenario_id: str
    stage: int = Field(ge=0, le=3)
    page: PageContext
    violations: list[Violation] = Field(min_length=1)
    recommended_plan_id: str
    candidate_plans: list[CandidatePlan] = Field(min_length=1)
    capability_bounds: CapabilityBounds = Field(default_factory=CapabilityBounds)
    history: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def plan_references_must_be_valid(self) -> "DecisionPackage":
        ids = [plan.id for plan in self.candidate_plans]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate plan IDs must be unique")
        if self.recommended_plan_id not in ids:
            raise ValueError("recommended_plan_id must identify a candidate plan")
        return self


class VisualPreferences(StrictModel):
    preferred_text_scale: float = Field(ge=1.0, le=2.0)
    preferred_line_height: float = Field(ge=1.2, le=2.0)
    preferred_letter_spacing_em: float = Field(ge=0.0, le=0.12)
    target_contrast_ratio: float = Field(ge=4.5, le=21.0)
    preferred_target_size_px: int = Field(ge=24, le=48)
    prefers_high_contrast: bool


class VisualProfile(StrictModel):
    id: str
    name: str
    acuity_category: str
    acuity_range: str
    description: str
    expected_barriers: list[str]
    preferences: VisualPreferences
    parameterization_note: str


class SimulationRequest(StrictModel):
    profile_id: str
    decision_package: DecisionPackage
    model: str | None = None


class HumanDecision(StrictModel):
    action: Action
    selected_plan_id: str | None = None
    customized_settings: VisualSettings | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    perceived_accessibility_fit: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    reason_codes: list[str] = Field(default_factory=list)
    rationale: str


class SimulationMetadata(StrictModel):
    run_id: str
    profile_id: str
    profile_name: str
    stage: int
    model: str
    prompt_version: str
    llm_inference_time_ms: int
    used_llm: bool
    decision_validated: bool


class SimulationResponse(StrictModel):
    decision: HumanDecision
    metadata: SimulationMetadata


class OllamaHealth(StrictModel):
    status: str
    base_url: str
    configured_model: str
    available_models: list[str]
