from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from cerebras.cloud.sdk import Cerebras

from .claims import extract_claims_from_text


def extract_claims_from_url(
    cerebras_client: Cerebras,
    *,
    url: str,
    model: str,
    max_claims: int = 8,
    timeout_seconds: int = 10,
) -> list[str]:
    """Fetches main content from a URL and uses the LLM to extract factual claims."""

    print(f"Fetching content from URL: {url}")

    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={
                "User-Agent": "cerebras-fact-checker/0.1 (+https://cookbook.openai.com/)"
            },
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        main_content_div = soup.find("article") or soup.find("main")
        if main_content_div:
            main_text = " ".join([p.get_text(" ", strip=True) for p in main_content_div.find_all("p")])
        else:
            main_text_elements = soup.find_all(["p", "h1", "h2", "h3"])
            main_text = " ".join([elem.get_text(" ", strip=True) for elem in main_text_elements])

        if not main_text or len(main_text.strip()) < 100:
            print(f"Warning: Not enough main text found for URL: {url}")
            return []

        print(
            f"Extracted {len(main_text)} characters from the URL. Now extracting claims..."
        )

        return extract_claims_from_text(
            cerebras_client,
            text=main_text,
            model=model,
            max_claims=max_claims,
        )

    except requests.exceptions.RequestException as e:
        print(f"Error fetching content from URL {url}: {e}")
        return []
    except Exception as e:
        print(f"Error processing URL {url}: {e}")
        return []
