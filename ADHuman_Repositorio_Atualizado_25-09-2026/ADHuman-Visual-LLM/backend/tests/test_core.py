import unittest

from app.decision_validation import normalize_decision
from app.models import Action, DecisionPackage, HumanDecision, VisualSettings
from app.profile_fit import build_fit_matrix
from app.profiles import get_profile, load_profiles
from app.prompts import build_messages


def settings(
    scale: float,
    line_height: float,
    spacing: float,
    contrast: float,
    target: int,
    high_contrast: bool,
) -> dict:
    return {
        "text_scale": scale,
        "line_height": line_height,
        "letter_spacing_em": spacing,
        "target_contrast_ratio": contrast,
        "target_size_px": target,
        "high_contrast": high_contrast,
    }


def sample_package(stage: int = 1) -> DecisionPackage:
    return DecisionPackage.model_validate(
        {
            "scenario_id": "test-scenario",
            "stage": stage,
            "page": {
                "url": "https://example.org",
                "title": "Teste",
                "context": "Contraste e legibilidade",
            },
            "violations": [
                {
                    "id": "v1",
                    "criterion": "WCAG 1.4.3",
                    "element": "Texto 1",
                    "description": "Contraste insuficiente",
                    "severity": "high",
                    "current_value": 2.1,
                    "required_value": 4.5,
                }
            ],
            "recommended_plan_id": "plan_enhanced",
            "candidate_plans": [
                {
                    "id": "plan_minimum",
                    "name": "Correção mínima",
                    "description": "Corrigir contraste",
                    "resulting_settings": settings(1.0, 1.5, 0.0, 4.5, 24, False),
                    "predicted_benefit": 0.66,
                    "regression_risk": 0.08,
                    "uncertainty": 0.08,
                    "visual_change_cost": 0.08,
                    "reversible": True,
                },
                {
                    "id": "plan_enhanced",
                    "name": "Legibilidade reforçada",
                    "description": "Aumentar contraste e texto",
                    "resulting_settings": settings(1.25, 1.5, 0.02, 7.0, 28, True),
                    "predicted_benefit": 0.84,
                    "regression_risk": 0.22,
                    "uncertainty": 0.12,
                    "visual_change_cost": 0.35,
                    "reversible": True,
                },
                {
                    "id": "plan_low_vision",
                    "name": "Baixa visão",
                    "description": "Ampliação e alto contraste",
                    "resulting_settings": settings(1.75, 1.7, 0.06, 15.0, 44, True),
                    "predicted_benefit": 0.97,
                    "regression_risk": 0.44,
                    "uncertainty": 0.18,
                    "visual_change_cost": 0.78,
                    "reversible": True,
                },
            ],
        }
    )


class CoreTests(unittest.TestCase):
    def test_four_visual_acuity_profiles_are_loaded(self) -> None:
        self.assertEqual(
            set(load_profiles()),
            {
                "acuity_reference",
                "acuity_mild",
                "acuity_moderate",
                "acuity_severe",
            },
        )

    def test_prompt_contains_profile_stage_and_untrusted_rule(self) -> None:
        profile = get_profile("acuity_moderate")
        self.assertIsNotNone(profile)
        messages = build_messages(profile, sample_package(stage=2))
        self.assertIn("DADOS NÃO CONFIÁVEIS", messages[0]["content"])
        self.assertIn('"id": "acuity_moderate"', messages[1]["content"])
        self.assertIn("LEVEL 2", messages[1]["content"])
        self.assertIn("COMPATIBILIDADE CALCULADA", messages[1]["content"])

    def test_fit_changes_with_acuity_profile(self) -> None:
        package = sample_package(stage=2)
        reference = get_profile("acuity_reference")
        mild = get_profile("acuity_mild")
        moderate = get_profile("acuity_moderate")
        severe = get_profile("acuity_severe")
        reference_fit = build_fit_matrix(package.candidate_plans, reference)
        mild_fit = build_fit_matrix(package.candidate_plans, mild)
        moderate_fit = build_fit_matrix(package.candidate_plans, moderate)
        severe_fit = build_fit_matrix(package.candidate_plans, severe)

        # Synthetic target preferences must discriminate the candidate plans.
        self.assertGreater(
            reference_fit["plan_minimum"]["score"],
            reference_fit["plan_enhanced"]["score"],
        )
        self.assertGreater(
            mild_fit["plan_enhanced"]["score"],
            mild_fit["plan_minimum"]["score"],
        )
        self.assertGreater(
            moderate_fit["plan_low_vision"]["score"],
            moderate_fit["plan_enhanced"]["score"],
        )
        self.assertGreater(
            severe_fit["plan_low_vision"]["score"],
            severe_fit["plan_enhanced"]["score"],
        )

    def test_level_1_only_approves_recommended_plan(self) -> None:
        decision = HumanDecision(
            action=Action.APPROVE,
            selected_plan_id="plan_minimum",
            confidence=0.9,
            rationale="Aprovar.",
        )
        normalized = normalize_decision(decision, sample_package(stage=1))
        self.assertEqual(normalized.action, Action.DEFER)

    def test_level_1_fills_missing_recommended_id(self) -> None:
        decision = HumanDecision(
            action=Action.APPROVE,
            confidence=0.8,
            rationale="A recomendação atende ao perfil.",
        )
        normalized = normalize_decision(decision, sample_package(stage=1))
        self.assertEqual(normalized.action, Action.APPROVE)
        self.assertEqual(normalized.selected_plan_id, "plan_enhanced")

    def test_level_2_accepts_safe_plan_alias(self) -> None:
        decision = HumanDecision(
            action=Action.SELECT,
            selected_plan_id="Plano 3",
            confidence=0.8,
            rationale="Selecionar plano de baixa visão.",
        )
        normalized = normalize_decision(decision, sample_package(stage=2))
        self.assertEqual(normalized.action, Action.SELECT)
        self.assertEqual(normalized.selected_plan_id, "plan_low_vision")

    def test_level_3_accepts_settings_within_capabilities(self) -> None:
        decision = HumanDecision(
            action=Action.CUSTOMIZE,
            customized_settings=VisualSettings(
                text_scale=2.0,
                line_height=1.8,
                letter_spacing_em=0.08,
                target_contrast_ratio=15.0,
                target_size_px=44,
                high_contrast=True,
            ),
            confidence=0.8,
            rationale="Configuração adequada ao perfil.",
        )
        normalized = normalize_decision(decision, sample_package(stage=3))
        self.assertEqual(normalized.action, Action.CUSTOMIZE)
        self.assertIsNotNone(normalized.customized_settings)


if __name__ == "__main__":
    unittest.main()
