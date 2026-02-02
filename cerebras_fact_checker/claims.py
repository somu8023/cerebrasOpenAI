from __future__ import annotations

import json
import re
import time

from cerebras.cloud.sdk import Cerebras


_CODE_FENCE_PREFIX_RE = re.compile(r"^\s*```(?:json)?\s*", flags=re.IGNORECASE)
_CODE_FENCE_SUFFIX_RE = re.compile(r"\s*```\s*$")


def _strip_json_fences(raw: str) -> str:
    raw = raw.strip()
    raw = _CODE_FENCE_PREFIX_RE.sub("", raw)
    raw = _CODE_FENCE_SUFFIX_RE.sub("", raw)
    return raw.strip()


def extract_claims_from_text(
    cerebras_client: Cerebras,
    *,
    text: str,
    model: str,
    max_claims: int = 8,
    reasoning_effort: str = "medium",
) -> list[str]:
    """Use Cerebras LLM to extract atomic factual claims from text.

    Output format (strict JSON): {"claims": ["...", ...]}
    """

    system_prompt_content = (
        "You are an information extraction assistant.\n"
        f"From the user's text, extract up to {max_claims} atomic factual claims.\n"
        "Each claim should:\n"
        "- Be checkable against external sources (dates, numbers, named entities)\n"
        "- Be concrete and not an opinion.\n\n"
        "Return STRICT JSON:\n"
        "{\n"
        '  "claims": ["...", "..."]\n'
        "}\n"
    )

    user_prompt_content = f"Text:\n\n{text}\n\nExtract up to {max_claims} factual claims."

    messages = [
        {"role": "system", "content": system_prompt_content},
        {"role": "user", "content": user_prompt_content},
    ]

    start_time = time.time()
    resp = cerebras_client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1.0,
        top_p=1.0,
        max_tokens=4096,
        reasoning_effort=reasoning_effort,
    )
    raw = resp.choices[0].message.content
    end_time = time.time()

    # Keep print behavior similar to the notebook, but the CLI can mute if needed.
    print(f"Cerebras LLM claim extraction took {end_time - start_time:.2f} seconds")

    raw = _strip_json_fences(raw)

    try:
        data = json.loads(raw)
        claims = data.get("claims", [])
        claims = [c.strip() for c in claims if isinstance(c, str) and c.strip()]
        return claims[:max_claims]
    except Exception as e:
        print("Error parsing claims JSON:", e)
        print("Raw model output:\n", raw)
        return []
