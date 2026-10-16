from __future__ import annotations

from app.models import CandidatePlan, VisualProfile


def _similarity(actual: float, preferred: float, zero_scale: float | None = None) -> float:
    """Return closeness to a synthetic preferred value, not mere threshold coverage.

    The previous implementation saturated at 1.0 whenever a plan exceeded a
    preferred value. That made, for example, 4.5:1 and 15:1 equally compatible
    with the reference profile. Here the profile values are treated as
    experimental target preferences, so both undershoot and overshoot reduce
    similarity. For a zero preferred letter-spacing, zero_scale avoids a
    division by zero while keeping the score bounded.
    """
    actual = float(actual)
    preferred = float(preferred)
    if preferred == 0.0:
        if zero_scale is None or zero_scale <= 0:
            return 1.0 if actual == 0.0 else 0.0
        return max(0.0, 1.0 - abs(actual) / zero_scale)
    larger = max(abs(actual), abs(preferred))
    if larger == 0.0:
        return 1.0
    return min(abs(actual), abs(preferred)) / larger


def plan_fit(plan: CandidatePlan, profile: VisualProfile) -> dict[str, float]:
    settings = plan.resulting_settings
    preferences = profile.preferences
    components = {
        "contrast": _similarity(
            settings.target_contrast_ratio,
            preferences.target_contrast_ratio,
        ),
        "text_scale": _similarity(
            settings.text_scale,
            preferences.preferred_text_scale,
        ),
        "line_height": _similarity(
            settings.line_height,
            preferences.preferred_line_height,
        ),
        "letter_spacing": _similarity(
            settings.letter_spacing_em,
            preferences.preferred_letter_spacing_em,
            zero_scale=0.12,
        ),
        "target_size": _similarity(
            float(settings.target_size_px),
            float(preferences.preferred_target_size_px),
        ),
        "high_contrast": 1.0
        if settings.high_contrast == preferences.prefers_high_contrast
        else 0.0,
    }
    score = sum(components.values()) / len(components)
    return {
        "score": round(score, 3),
        **{key: round(value, 3) for key, value in components.items()},
    }


def build_fit_matrix(
    plans: list[CandidatePlan],
    profile: VisualProfile,
) -> dict[str, dict[str, float]]:
    return {plan.id: plan_fit(plan, profile) for plan in plans}
