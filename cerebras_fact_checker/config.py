from __future__ import annotations

import os
from dataclasses import dataclass


def _getenv(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


@dataclass(frozen=True)
class Settings:
    cerebras_api_key: str
    parallel_api_key: str
    cerebras_model_name: str = "llama3.1-70b"
    parallel_search_mode: str = "one-shot"
    parallel_max_results: int = 6


def load_settings() -> Settings:
    cerebras_api_key = _getenv("CEREBRAS_API_KEY")
    parallel_api_key = _getenv("PARALLEL_API_KEY")

    if not cerebras_api_key or not parallel_api_key:
        raise RuntimeError(
            "Set CEREBRAS_API_KEY and PARALLEL_API_KEY as environment variables (or in a .env file)."
        )

    model = _getenv("CEREBRAS_MODEL_NAME", "llama3.1-70b") or "llama3.1-70b"
    mode = _getenv("PARALLEL_SEARCH_MODE", "one-shot") or "one-shot"

    max_results_raw = _getenv("PARALLEL_MAX_RESULTS")
    max_results = 6
    if max_results_raw:
        try:
            max_results = int(max_results_raw)
        except ValueError:
            max_results = 6

    return Settings(
        cerebras_api_key=cerebras_api_key,
        parallel_api_key=parallel_api_key,
        cerebras_model_name=model,
        parallel_search_mode=mode,
        parallel_max_results=max_results,
    )
