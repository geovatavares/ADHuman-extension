from __future__ import annotations

import json
import time
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.models import HumanDecision


class OllamaError(RuntimeError):
    """Falha de conexão ou resposta inválida do Ollama."""


@dataclass(frozen=True)
class OllamaDecisionResult:
    decision: HumanDecision
    inference_time_ms: int
    raw_content: str


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        temperature: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Não foi possível conectar ao Ollama em {self.base_url}."
            ) from exc

        payload = response.json()
        return [
            item.get("name", "")
            for item in payload.get("models", [])
            if item.get("name")
        ]

    async def decide(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        allowed_plan_ids: list[str],
        stage: int,
    ) -> OllamaDecisionResult:
        response_schema = HumanDecision.model_json_schema()
        stage_actions = {
            1: ["approve", "reject", "defer"],
            2: ["select", "reject", "defer"],
            3: ["select", "customize", "reject", "defer"],
        }
        response_schema["properties"]["action"] = {
            "type": "string",
            "enum": stage_actions[stage],
        }
        response_schema["properties"]["selected_plan_id"] = {
            "anyOf": [
                {"type": "string", "enum": allowed_plan_ids},
                {"type": "null"},
            ],
            "default": None,
        }
        # These fields are experimental measurements, so require the LLM to
        # provide them instead of silently accepting Pydantic defaults.
        response_schema["properties"]["confidence"] = {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        }
        response_schema["properties"]["perceived_accessibility_fit"] = {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        }
        response_schema["properties"]["reason_codes"] = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 4,
        }
        required = list(response_schema.get("required", []))
        for field in (
            "action",
            "confidence",
            "perceived_accessibility_fit",
            "reason_codes",
            "rationale",
        ):
            if field not in required:
                required.append(field)
        response_schema["required"] = required
        request_payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "format": response_schema,
            "options": {
                "temperature": self.temperature,
                "num_predict": 650,
            },
        }

        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=request_payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            details = exc.response.text[:500]
            raise OllamaError(
                f"Ollama retornou HTTP {exc.response.status_code}: {details}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Não foi possível consultar o Ollama em {self.base_url}."
            ) from exc

        inference_time_ms = int((time.perf_counter() - start) * 1000)
        try:
            payload = response.json()
            raw_content = payload["message"]["content"]
            decision = HumanDecision.model_validate(json.loads(raw_content))
        except (KeyError, json.JSONDecodeError, ValidationError) as exc:
            raise OllamaError(
                "O Ollama respondeu, mas a decisão não corresponde ao JSON esperado."
            ) from exc

        return OllamaDecisionResult(
            decision=decision,
            inference_time_ms=inference_time_ms,
            raw_content=raw_content,
        )
