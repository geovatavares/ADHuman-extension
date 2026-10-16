from __future__ import annotations

import json
from functools import lru_cache

from app.config import PROJECT_ROOT
from app.models import VisualProfile


PROFILES_PATH = PROJECT_ROOT / "profiles" / "profiles.json"


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, VisualProfile]:
    raw_profiles = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    profiles = [VisualProfile.model_validate(item) for item in raw_profiles]
    return {profile.id: profile for profile in profiles}


def get_profile(profile_id: str) -> VisualProfile | None:
    return load_profiles().get(profile_id)
