from __future__ import annotations

import textwrap
from typing import Any


def build_evidence_context(results: list[dict[str, Any]], max_chars: int = 8000) -> str:
    blocks: list[str] = []
    
    if not results:
        return ""
        
    # Per-Source Truncation (The Equal Slice Rule)
    # Guarantee that every source gets a perfectly equal share of the context window.
    max_chars_per_source = max_chars // len(results)

    for idx, r in enumerate(results):
        excerpts_list = r.get("excerpts") or []
        excerpts_text = "\n\n".join(excerpts_list)
        
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
        
        if len(block) > max_chars_per_source:
            block = block[:max_chars_per_source] + "\n\n[Excerpt truncated for source limit]"
            
        blocks.append(block)

    context = "\n\n".join(blocks)

    return context
