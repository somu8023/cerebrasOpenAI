from __future__ import annotations

from cerebras.cloud.sdk import Cerebras
from parallel import Parallel

from .config import Settings


def create_clients(settings: Settings) -> tuple[Cerebras, Parallel]:
    cerebras_client = Cerebras(
        api_key=settings.cerebras_api_key,
        default_headers={
            "X-Cerebras-3rd-Party-Integration": "parallel-ai-workshop",
        },
    )
    parallel_client = Parallel(api_key=settings.parallel_api_key)
    return cerebras_client, parallel_client
