from __future__ import annotations

import textwrap
from typing import Any


def build_evidence_context(results: list[dict[str, Any]], max_chars: int = 8000) -> str:
    blocks: list[str] = []

    for idx, r in enumerate(results):
        excerpts_text = "\n\n".join((r.get("excerpts") or [])[:2])
        block = textwrap.dedent(
            f"""
            [Source {idx + 1}]
            Title: {r.get('title') or r.get('url')}
            URL: {r.get('url')}
            Publish date: {r.get('publish_date')}

            Excerpts:
            {excerpts_text}
            """
        ).strip()
        blocks.append(block)

    context = "\n\n".join(blocks)
    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n[Context truncated for length]"

    return context
