from __future__ import annotations

import re
import unicodedata

from app.models import Action, DecisionPackage, HumanDecision, VisualSettings


def _normalize_token(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]", "", normalized.lower())


def _normalize_plan_id(
    selected_plan_id: str | None,
    package: DecisionPackage,
) -> str | None:
    if not selected_plan_id:
        return None
    allowed = [plan.id for plan in package.candidate_plans]
    if selected_plan_id in allowed:
        return selected_plan_id

    aliases = {_normalize_token(plan_id): plan_id for plan_id in allowed}
    for index, plan_id in enumerate(allowed, start=1):
        aliases[f"plan{index}"] = plan_id
        aliases[f"plano{index}"] = plan_id
        aliases[str(index)] = plan_id
    return aliases.get(_normalize_token(selected_plan_id))


def _within_capabilities(
    settings: VisualSettings,
    package: DecisionPackage,
) -> bool:
    bounds = package.capability_bounds
    return (
        bounds.text_scale_min <= settings.text_scale <= bounds.text_scale_max
        and bounds.line_height_min <= settings.line_height <= bounds.line_height_max
        and bounds.letter_spacing_em_min
        <= settings.letter_spacing_em
        <= bounds.letter_spacing_em_max
        and bounds.contrast_ratio_min
        <= settings.target_contrast_ratio
        <= bounds.contrast_ratio_max
        and bounds.target_size_px_min
        <= settings.target_size_px
        <= bounds.target_size_px_max
    )


def _safe_defer(
    decision: HumanDecision,
    reason_code: str,
    rationale: str,
) -> HumanDecision:
    return HumanDecision(
        action=Action.DEFER,
        confidence=0.0,
        perceived_accessibility_fit=decision.perceived_accessibility_fit,
        reason_codes=[reason_code],
        rationale=rationale,
    )


def normalize_decision(
    decision: HumanDecision,
    package: DecisionPackage,
) -> HumanDecision:
    selected = _normalize_plan_id(decision.selected_plan_id, package)
    if selected != decision.selected_plan_id:
        decision = decision.model_copy(update={"selected_plan_id": selected})

    if decision.action in {Action.REJECT, Action.DEFER}:
        return decision.model_copy(
            update={"selected_plan_id": None, "customized_settings": None}
        )

    if package.stage == 1:
        if decision.action != Action.APPROVE:
            return _safe_defer(
                decision,
                "invalid_level_1_action",
                "A resposta não corresponde às ações permitidas no Level 1.",
            )
        selected = decision.selected_plan_id or package.recommended_plan_id
        if selected != package.recommended_plan_id:
            return _safe_defer(
                decision,
                "invalid_level_1_plan",
                "O Level 1 só permite aprovar o plano recomendado.",
            )
        return decision.model_copy(
            update={
                "selected_plan_id": package.recommended_plan_id,
                "customized_settings": None,
            }
        )

    if package.stage == 2:
        if decision.action != Action.SELECT or not decision.selected_plan_id:
            return _safe_defer(
                decision,
                "invalid_level_2_selection",
                "O Level 2 exige a seleção de um plano candidato.",
            )
        return decision.model_copy(update={"customized_settings": None})

    if package.stage == 3:
        if decision.action == Action.SELECT and decision.selected_plan_id:
            return decision.model_copy(update={"customized_settings": None})
        if (
            decision.action == Action.CUSTOMIZE
            and decision.customized_settings is not None
            and _within_capabilities(decision.customized_settings, package)
        ):
            return decision.model_copy(update={"selected_plan_id": None})
        return _safe_defer(
            decision,
            "invalid_level_3_action",
            "A ação personalizada está ausente ou fora das capacidades do sistema.",
        )

    return _safe_defer(
        decision,
        "invalid_stage",
        "O nível de envolvimento não permite uma decisão humana.",
    )
