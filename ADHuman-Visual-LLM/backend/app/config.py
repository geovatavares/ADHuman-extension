from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Permite executar os testes centrais antes da instalação.
    def load_dotenv(*args, **kwargs) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL", "http://127.0.0.1:11434"
    ).rstrip("/")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    # Para os experimentos automatizados, nunca usar menos de 300 s,
    # mesmo que um .env antigo ainda defina OLLAMA_TIMEOUT_SECONDS=120.
    ollama_timeout_seconds: float = max(
        300.0,
        float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")),
    )
    ollama_temperature: float = float(
        os.getenv("OLLAMA_TEMPERATURE", "0.2")
    )
    simulator_host: str = os.getenv("SIMULATOR_HOST", "127.0.0.1")
    simulator_port: int = int(os.getenv("SIMULATOR_PORT", "8000"))
    log_dir: Path = PROJECT_ROOT / os.getenv("LOG_DIR", "logs")
    prompt_version: str = os.getenv("PROMPT_VERSION", "3.0.0-visual-acuity")


settings = Settings()
