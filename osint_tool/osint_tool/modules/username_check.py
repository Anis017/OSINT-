"""
Checks whether a given username has a PUBLIC profile page on a list of
platforms. This works exactly like a human clicking each profile URL in
a browser and seeing whether it 404s -- no login, no scraping of
protected content.
"""

import asyncio
import json
import time
from urllib.parse import quote, urlsplit, urlunsplit

import aiohttp

import config as app_config
from config import DATA_DIR, MAX_CONCURRENCY, REQUEST_TIMEOUT, USER_AGENT

# Optional config knobs -- fall back to sane defaults if not present in config.py yet.
USERNAME_CHECK_MAX_RETRIES = getattr(app_config, "USERNAME_CHECK_MAX_RETRIES", 2)
USERNAME_CHECK_RETRY_BACKOFF = getattr(app_config, "USERNAME_CHECK_RETRY_BACKOFF", 1)  # seconds, multiplied by attempt number


_SITES_CACHE = None


def load_sites():
    """Cached read of sites.json -- avoids re-reading disk on every check."""
    global _SITES_CACHE
    if _SITES_CACHE is None:
        with open(DATA_DIR / "sites.json", "r", encoding="utf-8") as f:
            _SITES_CACHE = json.load(f)
    return _SITES_CACHE


def _normalize_url(url):
    """Strips query string, fragment, and trailing slash so redirect
    comparisons aren't thrown off by trivial differences."""
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc.lower(), path, "", ""))


async def _fetch(session, url, sem):
    async with sem:
        return await session.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            allow_redirects=True,
        )


async def _check_one(session, site_name, site_cfg, username, sem):
    safe_username = quote(username, safe="")
    url = site_cfg["url"].format(username=safe_username)

    last_error = None
    for attempt in range(USERNAME_CHECK_MAX_RETRIES + 1):
        try:
            async with sem:
                async with session.get(
                    url,
                    headers={"User-Agent": USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                    allow_redirects=True,
                ) as resp:
                    final_url = str(resp.url)
                    redirected_away = (
                        site_cfg.get("redirect_means_missing", False)
                        and _normalize_url(final_url) != _normalize_url(url)
                    )

                    error_type = site_cfg["error_type"]

                    if error_type == "status_code":
                        exists = (
                            resp.status != site_cfg["error_code"]
                            and resp.status < 400
                            and not redirected_away
                        )
                    elif error_type == "text_match":
                        body = await resp.text(errors="ignore")
                        exists = (
                            site_cfg["error_text"] not in body
                            and resp.status < 400
                            and not redirected_away
                        )
                    elif error_type == "text_presence":
                        body = await resp.text(errors="ignore")
                        presence_text = site_cfg["presence_text"].format(username=username)
                        exists = (
                            presence_text in body
                            and resp.status < 400
                            and not redirected_away
                        )
                    else:
                        raise ValueError(f"Unknown error_type for site {site_name!r}: {error_type!r}")

                    return {
                        "site": site_name,
                        "url": url,
                        "final_url": final_url,
                        "exists": exists,
                        "status_code": resp.status,
                        "checked_at": time.time(),
                    }
        except Exception as e:
            last_error = e
            if attempt < USERNAME_CHECK_MAX_RETRIES:
                await asyncio.sleep(USERNAME_CHECK_RETRY_BACKOFF * (attempt + 1))

    return {
        "site": site_name,
        "url": url,
        "exists": None,
        "error": str(last_error),
        "checked_at": time.time(),
    }


async def check_username_async(username):
    sites = load_sites()
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            _check_one(session, name, cfg, username, sem)
            for name, cfg in sites.items()
        ]
        return await asyncio.gather(*tasks)


def check_username(username):
    """Sync wrapper. Returns list of dicts: site, url, final_url, exists,
    status_code, checked_at (and error, if the request failed)."""
    return asyncio.run(check_username_async(username))