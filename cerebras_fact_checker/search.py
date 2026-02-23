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
        # Historical archives & encyclopedias
        "britannica.com", "jstor.org", "gallica.bnf.fr", "persee.fr", "cairn.info", "halshs.archives-ouvertes.fr",
        "archives-nationales.culture.gouv.fr", "europeana.eu", "deutsche-digitale-bibliothek.de", "dialnet.unirioja.es", "scielo.org",
        "history.com", "bl.uk",
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
    "history":     ["britannica.com", "jstor.org", "gallica.bnf.fr",
                    "archives-nationales.culture.gouv.fr", "history.com",
                    "bbc.co.uk/history", "bl.uk", "europeana.eu"],
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
    # Historical claims: primary archival & academic databases
    "history": [
        "https://gallica.bnf.fr/accueil/?lang=EN",               # BnF Gallica — French national digital library
        "https://www.insee.fr/en/statistiques",                  # INSEE — French official statistics (historical series)
        "https://www.jstor.org",                                 # JSTOR peer-reviewed journals
        "https://link.springer.com",                             # Springer academic publisher
        "https://www.tandfonline.com",                           # Taylor & Francis economic history journals
        "https://www.persee.fr",                                 # Persée — French scholarly journals (open access)
        "https://halshs.archives-ouvertes.fr",                   # HAL SHS — French open-access social science archive
        "https://www.cairn.info",                                # Cairn — French academic journal platform
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
    # Historical / regional industry claims (must come after trade so history overrides when both match)
    ("history",     [r"\b(19|20)th.{0,5}century\b", r"\bhistor(?:y|ical|ically)\b",
                     r"\bindustrial.{0,20}(?:decline|revolution|heritage)\b",
                     r"\b(?:decline|deindustri(?:ali[sz]ation)?)\b",
                     r"\btextile\b", r"\bmanufactur\b", r"\bmill\b", r"\bfabric\b",
                     r"\b(?:ancien|heritage|archiv|medieval|renaissance)\b"]),
]

# ── Country / region → (language_code, language_name) ─────────────────────────
_REGION_LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    # ── French ──
    "south korea":  ("ko", "Korean"),
    "north korea":  ("ko", "Korean"),
    "france":       ("fr", "French"),
    "french":       ("fr", "French"),
    "paris":        ("fr", "French"),
    "vosges":       ("fr", "French"),
    "alsace":       ("fr", "French"),
    "normandy":     ("fr", "French"),
    "bordeaux":     ("fr", "French"),
    "lyon":         ("fr", "French"),
    "marseille":    ("fr", "French"),
    "cevennes":     ("fr", "French"),
    "brittany":     ("fr", "French"),
    "provence":     ("fr", "French"),
    "belgium":      ("fr", "French"),
    # ── German ──
    "germany":      ("de", "German"),
    "german":       ("de", "German"),
    "berlin":       ("de", "German"),
    "bavaria":      ("de", "German"),
    "austria":      ("de", "German"),
    "switzerland":  ("de", "German"),
    "munich":       ("de", "German"),
    "hamburg":      ("de", "German"),
    "cologne":      ("de", "German"),
    "frankfurt":    ("de", "German"),
    # ── Spanish / Latin America ──
    "spain":        ("es", "Spanish"),
    "spanish":      ("es", "Spanish"),
    "madrid":       ("es", "Spanish"),
    "barcelona":    ("es", "Spanish"),
    "mexico":       ("es", "Spanish"),
    "argentina":    ("es", "Spanish"),
    "colombia":     ("es", "Spanish"),
    "chile":        ("es", "Spanish"),
    "peru":         ("es", "Spanish"),
    "venezuela":    ("es", "Spanish"),
    "cuba":         ("es", "Spanish"),
    "bogota":       ("es", "Spanish"),
    "lima":         ("es", "Spanish"),
    "buenos aires": ("es", "Spanish"),
    # ── Italian ──
    "italy":        ("it", "Italian"),
    "italian":      ("it", "Italian"),
    "rome":         ("it", "Italian"),
    "milan":        ("it", "Italian"),
    "venice":       ("it", "Italian"),
    "florence":     ("it", "Italian"),
    "naples":       ("it", "Italian"),
    "sicily":       ("it", "Italian"),
    # ── Japanese ──
    "japan":        ("ja", "Japanese"),
    "japanese":     ("ja", "Japanese"),
    "tokyo":        ("ja", "Japanese"),
    "osaka":        ("ja", "Japanese"),
    "kyoto":        ("ja", "Japanese"),
    # ── Chinese ──
    "china":        ("zh", "Chinese"),
    "chinese":      ("zh", "Chinese"),
    "beijing":      ("zh", "Chinese"),
    "shanghai":     ("zh", "Chinese"),
    "taiwan":       ("zh", "Chinese"),
    "hong kong":    ("zh", "Chinese"),
    # ── Russian / Slavic ──
    "russia":       ("ru", "Russian"),
    "russian":      ("ru", "Russian"),
    "moscow":       ("ru", "Russian"),
    "soviet":       ("ru", "Russian"),
    "ussr":         ("ru", "Russian"),
    "ukraine":      ("uk", "Ukrainian"),
    "poland":       ("pl", "Polish"),
    "warsaw":       ("pl", "Polish"),
    # ── Portuguese ──
    "portugal":     ("pt", "Portuguese"),
    "brazil":       ("pt", "Portuguese"),
    "sao paulo":    ("pt", "Portuguese"),
    "rio de janeiro": ("pt", "Portuguese"),
    # ── Dutch ──
    "netherlands":  ("nl", "Dutch"),
    "dutch":        ("nl", "Dutch"),
    "amsterdam":    ("nl", "Dutch"),
    "holland":      ("nl", "Dutch"),
    # ── Nordic ──
    "sweden":       ("sv", "Swedish"),
    "stockholm":    ("sv", "Swedish"),
    "norway":       ("no", "Norwegian"),
    "oslo":         ("no", "Norwegian"),
    "denmark":      ("da", "Danish"),
    "copenhagen":   ("da", "Danish"),
    "finland":      ("fi", "Finnish"),
    "helsinki":     ("fi", "Finnish"),
    # ── Greek / Turkish ──
    "greece":       ("el", "Greek"),
    "athens":       ("el", "Greek"),
    "turkey":       ("tr", "Turkish"),
    "istanbul":     ("tr", "Turkish"),
    "ankara":       ("tr", "Turkish"),
    # ── Korean ──
    "korea":        ("ko", "Korean"),
    "seoul":        ("ko", "Korean"),
    # ── Arabic ──
    "arabic":       ("ar", "Arabic"),
    "saudi":        ("ar", "Arabic"),
    "saudi arabia": ("ar", "Arabic"),
    "egypt":        ("ar", "Arabic"),
    "cairo":        ("ar", "Arabic"),
    "iraq":         ("ar", "Arabic"),
    "baghdad":      ("ar", "Arabic"),
    "syria":        ("ar", "Arabic"),
    "jordan":       ("ar", "Arabic"),
    "morocco":      ("ar", "Arabic"),
    "algeria":      ("ar", "Arabic"),
    "tunisia":      ("ar", "Arabic"),
    "lebanon":      ("ar", "Arabic"),
    # ── English-speaking (en) — South Asia ──
    "india":        ("en", "English"),
    "indian":       ("en", "English"),
    "delhi":        ("en", "English"),
    "mumbai":       ("en", "English"),
    "calcutta":     ("en", "English"),
    "kolkata":      ("en", "English"),
    "bangalore":    ("en", "English"),
    "pakistan":     ("en", "English"),
    "bangladesh":   ("en", "English"),
    "sri lanka":    ("en", "English"),
    "nepal":        ("en", "English"),
    # ── English-speaking (en) — UK & Ireland ──
    "uk":           ("en", "English"),
    "united kingdom": ("en", "English"),
    "britain":      ("en", "English"),
    "british":      ("en", "English"),
    "england":      ("en", "English"),
    "london":       ("en", "English"),
    "scotland":     ("en", "English"),
    "wales":        ("en", "English"),
    "ireland":      ("en", "English"),
    "manchester":   ("en", "English"),
    "birmingham":   ("en", "English"),
    # ── English-speaking (en) — Oceania ──
    "australia":    ("en", "English"),
    "sydney":       ("en", "English"),
    "melbourne":    ("en", "English"),
    "new zealand":  ("en", "English"),
    # ── English-speaking (en) — North America ──
    "canada":       ("en", "English"),
    "toronto":      ("en", "English"),
    "vancouver":    ("en", "English"),
    # ── English-speaking (en) — Africa ──
    "nigeria":      ("en", "English"),
    "lagos":        ("en", "English"),
    "south africa": ("en", "English"),
    "johannesburg": ("en", "English"),
    "kenya":        ("en", "English"),
    "nairobi":      ("en", "English"),
    "ghana":        ("en", "English"),
    "ethiopia":     ("en", "English"),
    "tanzania":     ("en", "English"),
    "uganda":       ("en", "English"),
    "zimbabwe":     ("en", "English"),
    # ── English-speaking (en) — Southeast Asia ──
    "indonesia":    ("en", "English"),
    "jakarta":      ("en", "English"),
    "malaysia":     ("en", "English"),
    "kuala lumpur": ("en", "English"),
    "singapore":    ("en", "English"),
    "thailand":     ("en", "English"),
    "bangkok":      ("en", "English"),
    "philippines":  ("en", "English"),
    "manila":       ("en", "English"),
    "vietnam":      ("en", "English"),
    "myanmar":      ("en", "English"),
    "cambodia":     ("en", "English"),
    # ── English-speaking (en) — Middle East ──
    "iran":         ("en", "English"),
    "tehran":       ("en", "English"),
    "israel":       ("en", "English"),
    "tel aviv":     ("en", "English"),
    "uae":          ("en", "English"),
    "dubai":        ("en", "English"),
    "qatar":        ("en", "English"),
    "kuwait":       ("en", "English"),
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

# ── Indicators that a claim is about historical/regional context ──────────────
# When present, regional archival sources are more relevant than WTO/IMF etc.
_HISTORICAL_RE = re.compile(
    r'\b(19|20)th.{0,5}century\b'
    r'|\bhistor(?:y|ical|ically)\b'
    r'|\b(?:ancient|medieval|renaissance|colonial|pre.?war|post.?war)\b'
    r'|\bindustrial.{0,20}(?:decline|revolution)\b'
    r'|\b(?:deindustriali[sz]ation|decline).{0,30}(?:industr|manufactur|textile|mill)\b'
    r'|\btextile.{0,30}(?:decline|industr|manufactur)\b',
    re.IGNORECASE,
)

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
    # English-speaking regions: UK/India/Australia/Canada/Africa/SE Asia/Middle East
    "en": ["bl.uk", "ons.gov.uk", "loc.gov", "nla.gov.au", "jstor.org"],
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

    # International-authority topics: locale adds noise — BUT not for historical claims.
    # A claim about 19th-century textile decline in France has no WTO stats to cite;
    # French national archives and encyclopedias are the authoritative sources.
    topics = detect_claim_topics(claim)
    intl_topics = [t for t in topics if t in _INTERNATIONAL_TOPICS]
    if intl_topics:
        # Override: historical/regional industry claims need locale even if "trade" matched
        if "history" in topics or _HISTORICAL_RE.search(claim):
            return True, (
                f"historical/regional claim ({intl_topics} also detected) — "
                f"using {lang_name} archival sources instead of international stat databases"
            )
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
    is_historical = "history" in topics or bool(_HISTORICAL_RE.search(claim))

    seen: set[str] = set()
    domains: list[str] = []
    for topic in topics:
        # For historical claims, skip international stats domains (WTO, IMF, etc.)
        # — they have no data about 19th/early-20th century regional industry.
        # History + locale domains are added below and will take priority instead.
        if is_historical and topic in _INTERNATIONAL_TOPICS:
            continue
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

    # ── Historical claim enhancements (run before numeric/trade routing) ───────
    _hist_topics = detect_claim_topics(claim)
    _is_historical = "history" in _hist_topics or bool(_HISTORICAL_RE.search(claim))
    if _is_historical:
        _region = detect_claim_region(claim)
        _lang_hint = _region[1] if _region else ""
        _lang_code = _region[0] if _region else ""
        if _lang_hint:
            queries.append(f"{claim} {_lang_hint} history")
        queries.append(f"{claim} historical encyclopedia")
        queries.append(f"history {claim} archives")
        # ── Targeted archival queries per region ──────────────────────────────
        # site: operators funnel the search to the most authoritative national
        # archive / open-access scholarly platform for each language region.
        # Strip stop-words from the claim to form a tight keyword core.
        _core = re.sub(
            r'\b(at the|of the|due to|the|and|in|from|a|an'
            r'|beginning|increasing|import|cheaper|during|between|after|before)\b',
            '', claim, flags=re.IGNORECASE
        ).strip()
        _core = re.sub(r'\s{2,}', ' ', _core).strip()

        # Per-language: (primary open-access archive, secondary scholarly platform)
        _ARCHIVAL_SITES: dict[str, list[str]] = {
            # France — richest open-access ecosystem
            "fr": [
                "gallica.bnf.fr",           # BnF national digital library
                "persee.fr",                # French open-access scholarly journals
                "cairn.info",               # French academic platform
                "halshs.archives-ouvertes.fr",  # French social science open archive
                "jstor.org",
            ],
            # Germany
            "de": [
                "deutsche-digitale-bibliothek.de",  # German Digital Library
                "bundesarchiv.de",          # Federal Archives
                "jstor.org",
                "springer.com",
            ],
            # Spain / Latin America
            "es": [
                "dialnet.unirioja.es",      # Spanish open-access portal
                "redalyc.org",              # Latin American open-access journals
                "jstor.org",
            ],
            # Italy
            "it": [
                "treccani.it",              # Treccani encyclopedia & journals
                "jstor.org",
                "springer.com",
            ],
            # Japan
            "ja": [
                "ndl.go.jp",               # National Diet Library digital collections
                "jstor.org",
                "springer.com",
            ],
            # China
            "zh": [
                "jstor.org",
                "springer.com",
            ],
            # Russia
            "ru": [
                "jstor.org",
                "springer.com",
            ],
            # Portugal / Brazil
            "pt": [
                "scielo.org",              # SciELO open-access Latin American journals
                "jstor.org",
            ],
            # Netherlands
            "nl": [
                "jstor.org",
                "springer.com",
            ],
            # Nordic (Swedish, Norwegian, Danish, Finnish)
            "sv": ["jstor.org", "springer.com"],
            "no": ["jstor.org", "springer.com"],
            "da": ["jstor.org", "springer.com"],
            "fi": ["jstor.org", "springer.com"],
            # Polish / Ukrainian
            "pl": ["jstor.org", "springer.com"],
            "uk": ["jstor.org", "springer.com"],
            # Greek / Turkish / Korean / Arabic
            "el": ["jstor.org", "springer.com"],
            "tr": ["jstor.org", "springer.com"],
            "ko": ["jstor.org", "springer.com"],
            "ar": ["jstor.org", "springer.com"],
            # English-speaking regions (India, UK, Australia, Canada, Africa, SE Asia, Middle East)
            # Rich English-language archival ecosystem.
            "en": [
                "bl.uk",                   # British Library digital collections
                "hathitrust.org",           # HathiTrust digital library (academic)
                "archive.org",             # Internet Archive (millions of historical texts)
                "jstor.org",
                "springer.com",
            ],
            # ── Universal fallback ── unknown region / unlisted language ─────────
            # _lang_code = "" when detect_claim_region() returns None.
            # Always guaranteed: JSTOR + Springer cover most world history topics.
            "": ["jstor.org", "springer.com"],
        }

        _archival_sites = _ARCHIVAL_SITES.get(_lang_code, ["jstor.org", "springer.com"])
        for _site in _archival_sites[:5]:   # cap at 5 site: queries to stay within query budget
            queries.append(f"site:{_site} {_core}")

    # ── Numeric / statistical claim enhancements ───────────────────────────────
    if is_numeric_claim(claim) and not _is_historical:
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

    return queries[:15]


def _recency_bonus(result: dict[str, Any], is_historical: bool = False) -> int:
    """Return a recency bonus (+25 to -15) based on the result's year.

    For historical claims (is_historical=True), recency bonuses are suppressed:
    a 1920 academic paper about the 1900s is MORE relevant than a 2024 blog
    post, so we apply a flat 0 bonus rather than penalising old documents.

    Tries publish_date first, then falls back to a 4-digit year in the URL.
    Returns 0 if no year can be determined.
    """
    # Historical claims: don't penalise old academic sources — they ARE the evidence.
    if is_historical:
        return 0

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
    
    # Use the top generated queries for the objective
    queries_list = "\n        - ".join(queries[:3])
    import textwrap
    objective = textwrap.dedent(
        f"""
        Find high-quality, relevant sources that address these topics/questions:
        - {queries_list}
        
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
    # Detect whether this is a historical claim so recency scoring is suppressed.
    _is_hist = any(
        kw in " ".join(queries).lower()
        for kw in ["century", "histor", "archiv", "decline", "textile", "industrial", "siècle", "déclin"]
    )
    # Compute composite score = quality (authority) + recency bonus
    # Historical claims: recency bonus is flat 0 so old academic papers aren't penalised.
    for res in all_results:
        res["composite_score"] = res["quality_score"] + _recency_bonus(res, is_historical=_is_hist)

    # Sort by composite score descending (recency-weighted authority)
    all_results.sort(key=lambda x: x["composite_score"], reverse=True)

    # Filter: hard-exclude composite <= 10
    all_results = [r for r in all_results if r["composite_score"] > 10]

    # For historical claims, relax the quality gate — academic PDFs from JSTOR/
    # Gallica/Persée often score 20 ("Other") but are the most relevant sources.
    quality_threshold = 60 if _is_hist else 80
    preferred = [r for r in all_results if r["quality_score"] >= quality_threshold]
    fallback  = [r for r in all_results if r["quality_score"] < quality_threshold]

    if len(preferred) >= num:
        results = preferred[:num]
    elif preferred:
        results = preferred + fallback[: num - len(preferred)]
    else:
        results = all_results[:num]

    # ── Recency floor: inject freshest source only for non-historical claims ──
    # For historical claims the "freshest" source is often a blog post or news
    # aggregator — exactly the kind of low-quality source we want to avoid.
    if results and not _is_hist:
        freshest = max(all_results, key=lambda x: _recency_bonus(x), default=None)
        if freshest and freshest["url"] not in {r["url"] for r in results}:
            # Replace the last (lowest-composite) result with the freshest one
            results[-1] = freshest
            print(f"[Recency floor] Injected freshest source: {freshest['url']}")

    return results
