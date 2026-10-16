from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.decision_validation import normalize_decision
from app.logging_service import JsonlRunLogger
from app.models import OllamaHealth, SimulationMetadata, SimulationRequest, SimulationResponse
from app.ollama_client import OllamaClient, OllamaError
from app.profile_fit import build_fit_matrix
from app.profiles import get_profile, load_profiles
from app.prompts import build_messages


app = FastAPI(
    title="ADHuman Visual Profiles — Ollama Human Proxy",
    description=(
        "Backend local que usa Ollama para simular participantes com perfis "
        "sintéticos de acuidade visual funcional."
    ),
    version="3.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

ollama = OllamaClient(
    base_url=settings.ollama_base_url,
    timeout_seconds=settings.ollama_timeout_seconds,
    temperature=settings.ollama_temperature,
)
run_logger = JsonlRunLogger(settings.log_dir)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "adhuman-visual-ollama-proxy"}


@app.get("/health/ollama", response_model=OllamaHealth)
async def health_ollama(
    model: str | None = Query(default=None),
) -> OllamaHealth:
    configured_model = model or settings.ollama_model
    try:
        available_models = await ollama.list_models()
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    status = "ready" if configured_model in available_models else "model_not_found"
    return OllamaHealth(
        status=status,
        base_url=settings.ollama_base_url,
        configured_model=configured_model,
        available_models=available_models,
    )


@app.get("/profiles")
async def profiles() -> list[dict]:
    return [
        profile.model_dump(mode="json")
        for profile in load_profiles().values()
    ]


@app.post("/simulation/decide", response_model=SimulationResponse)
async def decide(request: SimulationRequest) -> SimulationResponse:
    profile = get_profile(request.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail=f"Perfil visual desconhecido: {request.profile_id}",
        )

    if request.decision_package.stage == 0:
        raise HTTPException(
            status_code=422,
            detail="Level 0 é autônomo e não solicita decisão humana.",
        )

    model = request.model or settings.ollama_model
    run_id = str(uuid4())
    messages = build_messages(profile, request.decision_package)
    fit_matrix = build_fit_matrix(
        request.decision_package.candidate_plans,
        profile,
    )
    try:
        result = await ollama.decide(
            model=model,
            messages=messages,
            allowed_plan_ids=[
                plan.id for plan in request.decision_package.candidate_plans
            ],
            stage=request.decision_package.stage,
        )
    except OllamaError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    decision = normalize_decision(result.decision, request.decision_package)
    metadata = SimulationMetadata(
        run_id=run_id,
        profile_id=profile.id,
        profile_name=profile.name,
        stage=request.decision_package.stage,
        model=model,
        prompt_version=settings.prompt_version,
        llm_inference_time_ms=result.inference_time_ms,
        used_llm=True,
        decision_validated=not any(
            code.startswith("invalid_") for code in decision.reason_codes
        ),
    )
    response = SimulationResponse(decision=decision, metadata=metadata)

    await run_logger.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "profile": profile.model_dump(mode="json"),
            "profile_plan_fit": fit_matrix,
            "request": request.model_dump(mode="json"),
            "prompt_messages": messages,
            "response": response.model_dump(mode="json"),
            "raw_llm_content": result.raw_content,
        }
    )
    return response
