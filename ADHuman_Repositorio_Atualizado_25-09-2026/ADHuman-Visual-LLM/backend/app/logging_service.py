from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any


class JsonlRunLogger:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.path = log_dir / "simulation-runs.jsonl"
        self._lock = asyncio.Lock()

    async def append(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        async with self._lock:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(self._append_sync, line)

    def _append_sync(self, line: str) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
