"""
Adapters: raw module output -> list[Finding].
Keep these here (not inside each module) so the modules stay decoupled
from the correlation layer -- they don't need to know it exists.
"""

import re
from urllib.parse import urlsplit

from .models import Finding, FindingType

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def normalize_username_check(results):
    """results = output of username_check.check_username()"""
    findings = []
    for r in results:
        if not r.get("exists"):
            continue
        findings.append(Finding(
            type=FindingType.URL,
            value=r["url"].rstrip("/").lower(),
            source_module="username_check",
            source_detail=r["site"],
            confidence=0.6,
            raw=r,
        ))
    return findings


def normalize_search_engines(aggregated_hits):
    """aggregated_hits = output of search_engines.aggregate_hits()"""
    findings = []
    for url, data in aggregated_hits.items():
        # More queries surfacing the same URL = higher confidence, capped at 0.9
        confidence = min(0.3 + 0.15 * data["count"], 0.9)
        findings.append(Finding(
            type=FindingType.URL,
            value=url.rstrip("/").lower(),
            source_module="search_engines",
            source_detail=f"{data['count']} quer{'y' if data['count'] == 1 else 'ies'}",
            confidence=confidence,
            raw=data,
        ))

        # Pull any emails visible in the snippet text -- cheap win, often missed
        for email in _EMAIL_RE.findall(data.get("body", "")):
            findings.append(Finding(
                type=FindingType.EMAIL,
                value=email.lower(),
                source_module="search_engines",
                source_detail=url,
                confidence=0.4,
                raw=data,
            ))
    return findings


def normalize_github_lookup(github_results):
    """
    github_results = list of dicts from github_lookup.search_github_users(),
    expected to carry at least: login, html_url, and ideally bio/location/email
    if you're already hitting the user-detail endpoint. Adjust field names
    to match whatever github_lookup.py actually returns.
    """
    findings = []
    for u in github_results:
        login = u.get("login")
        if login:
            findings.append(Finding(
                type=FindingType.USERNAME,
                value=login.lower(),
                source_module="github_lookup",
                source_detail="github",
                confidence=0.7,
                raw=u,
            ))
        profile_url = u.get("html_url") or u.get("profile_url")
        if profile_url:
            findings.append(Finding(
                type=FindingType.URL,
                value=profile_url.rstrip("/").lower(),
                source_module="github_lookup",
                source_detail="github",
                confidence=0.7,
                raw=u,
            ))
        if u.get("location"):
            findings.append(Finding(
                type=FindingType.LOCATION,
                value=u["location"].strip().lower(),
                source_module="github_lookup",
                source_detail="github bio",
                confidence=0.5,
                raw=u,
            ))
        if u.get("email"):
            findings.append(Finding(
                type=FindingType.EMAIL,
                value=u["email"].lower(),
                source_module="github_lookup",
                source_detail="github public email",
                confidence=0.8,
                raw=u,
            ))
        if u.get("company"):
            findings.append(Finding(
                type=FindingType.EMPLOYER,
                value=u["company"].strip().lstrip("@").lower(),
                source_module="github_lookup",
                source_detail="github bio",
                confidence=0.5,
                raw=u,
            ))
    return findings


def username_from_url(url):
    """Best-effort extraction of a handle from a profile URL's last path segment."""
    path = urlsplit(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[-1].lower()