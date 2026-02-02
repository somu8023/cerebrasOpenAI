from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from parallel import Parallel


def score_source_quality(url: str) -> tuple[int, str]:
    """Score a source based on domain authority and reliability.
    
    Returns (score, tier) where higher score = more authoritative.
    """
    domain = urlparse(url).netloc.lower()
    
    # Tier 1: Government and official sources (score 100)
    if any(domain.endswith(tld) for tld in ['.gov', '.gov.in', '.nic.in']):
        return (100, 'Government')
    
    # Tier 2: Educational institutions (score 90)
    if any(domain.endswith(tld) for tld in ['.edu', '.ac.in', '.ac.uk']):
        return (90, 'Educational')
    
    # Tier 3: Major news organizations (score 80)
    major_news = [
        'bbc.com', 'reuters.com', 'apnews.com', 'npr.org',
        'nytimes.com', 'wsj.com', 'washingtonpost.com',
        'thehindu.com', 'indianexpress.com', 'hindustantimes.com',
        'timesofindia.com', 'ndtv.com', 'theguardian.com'
    ]
    if any(news in domain for news in major_news):
        return (80, 'Major News')
    
    # Tier 4: Reputable organizations (score 70)
    if any(domain.endswith(tld) for tld in ['.org']):
        return (70, 'Organization')
    
    # Tier 5: Other sources - deprioritize
    # Low-quality patterns
    low_quality_patterns = [
        'onefivenine.com',  # Village directories
        'villageinfo.in',
        'mapsofindia.com',
        'citypopulation.de',
    ]
    if any(pattern in domain for pattern in low_quality_patterns):
        return (10, 'Low-quality')
    
    # Default tier
    return (50, 'Other')


def generate_search_variations(claim: str) -> list[str]:
    """Generate multiple search query variations from a claim to improve search accuracy.
    
    This helps avoid issues where similar words (like 'Patna' vs 'Patan') cause confusion.
    """
    queries = [
        claim,  # Original claim
        f"verify: {claim}",  # Verification framing
        f"fact check: {claim}",  # Fact-check framing
    ]
    
    # Extract potential entity-based queries by looking for "is in" patterns
    if " is in " in claim.lower():
        parts = claim.lower().split(" is in ")
        if len(parts) == 2:
            entity = parts[0].strip()
            location = parts[1].strip()
            queries.append(f"where is {entity}")
            queries.append(f"{entity} location")
            queries.append(f"{entity} {location}")
    
    return queries[:5]  # Limit to 5 variations


def search_web(
    parallel_client: Parallel,
    *,
    query: str | list[str],
    num: int = 5,
    mode: str = "one-shot",
    max_chars_per_result: int = 8000,
) -> list[dict[str, Any]]:
    """Search the web using Parallel's Search API.

    Returns dicts with: url, title, publish_date, excerpts.
    """
    # Handle both single query and list of queries
    if isinstance(query, str):
        queries = [query]
    else:
        queries = query
    
    # Use first query for objective, but search with all variations
    objective = (
        "Find high-quality, up-to-date sources that answer the question:\n\n"
        f"{queries[0]}\n\n"
        "Prefer authoritative sites (e.g., .gov, .edu, major news, or official org websites). "
        "EXCLUDE Wikipedia and other wiki sites."
    )

    search = parallel_client.beta.search(
        objective=objective,
        search_queries=queries,
        mode=mode,
        max_results=num,
        excerpts={
            "max_chars_per_result": max_chars_per_result,
        },
    )

    all_results: list[dict[str, Any]] = []
    wikipedia_count = 0
    
    for r in search.results:
        url_lower = r.url.lower()
        
        # Completely exclude Wikipedia
        if any(domain in url_lower for domain in ["wikipedia.org", "wiki/"]):
            wikipedia_count += 1
            continue
        
        result_dict = {
            "url": r.url,
            "title": getattr(r, "title", None),
            "publish_date": getattr(r, "publish_date", None),
            "excerpts": list(r.excerpts or []),
        }
        
        # Score the source quality
        score, tier = score_source_quality(r.url)
        result_dict["quality_score"] = score
        result_dict["quality_tier"] = tier
        all_results.append(result_dict)
    
    # Sort by quality score (highest first)
    all_results.sort(key=lambda x: x["quality_score"], reverse=True)
    
    # Filter out low-quality sources if we have better options
    high_quality = [r for r in all_results if r["quality_score"] >= 50]
    low_quality = [r for r in all_results if r["quality_score"] < 50]
    
    # Prefer high-quality sources
    if high_quality:
        results = high_quality[:num]
    else:
        # If no high-quality sources, use what we have
        results = all_results[:num]
    
    return results
