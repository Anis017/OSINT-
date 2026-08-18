"""
Public web search via DuckDuckGo (no API key required, no login).
"""

import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from ddgs import DDGS

from config import SEARCH_RESULTS_PER_QUERY

# Optional config knobs -- fall back to sane defaults if not present in config.py yet.
try:
    import config as _config
except ImportError:
    _config = None

if _config is not None:
    SEARCH_MAX_WORKERS = getattr(_config, "SEARCH_MAX_WORKERS", 5)
    SEARCH_MAX_RETRIES = getattr(_config, "SEARCH_MAX_RETRIES", 2)
    SEARCH_RETRY_BACKOFF = getattr(_config, "SEARCH_RETRY_BACKOFF", 2)
else:
    SEARCH_MAX_WORKERS = 5
    SEARCH_MAX_RETRIES = 2
    SEARCH_RETRY_BACKOFF = 2  # seconds, multiplied by attempt number


def build_queries(full_name, extra_context=None, location=None, mode="deep"):
    """
    mode="quick" -> core identity queries only (fast, cheap)
    mode="deep"  -> full query set including location-based queries
    """
    name = full_name.strip()
    ctx = f" {extra_context.strip()}" if extra_context else ""
    loc = location.strip() if location else None

    core_queries = [
        f'"{name}"{ctx}',
        f'"{name}"{ctx} linkedin',
        f'"{name}"{ctx} github',
    ]

    extended_queries = [
        f'"{name}"{ctx} twitter OR x.com',
        f'"{name}"{ctx} instagram',
        f'"{name}"{ctx} facebook',
        f'"{name}"{ctx} resume OR cv',
        f'"{name}"{ctx} news',
        f'"{name}"{ctx} interview OR podcast',
    ]

    location_queries = []
    if loc:
        location_queries = [
            f'"{name}" "{loc}"{ctx}',
            f'"{name}" "{loc}" linkedin',
            f'"{name}" "{loc}" facebook',
            f'"{name}" "{loc}" news OR obituary OR wedding',
            f'"{name}" "{loc}" phone OR address',
        ]

    if mode == "quick":
        return core_queries

    return core_queries + extended_queries + location_queries


def _fetch_one(query, max_results, retries=SEARCH_MAX_RETRIES, backoff=SEARCH_RETRY_BACKOFF):
    """Run a single DDG query with its own client and retry-with-backoff."""
    last_error = None
    for attempt in range(retries + 1):
        try:
            with DDGS() as ddgs:
                hits = list(ddgs.text(query, max_results=max_results))
            return query, hits
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    return query, [{"title": "ERROR", "href": "", "body": str(last_error)}]


def run_search(full_name, extra_context=None, location=None, mode="deep", max_workers=SEARCH_MAX_WORKERS):
    """
    Runs all queries concurrently via a thread pool (DDGS calls are blocking I/O,
    so threads -- not asyncio -- are the right tool here).
    Returns dict: {query_string: [hit, ...]}
    """
    queries = build_queries(full_name, extra_context, location, mode=mode)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_fetch_one, q, SEARCH_RESULTS_PER_QUERY) for q in queries
        ]
        for future in as_completed(futures):
            query, hits = future.result()
            results[query] = hits

    return results


def aggregate_hits(results):
    """
    Flattens per-query results into unique URLs, counting how many distinct
    queries surfaced each one. A higher count is a decent free confidence
    signal -- e.g. a LinkedIn URL showing up under both the base query and
    the "linkedin" query is more likely a real match than one that only
    shows up once under a broad query.

    Returns dict: {url: {"count": int, "queries": [...], "title": str, "body": str}}
    """
    agg = defaultdict(lambda: {"count": 0, "queries": [], "title": "", "body": ""})

    for query, hits in results.items():
        for hit in hits:
            url = hit.get("href", "")
            if not url:
                continue
            entry = agg[url]
            entry["count"] += 1
            entry["queries"].append(query)
            entry["title"] = entry["title"] or hit.get("title", "")
            entry["body"] = entry["body"] or hit.get("body", "")

    # Sort by confidence (count) descending for convenience.
    return dict(sorted(agg.items(), key=lambda kv: kv[1]["count"], reverse=True))