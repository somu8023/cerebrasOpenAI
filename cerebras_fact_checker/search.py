from __future__ import annotations

import datetime
import re
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


# ── Topic → authoritative primary-source domains ──────────────────────────────
TOPIC_DOMAIN_WHITELIST: dict[str, list[str]] = {
    "defence":     ["nato.int", "sipri.org", "defense.gov", "mod.uk", "iiss.org"],
    "economics":   ["imf.org", "worldbank.org", "oecd.org", "bis.org", "federalreserve.gov", "ecb.europa.eu"],
    "health":      ["who.int", "cdc.gov", "nih.gov", "ecdc.europa.eu"],
    "environment": ["unep.org", "ipcc.ch", "noaa.gov", "epa.gov"],
    "trade":       ["wto.org", "unctad.org"],
    "energy":      ["iea.org", "eia.gov", "irena.org"],
    "population":  ["un.org", "census.gov", "stats.oecd.org"],
    "education":   ["unesco.org", "oecd.org", "nces.ed.gov"],
    "human_rights": ["hrw.org", "amnesty.org", "ohchr.org"],
    "science":     ["nature.com", "pubmed.ncbi.nlm.nih.gov", "nasa.gov"],
}

# ── Pinned HTML stat pages per topic ──────────────────────────────────────────
# These are exact URLs for HTML data pages (not PDFs) whose text content the
# search API can extract directly, capturing tables and per-country breakdowns.
# Used in place of generic site: queries to avoid landing on press releases / PDFs.
TOPIC_PINNED_URLS: dict[str, list[str]] = {
    "defence": [
        "https://www.nato.int/cps/en/natohq/topics_49198.htm",   # NATO defence expenditure stats HTML
        "https://www.sipri.org/databases/milex",                 # SIPRI military expenditure DB
    ],
    "economics": [
        "https://www.imf.org/en/Publications/WEO/weo-database/2024/October",
    ],
    "health": [
        "https://www.who.int/data/gho",
    ],
    "environment": [
        "https://www.unep.org/resources/emissions-gap-report-2024",
    ],
    "energy": [
        "https://www.iea.org/data-and-statistics",
    ],
    "trade": [
        "https://stats.wto.org",
    ],
    "population": [
        "https://population.un.org/dataportal",
    ],
}

# ── Claim topic → detection patterns ──────────────────────────────────────────
_TOPIC_PATTERNS: list[tuple[str, list[str]]] = [
    ("defence",     ["nato", r"defen[cs]e", "military", r"gdp.{0,10}spend", "troop", "armed force", r"2\s*%.*gdp"]),
    ("economics",   [r"\bGDP\b", "economy", "economic", "inflation", "recession", "fiscal", r"\bdebt\b", "budget deficit"]),
    ("health",      ["vaccine", "covid", "pandemic", "mortality", "disease", "virus", "life expectancy"]),
    ("environment", ["climate", "emission", "carbon", "greenhouse", "deforestation", "sea level", "temperature rise"]),
    ("trade",       [r"\bexport\b", r"\bimport\b", "tariff", "trade war", "trade balance", "WTO"]),
    ("energy",      [r"\boil\b", r"\bgas\b", r"\bcoal\b", "nuclear", "solar", "wind power", "energy consumption", r"\bbarrel\b"]),
    ("population",  ["population", "birth rate", "fertility", "demographic", "migration"]),
    ("education",   ["literacy", r"\bschool\b", "university", "dropout", "graduation rate"]),
    ("human_rights", ["human rights", "freedom of press", "democracy index", "corruption index"]),
    ("science",     ["speed of light", "quantum", r"\bphysics\b", r"\bchemistry\b", r"\bspace\b", r"\bplanet\b"]),
]

# ── Country / region → (language_code, language_name) ─────────────────────────
_REGION_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "south korea": ("ko", "Korean"),
    "north korea": ("ko", "Korean"),
    "france":      ("fr", "French"),
    "french":      ("fr", "French"),
    "paris":       ("fr", "French"),
    "vosges":      ("fr", "French"),
    "alsace":      ("fr", "French"),
    "normandy":    ("fr", "French"),
    "germany":     ("de", "German"),
    "german":      ("de", "German"),
    "berlin":      ("de", "German"),
    "bavaria":     ("de", "German"),
    "austria":     ("de", "German"),
    "switzerland": ("de", "German"),
    "spain":       ("es", "Spanish"),
    "spanish":     ("es", "Spanish"),
    "madrid":      ("es", "Spanish"),
    "mexico":      ("es", "Spanish"),
    "argentina":   ("es", "Spanish"),
    "italy":       ("it", "Italian"),
    "italian":     ("it", "Italian"),
    "rome":        ("it", "Italian"),
    "japan":       ("ja", "Japanese"),
    "japanese":    ("ja", "Japanese"),
    "tokyo":       ("ja", "Japanese"),
    "china":       ("zh", "Chinese"),
    "chinese":     ("zh", "Chinese"),
    "beijing":     ("zh", "Chinese"),
    "russia":      ("ru", "Russian"),
    "russian":     ("ru", "Russian"),
    "moscow":      ("ru", "Russian"),
    "portugal":    ("pt", "Portuguese"),
    "brazil":      ("pt", "Portuguese"),
    "netherlands": ("nl", "Dutch"),
    "dutch":       ("nl", "Dutch"),
    "poland":      ("pl", "Polish"),
    "ukraine":     ("uk", "Ukrainian"),
    "sweden":      ("sv", "Swedish"),
    "norway":      ("no", "Norwegian"),
    "denmark":     ("da", "Danish"),
    "finland":     ("fi", "Finnish"),
    "greece":      ("el", "Greek"),
    "turkey":      ("tr", "Turkish"),
    "korea":       ("ko", "Korean"),
    "arabic":      ("ar", "Arabic"),
    "saudi":       ("ar", "Arabic"),
    "egypt":       ("ar", "Arabic"),
}

# ── Numeric / statistical indicator regex ──────────────────────────────────────
_NUMERIC_RE = re.compile(
    r'\b(\d+\.?\d*\s*%|percent|GDP|billion|trillion|million|'
    r'budget|spending|expenditure|rank(?:ed)?\s+\d+|per\s+capita|'
    r'rate|ratio|index|average|median|contribut)\b',
    re.IGNORECASE,
)

# ── Topics where international official sources beat regional ones ───────────────
# For these, locale search adds noise, not signal.
_INTERNATIONAL_TOPICS: set[str] = {
    "defence", "economics", "health", "environment",
    "trade", "energy", "population",
}

# ── Regional authoritative source domains per language ───────────────────────────
# These are real national archives, stat agencies, and encyclopedias.
_REGIONAL_DOMAINS: dict[str, list[str]] = {
    "fr": ["insee.fr", "ina.fr", "legifrance.gouv.fr", "archives-nationales.culture.gouv.fr",
           "larousse.fr", "gallica.bnf.fr"],
    "de": ["bundesarchiv.de", "destatis.de", "bpb.de", "dw.com", "spiegel.de"],
    "es": ["ine.es", "boe.es", "cervantes.es", "elmundo.es", "elpais.com"],
    "it": ["istat.it", "quirinale.it", "archiviodistatoit", "corriere.it", "treccani.it"],
    "ja": ["stat.go.jp", "ndl.go.jp", "nhk.or.jp", "kantei.go.jp"],
    "zh": ["stats.gov.cn", "xinhuanet.com", "people.com.cn"],
    "ru": ["gks.ru", "kremlin.ru", "rbc.ru", "tass.ru"],
    "pt": ["ibge.gov.br", "ine.pt", "pordata.pt"],
    "nl": ["cbs.nl", "rijksoverheid.nl", "nrc.nl"],
    "pl": ["stat.gov.pl", "gov.pl"],
    "sv": ["scb.se", "riksdagen.se"],
    "no": ["ssb.no", "regjeringen.no"],
    "da": ["dst.dk", "stm.dk"],
    "fi": ["stat.fi", "finlex.fi"],
    "el": ["statistics.gr", "hellenicparliament.gr"],
    "tr": ["tuik.gov.tr", "tbmm.gov.tr"],
    "ko": ["kostat.go.kr", "korea.kr"],
    "ar": ["stats.gov.sa", "capmas.gov.eg"],
}


def detect_claim_topics(claim: str) -> list[str]:
    """Return matched topic keys for a claim (ordered, deduplicated)."""
    matched: list[str] = []
    for topic, patterns in _TOPIC_PATTERNS:
        for pat in patterns:
            if re.search(pat, claim, re.IGNORECASE):
                matched.append(topic)
                break
    return matched


def detect_claim_region(claim: str) -> tuple[str, str] | None:
    """Detect the primary region/country mentioned in a claim.

    Returns (language_code, language_name) or None.
    Longest key matched first so "south korea" beats "korea".
    """
    claim_lower = claim.lower()
    for region, lang_pair in sorted(_REGION_LANGUAGE_MAP.items(), key=lambda x: -len(x[0])):
        if region in claim_lower:
            return lang_pair
    return None


def is_numeric_claim(claim: str) -> bool:
    """Return True if the claim contains numeric / statistical assertions."""
    return bool(_NUMERIC_RE.search(claim))


def should_use_locale_search(claim: str) -> tuple[bool, str]:
    """Decide whether regional-language sources genuinely help for this claim.

    Returns (use_locale: bool, reason: str).

    Rules:
    - If no region is detected → skip (no locale to use)
    - If claim is numeric/statistical → skip (numbers live in official intl DBs)
    - If claim topics overlap with international-authority topics → skip
      (NATO, IMF, WHO etc. publish authoritatively in English)
    - Otherwise (regional history, culture, geography, politics, industry) → enable
    """
    region = detect_claim_region(claim)
    if region is None:
        return False, "no region detected"

    lang_code, lang_name = region

    # Numeric claims: official international datasets are the ground truth
    if is_numeric_claim(claim):
        return False, f"numeric/statistical claim — official intl sources preferred over {lang_name}"

    # International-authority topics: locale adds noise
    topics = detect_claim_topics(claim)
    intl_topics = [t for t in topics if t in _INTERNATIONAL_TOPICS]
    if intl_topics:
        return False, (
            f"international topic(s) {intl_topics} detected — "
            f"official domain sources preferred over {lang_name} regional sources"
        )

    # Regional history / culture / geography / local facts → locale helps
    return True, f"regional claim about {region[1]}-speaking area — adding {lang_name} authoritative sources"


def get_topic_domains(claim: str) -> list[str]:
    """Return a deduplicated list of authoritative domains for the claim's topics.

    Also injects regional authoritative domains when the smart locale router
    decides they are genuinely useful (non-numeric, non-international claim).
    """
    topics = detect_claim_topics(claim)
    seen: set[str] = set()
    domains: list[str] = []
    for topic in topics:
        for d in TOPIC_DOMAIN_WHITELIST.get(topic, []):
            if d not in seen:
                seen.add(d)
                domains.append(d)

    # Inject regional domains only when locale search is actually useful
    use_locale, _ = should_use_locale_search(claim)
    if use_locale:
        region = detect_claim_region(claim)
        if region:
            lang_code = region[0]
            for d in _REGIONAL_DOMAINS.get(lang_code, []):
                if d not in seen:
                    seen.add(d)
                    domains.append(d)

    return domains


def generate_search_variations(claim: str) -> list[str]:
    """Generate diverse search query variations for a claim.

    Auto-routing:
    - Numeric/stat claims get current-year + official-domain targeted queries.
    - Regional claims that benefit from locale get a targeted regional query.
      (International/numeric claims skip locale automatically.)
    """
    _now = datetime.datetime.now()
    current_year = str(_now.year)
    # Annual reports are published mid-year; querying the current year before June
    # returns non-existent or stub pages — use the previous year's report instead.
    report_year = str(_now.year - 1) if _now.month < 6 else current_year
    has_year = bool(re.search(r'\b(19|20)\d{2}\b', claim))

    queries: list[str] = [
        claim,
        f"verify: {claim}",
        f"fact check: {claim}",
    ]

    # Entity location shortcut
    if " is in " in claim.lower():
        parts = claim.lower().split(" is in ", 1)
        entity, location = parts[0].strip(), parts[1].strip()
        queries.append(f"where is {entity}")
        queries.append(f"{entity} location")

    # ── Numeric / statistical claim enhancements ───────────────────────────────
    if is_numeric_claim(claim):
        if not has_year:
            queries.append(f"{claim} {report_year}")
        topics = detect_claim_topics(claim)
        # Use targeted queries that match actual stat-page content, not press releases
        official_hints: dict[str, str] = {
            "defence":     f"NATO members defence spending percent of GDP {report_year} who met 2 percent target list",
            "economics":   f"IMF world economic outlook {report_year} GDP data by country",
            "health":      f"WHO health statistics {report_year} country data",
            "environment": f"UNEP emissions {report_year} country figures GHG",
            "energy":      f"IEA energy statistics {report_year} country consumption",
            "trade":       f"WTO trade statistics {report_year} country merchandise",
            "population":  f"UN population {report_year} country estimates table",
        }
        for t in topics:
            if t in official_hints and len(queries) < 8:
                queries.append(official_hints[t])
        # For defence claims, inject pinned HTML stat page URLs directly as queries.
        # Parallel fetches URLs passed as queries, so this bypasses PDF extraction issues.
        if "defence" in topics:
            for url in TOPIC_PINNED_URLS.get("defence", []):
                if len(queries) < 8:
                    queries.append(url)
    else:
        if not has_year:
            queries.append(f"{claim} {current_year}")

    # ── Smart locale routing ───────────────────────────────────────────────────
    use_locale, locale_reason = should_use_locale_search(claim)
    print(f"[Locale] {locale_reason}")
    if use_locale:
        region = detect_claim_region(claim)
        if region:
            lang_code, lang_name = region
            queries.append(f"{claim} {lang_name} sources")

    return queries[:8]


def _recency_bonus(result: dict[str, Any]) -> int:
    """Return a recency bonus (+25 to -15) based on the result's year.

    Tries publish_date first, then falls back to a 4-digit year in the URL.
    Returns 0 if no year can be determined.
    """
    year: int | None = None

    # 1. Try the publish_date field
    pd = result.get("publish_date")
    if pd:
        m = re.search(r"(20\d{2})", str(pd))
        if m:
            year = int(m.group(1))

    # 2. Fall back to year embedded in URL path
    if year is None:
        m = re.search(r"/(20\d{2})[/\-_]", result.get("url", ""))
        if m:
            year = int(m.group(1))

    if year is None:
        return 0

    current = datetime.datetime.now().year
    delta = current - year
    if delta <= 0:   return 35   # current year  — beats any older high-authority source
    if delta == 1:   return 30   # 1 year old     — still very fresh
    if delta == 2:   return 10   # 2 years old
    if delta == 3:   return 0    # 3 years old — neutral
    if delta <= 5:   return -5   # 4-5 years old
    return -15                   # 6+ years old


def search_web(
    parallel_client: Parallel,
    *,
    query: str | list[str],
    num: int = 5,
    mode: str = "one-shot",
    max_chars_per_result: int = 8000,
    topic_domains: list[str] | None = None,
    pinned_urls: list[str] | None = None,
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

    if topic_domains:
        domains_str = ", ".join(topic_domains[:6])
        objective += (
            f"\n\nPRIORITY SOURCES: The following authoritative domains are especially "
            f"relevant for this claim — prefer results from them when available: {domains_str}"
        )

    if pinned_urls:
        urls_str = "\n".join(f"  - {u}" for u in pinned_urls)
        objective += (
            f"\n\nCRITICAL — MUST FETCH: The following URLs contain the exact data tables "
            f"needed to answer this question. You MUST retrieve and include content from "
            f"these specific pages, not just the domain homepage:\n{urls_str}"
        )

    # Always fetch a fixed large pool so num=2 and num=6 draw from the same candidate set.
    # This prevents older sources appearing when fewer results are requested.
    fetch_count = max(num * 5, 20)

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

    # ── Fixed large pool: always fetch enough so num=3 and num=6 draw from the same set ──
    # Compute composite score = quality (authority) + recency bonus
    for res in all_results:
        res["composite_score"] = res["quality_score"] + _recency_bonus(res)

    # Sort by composite score descending (recency-weighted authority)
    all_results.sort(key=lambda x: x["composite_score"], reverse=True)

    # Filter: hard-exclude composite <= 10
    all_results = [r for r in all_results if r["composite_score"] > 10]

    # Prefer authoritative sources (quality_score >= 80); recency already baked into composite
    preferred = [r for r in all_results if r["quality_score"] >= 80]
    fallback  = [r for r in all_results if r["quality_score"] < 80]

    if len(preferred) >= num:
        results = preferred[:num]
    elif preferred:
        results = preferred + fallback[: num - len(preferred)]
    else:
        results = all_results[:num]

    # ── Recency floor: always include the freshest source in the pool ─────────
    # Guarantees that num=2 and num=6 both see the most recent evidence,
    # preventing stale training-knowledge fallback from giving wrong verdicts.
    if results:
        freshest = max(all_results, key=lambda x: _recency_bonus(x), default=None)
        if freshest and freshest["url"] not in {r["url"] for r in results}:
            # Replace the last (lowest-composite) result with the freshest one
            results[-1] = freshest
            print(f"[Recency floor] Injected freshest source: {freshest['url']}")

    return results
