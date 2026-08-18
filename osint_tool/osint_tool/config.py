"""
Central configuration for the OSINT tool.

ETHICS / LEGAL NOTE
--------------------
This tool only ever:
  - Queries public search engines
  - Checks whether a PUBLIC profile page exists on a platform (HTTP GET,
    same as visiting the page in a browser)
  - Calls official public APIs (e.g. GitHub's public search API)

It never:
  - Logs into anything
  - Scrapes content that requires authentication
  - Bypasses rate limits, CAPTCHAs, or ToS protections
  - Aggregates private/leaked data (breach dumps, etc.)

Use it only on people who have consented, or for research on yourself /
public figures where you have a legitimate reason. Respect local law
(GDPR etc. if you're in the EU) and each platform's Terms of Service.
Add delays / respect robots.txt if you scale this up.
"""

import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

USER_AGENT = "Mozilla/5.0 (compatible; PublicOSINTResearchBot/1.0)"

# How many concurrent HTTP requests when checking usernames across sites
MAX_CONCURRENCY = 15

# Timeout (seconds) per HTTP request
REQUEST_TIMEOUT = 8

# How many search-engine results to pull per query
SEARCH_RESULTS_PER_QUERY = 8
