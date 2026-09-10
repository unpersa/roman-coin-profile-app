from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    project_dir: Path
    processed_dir: Path
    cache_dir: Path
    gemini_model: str
    gemini_verifier_model: str
    gemini_fallback_model: str = "gemini-3.6-flash"
    top_k_candidates: int = 15
    rrf_k: int = 60
    hybrid_local_weight: float = 1.0
    hybrid_api_weight: float = 1.0
    request_timeout: int = 30

    @classmethod
    def from_environment(cls) -> "Settings":
        project_dir = Path(os.getenv(
            "ROMAN_COIN_PROJECT_DIR",
            ".",
        ))
        processed_dir = project_dir / "data" / "processed"
        cache_dir = processed_dir / "app_runtime_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        model = os.getenv("GEMINI_VISION_MODEL", "gemini-3.7-flash")
        verifier = os.getenv("GEMINI_VERIFIER_MODEL", model)
        fallback = os.getenv(
            "GEMINI_FALLBACK_MODEL",
            "gemini-3.6-flash",
        ).strip()
        return cls(
            project_dir=project_dir,
            processed_dir=processed_dir,
            cache_dir=cache_dir,
            gemini_model=model,
            gemini_verifier_model=verifier,
            gemini_fallback_model=fallback,
        )

def get_secret(
    name: str,
):
    value = str(
        os.getenv(
            name,
            "",
        )
        or ""
    ).strip()

    if value:
        return value

    try:
        import streamlit as st

        value = str(
            st.secrets.get(
                name,
                "",
            )
            or ""
        ).strip()

        if value:
            return value

    except Exception:
        pass

    return None
