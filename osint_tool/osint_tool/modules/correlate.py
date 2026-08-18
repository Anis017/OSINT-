"""
Correlation layer: takes the flat list of Finding objects from every module
and looks for agreement between them. This is what turns "5 disconnected
lists of hits" into "here's what we're actually confident is true about
this person."

Rules implemented:
1. Same URL/username surfaced by multiple independent modules -> high confidence.
2. Same username string appears across different platforms -> likely same person,
   flagged as a cross-platform handle pattern.
3. Location mentioned in one source matches a location-qualified search hit.
4. Email domain matches a claimed employer.
"""

from collections import defaultdict

from .models import Correlation, FindingType
from .normalizers import username_from_url


def _base_confidence_boost(source_count):
    # Agreement across independent modules is worth more than repeated
    # hits within a single module (which normalizers already price in).
    return {1: 0.0, 2: 0.2, 3: 0.35}.get(source_count, 0.45)


def correlate_urls(findings):
    """Same URL/value seen by more than one module -> stronger signal."""
    by_value = defaultdict(list)
    for f in findings:
        if f.type == FindingType.URL:
            by_value[f.value].append(f)

    correlations = []
    for value, group in by_value.items():
        if len(group) < 2:
            continue
        sources = {f.source_module for f in group}
        base_conf = max(f.confidence for f in group)
        boosted = min(base_conf + _base_confidence_boost(len(sources)), 0.98)
        correlations.append(Correlation(
            finding_type=FindingType.URL,
            value=value,
            supporting_findings=group,
            confidence=boosted,
            note=f"Confirmed independently by: {', '.join(sorted(sources))}",
        ))
    return correlations


def correlate_usernames(findings):
    """
    Same handle string shows up across different platforms/URLs.
    This is the classic OSINT pivot: one username -> reused everywhere.
    """
    handles = defaultdict(list)

    for f in findings:
        if f.type == FindingType.USERNAME:
            handles[f.value].append(f)
        elif f.type == FindingType.URL:
            handle = username_from_url(f.value)
            if handle:
                handles[handle].append(f)

    correlations = []
    for handle, group in handles.items():
        distinct_platforms = {f.source_detail for f in group}
        if len(distinct_platforms) < 2:
            continue
        correlations.append(Correlation(
            finding_type=FindingType.USERNAME,
            value=handle,
            supporting_findings=group,
            confidence=min(0.4 + 0.15 * len(distinct_platforms), 0.95),
            note=f"Handle reused across {len(distinct_platforms)} platforms: "
                 f"{', '.join(sorted(distinct_platforms))}",
        ))
    return correlations


def correlate_locations(findings):
    """Same location string (normalized) claimed by more than one source."""
    by_location = defaultdict(list)
    for f in findings:
        if f.type == FindingType.LOCATION:
            by_location[f.value].append(f)

    correlations = []
    for loc, group in by_location.items():
        sources = {f.source_module for f in group}
        if len(sources) < 2:
            continue
        correlations.append(Correlation(
            finding_type=FindingType.LOCATION,
            value=loc,
            supporting_findings=group,
            confidence=min(0.4 + 0.2 * len(sources), 0.9),
            note=f"Location '{loc}' corroborated by {len(sources)} independent sources",
        ))
    return correlations


def correlate_employer_email(findings):
    """Claimed employer name appears inside an email domain -- e.g.
    company='Acme Corp' + email='jdoe@acme.com'."""
    employers = [f for f in findings if f.type == FindingType.EMPLOYER]
    emails = [f for f in findings if f.type == FindingType.EMAIL]

    correlations = []
    for emp in employers:
        emp_token = emp.value.replace(" ", "").replace(",", "")[:6]
        if not emp_token:
            continue
        for email in emails:
            domain = email.value.split("@")[-1].split(".")[0]
            if emp_token[:4] and emp_token[:4] in domain:
                correlations.append(Correlation(
                    finding_type=FindingType.EMAIL,
                    value=email.value,
                    supporting_findings=[emp, email],
                    confidence=0.75,
                    note=f"Email domain matches claimed employer '{emp.value}'",
                ))
    return correlations


def run_correlation(findings):
    """Runs all correlation rules and returns a combined, confidence-sorted list."""
    all_correlations = (
        correlate_urls(findings)
        + correlate_usernames(findings)
        + correlate_locations(findings)
        + correlate_employer_email(findings)
    )
    return sorted(all_correlations, key=lambda c: c.confidence, reverse=True)