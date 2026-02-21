from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from parallel import Parallel


def score_source_quality(url: str) -> tuple[int, str]:
    """Score a source based on domain authority and reliability.

    Option H implementation:
      - Explicit allowlists at every tier (no TLD freebies except .gov/.edu)
      - Keyword-in-domain heuristic auto-catches aggregators not in denylist
      - Default for unknowns is 20 (used for LLM context, never shown to user)

    Returns (score, tier_label).
    """
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    # ── Tier 0 (score 110): Primary statistical / intergovernmental datasets ────
    tier0 = [
        "data.worldbank.org", "worldbank.org",
        "imf.org", "datamapper.imf.org", "data.imf.org",
        "data.oecd.org", "stats.oecd.org", "oecd.org",
        "unstats.un.org", "data.un.org", "un.org",
        "data.who.int", "who.int",
        "eurostat.ec.europa.eu",
        "ons.gov.uk",
        "bls.gov", "bea.gov", "census.gov", "fred.stlouisfed.org",
        "ourworldindata.org",
        "unodc.org", "ilo.org", "wto.org",
        "databank.worldbank.org",
    ]
    if any(domain == d or domain.endswith("." + d) for d in tier0):
        return (110, "Statistical DB")

    # ── Tier 1 (score 100): Government TLDs ─────────────────────────────────────
    gov_tlds = [".gov", ".gov.in", ".nic.in", ".gov.uk", ".gov.au",
                ".gov.ca", ".gouv.fr", ".gob.mx", ".gov.sg", ".govt.nz"]
    if any(domain.endswith(t) for t in gov_tlds):
        return (100, "Government")

    # ── Tier 2 (score 90): Educational institutions ──────────────────────────────
    edu_tlds = [".edu", ".ac.in", ".ac.uk", ".edu.au"]
    if any(domain.endswith(t) for t in edu_tlds):
        return (90, "Educational")

    # ── Tier 3a (score 85): Trusted non-profit / intergovernmental .org ──────────
    # Only explicitly listed orgs — .org alone is NOT sufficient
    trusted_orgs = [
        "who.int", "unicef.org", "undp.org", "unfpa.org",
        "wfp.org", "unep.org", "unhcr.org", "iaea.org",
        "nato.int", "icrc.org",
        "pewresearch.org", "brookings.edu",
        "rand.org", "chathamhouse.org",
        "oxfam.org", "amnesty.org", "hrw.org",
        "nature.com", "sciencedirect.com", "pubmed.ncbi.nlm.nih.gov",
        "scholar.google.com",
        # Official sports governing bodies
        "icc-cricket.com", "bcci.tv",
        "fifa.com", "uefa.com",
        "olympics.com", "olympic.org",
        "iaaf.org", "worldathletics.org",
        "itf.com", "atptour.com", "wtatennis.com",
        "nba.com", "nfl.com", "mlb.com", "nhl.com",
        "formula1.com",
    ]
    if any(domain == d or domain.endswith("." + d) for d in trusted_orgs):
        return (85, "Trusted Org")

    # ── Tier 3b (score 80): Major established news organisations ────────────────
    major_news = [
        "bbc.com", "reuters.com", "apnews.com", "npr.org",
        "nytimes.com", "wsj.com", "washingtonpost.com",
        "theguardian.com", "economist.com", "ft.com", "bloomberg.com",
        "thehindu.com", "indianexpress.com", "hindustantimes.com",
        "timesofindia.com", "ndtv.com",
        "dw.com", "aljazeera.com", "france24.com",
        "scmp.com",  # South China Morning Post
        "businessinsider.com", "cnbc.com", "forbes.com",
        # Sports statistics & reference databases
        "espncricinfo.com", "cricbuzz.com",
        "sports-reference.com", "baseball-reference.com",
        "basketball-reference.com", "fbref.com",
        "transfermarkt.com",
        "espn.com",
    ]
    if any(n in domain for n in major_news):
        return (80, "Major News")

    # ── Keyword-in-domain heuristic: likely aggregator (score 15) ────────────────
    # Domains containing these words are almost always country-comparison /
    # ranking aggregators or SEO data-republishers — regardless of TLD.
    aggregator_keywords = [
        "rank", "ranking", "compare", "comparison",
        "economy", "economies", "economic",
        "countrystat", "worldstat", "globalstat",
        "profile", "indicator", "statistics",
        "mylife", "numbeo", "knoema", "macrotrend",
    ]
    if any(kw in domain for kw in aggregator_keywords):
        return (15, "Likely Aggregator")

    # ── Explicit denylist (score 5) ──────────────────────────────────────────────
    denylist = [
        "countryeconomy.com", "mylifeelsewhere.com", "numbeo.com",
        "nationmaster.com", "indexmundi.com",
        "globaleconomy.com", "theglobaleconomy.com", "worldometers.info",
        "tradingeconomics.com", "macrotrends.net", "knoema.com",
        "georank.org",
        "cleartax.in", "investopedia.com", "bankbazaar.com",
        "paisabazaar.com", "groww.in", "moneycontrol.com",
        "business-standard.com", "livemint.com",
        "economictimes.indiatimes.com",
        "onefivenine.com", "villageinfo.in", "mapsofindia.com",
        "citypopulation.de",
    ]
    if any(d in domain for d in denylist):
        return (5, "Blocked")

    # ── Default: unknown domain ──────────────────────────────────────────────────
    # Score 20 = passes to LLM for context, but NEVER shown to user (display
    # threshold is >= 80). Unknown != trusted.
    return (20, "Other")


def generate_search_variations(claim: str) -> list[str]:
    import datetime
    import re
    
    current_year = str(datetime.datetime.now().year)

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
            
    # Auto-inject current year if no year is mentioned in the claim
    if not re.search(r'\b(19|20)\d{2}\b', claim):
        queries.append(f"{claim} {current_year}")

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
    import textwrap
    objective = textwrap.dedent(
        f"""
        Find high-quality, up-to-date sources that answer the question: {queries[0]}
        
        ONLY return results from highly authoritative sources:
        - Government (.gov)
        - Educational (.edu)
        - Peer-reviewed journals
        - Official statistical agencies
        - Major established news organizations citing primary data

        EXCLUDE:
        - Wikipedia and wikis
        - Social media
        - Forums
        - Q&A sites (Quora, Reddit, StackExchange)
        - Blogs and opinion pieces
        - Review sites
        - E-commerce sites
        - Business directories
        - User-generated content
        - Dataset portals or catalog pages without reported statistics

        CRITICAL EVIDENCE REQUIREMENTS:

        - Only return excerpts that contain explicit factual or quantitative evidence.
        - The number must be visible in the article text (not only in downloadable files).
        - If the query does not specify a year, prioritize pulling text that contains recent data or current year estimates.
        """
    ).strip()

    # Request extra results to compensate for aggressive post-filtering
    fetch_count = num * 3 + 4

    search = parallel_client.beta.search(
        objective=objective,
        search_queries=queries,
        mode=mode,
        max_results=fetch_count,
        excerpts={
            "max_chars_per_result": max_chars_per_result,
        },
    )

    all_results: list[dict[str, Any]] = []
    wikipedia_count = 0
    
    # Hard-exclude: sources that should NEVER appear in fact-checking results
    excluded_domains = [
        # Wikis & crowdsourced knowledge
        "wikipedia.org", "wiki/", "fandom.com", "wikia.com",
        # Q&A / Forums / User-generated opinion platforms
        "quora.com", "reddit.com", "yahoo.com/answers",
        "stackexchange.com", "stackoverflow.com",
        "warriorforum.com", "discourse.org",
        # Social media
        "twitter.com", "x.com", "facebook.com", "instagram.com",
        "tiktok.com", "pinterest.com", "linkedin.com/posts",
        "threads.net", "mastodon.", "bsky.app",
        # Video platforms (transcripts unreliable)
        "youtube.com", "youtu.be", "vimeo.com",
    ]

    for r in search.results:
        url_lower = r.url.lower()
        
        # Completely exclude unreliable sources
        if any(domain in url_lower for domain in excluded_domains):
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
    
    # Filter: hard-exclude score <= 10, pass score >= 20 to LLM
    all_results = [r for r in all_results if r["quality_score"] > 10]

    # Prefer authoritative sources (score >= 80 = Statistical DB / Gov / Edu / Trusted Org / Major News)
    preferred = [r for r in all_results if r["quality_score"] >= 80]
    fallback  = [r for r in all_results if r["quality_score"] < 80]

    if len(preferred) >= num:
        results = preferred[:num]
    elif preferred:
        results = preferred + fallback[: num - len(preferred)]
    else:
        results = all_results[:num]

    return results
