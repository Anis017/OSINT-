#!/usr/bin/env python3
# main.py – Advanced OSINT tool (merged with new features)

import argparse
import asyncio
import os
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table

# ---- Existing modules (your code) ----
from modules.search_engines import run_search
from modules.github_lookup import search_github_users
from modules.username_check import check_username_async
from modules.name_utils import generate_username_variants, generate_email_variants
from modules.models import Finding, FindingType
from modules.report import save_report
# -------------------------------------------------

# ---- New modules ----
from core.async_worker import run_parallel
from core.evidence import create_evidence
from core.network import get_http_session
from core.config_loader import load_config
from analytics import extract_entities, build_graph, export_graph_html, classify_threat, build_timeline
from intel import vt_lookup, shodan_lookup, abuseipdb_check, hibp_check
from storage import init_db, save_finding
from modules.report import save_advanced_report
# ---------------------------------------

console = Console()
config = load_config()


def parse_args():
    parser = argparse.ArgumentParser(description="Public-data OSINT lookup by name")
    parser.add_argument("name", help='Full name to search, e.g. "Jane Doe"')
    parser.add_argument("--context", default=None,
                        help="Extra disambiguating context (city, employer, etc.)")
    parser.add_argument("--username", default=None,
                        help="A known/suspected username to check directly")
    parser.add_argument("--location", default=None,
                        help='City/region/country to narrow results, e.g. "Bejaia, Algerie"')
    parser.add_argument("--email-domain", default=None,
                        help="Generate likely email address patterns for this domain")
    parser.add_argument("--skip-username-scan", action="store_true",
                        help="Skip the cross-platform username existence check")
    parser.add_argument("--schedule", type=int, metavar="MINUTES",
                        help="Run periodically every MINUTES (watch mode)")
    parser.add_argument("--no-enrich", action="store_true",
                        help="Skip threat intelligence enrichment (VirusTotal, Shodan, etc.)")
    parser.add_argument("--no-graph", action="store_true",
                        help="Skip building relationship graph")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip generating PDF report (only Markdown/JSON)")
    return parser.parse_args()


def convert_to_findings(name, search_results, github_users, username_results, email_domain=None):
    """
    Convert all raw results from existing modules into a list of Finding objects.
    Handles search results that may be dicts or strings.
    """
    findings = []

    # 1. Web search results – handle dicts with 'href'
    for query, results in search_results.items():
        for item in results:
            if isinstance(item, dict):
                url = item.get('href', '')
                title = item.get('title', '')
                body = item.get('body', '')
                extra = {'title': title, 'body': body}
            else:
                url = str(item)
                extra = {}
            if not url:
                continue
            f = Finding(
                type=FindingType.URL,
                value=url,
                source=f"search_engine:{query}",
                timestamp=datetime.now(timezone.utc),
                evidence_hash=create_evidence(url, f"search_engine:{query}", "url")["hash"],
                extra=extra
            )
            findings.append(f)

    # 2. GitHub users
    if isinstance(github_users, list):
        for user in github_users:
            login = user.get("login", "")
            url = user.get("html_url", "")
            if not login:
                continue
            f = Finding(
                type=FindingType.GITHUB,
                value=login,
                source="github_api",
                timestamp=datetime.now(timezone.utc),
                extra={"url": url, "name": user.get("name", "")},
                evidence_hash=create_evidence(login, "github_api", "github")["hash"]
            )
            findings.append(f)

    # 3. Username check results
    for variant, results in username_results.items():
        for r in results:
            if r.get("exists"):
                site = r.get("site", "")
                url = r.get("url", "")
                f = Finding(
                    type=FindingType.USERNAME,
                    value=variant,
                    source=f"username_check:{site}",
                    timestamp=datetime.now(timezone.utc),
                    extra={"site": site, "profile_url": url},
                    evidence_hash=create_evidence(variant, f"username_check:{site}", "username")["hash"]
                )
                findings.append(f)

    # 4. Email patterns
    if email_domain:
        emails = generate_email_variants(name, email_domain)
        for e in emails:
            f = Finding(
                type=FindingType.EMAIL,
                value=e,
                source="pattern_generator",
                timestamp=datetime.now(timezone.utc),
                extra={"domain": email_domain},
                evidence_hash=create_evidence(e, "pattern_generator", "email")["hash"]
            )
            findings.append(f)

    return findings


async def enrich_findings(findings):
    """Enrich each finding with threat intelligence APIs."""
    enriched = []
    for f in findings:
        if f.type == FindingType.IP:
            vt = await vt_lookup(f.value)
            sh = await shodan_lookup(f.value) if config.SHODAN_API_KEY else None
            ab = await abuseipdb_check(f.value) if config.ABUSEIPDB_API_KEY else None
            f.enrichments = {"virustotal": vt, "shodan": sh, "abuseipdb": ab}
        elif f.type == FindingType.EMAIL:
            hibp = await hibp_check(f.value) if config.HIBP_API_KEY else None
            f.enrichments = {"hibp": hibp}
        enriched.append(f)
    return enriched


async def run_investigation_async(args):
    """Main async investigation flow."""
    console.rule(f"[bold cyan]OSINT lookup: {args.name}")

    # Step 1: run existing modules (wrap sync functions with to_thread)
    console.print("[yellow]Running web searches...[/yellow]")
    search_results = await asyncio.to_thread(run_search, args.name, args.context, args.location)
    total_hits = sum(len(v) for v in search_results.values())
    console.print(f"  -> {total_hits} raw results across {len(search_results)} queries")

    console.print("[yellow]Checking GitHub public API for name matches...[/yellow]")
    github_users = await asyncio.to_thread(search_github_users, args.name)
    if isinstance(github_users, list):
        console.print(f"  -> {len(github_users)} GitHub profile(s) with matching name")

    username_results_by_variant = {}
    if not args.skip_username_scan:
        variants = [args.username] if args.username else generate_username_variants(args.name)
        console.print(f"[yellow]Checking {len(variants)} username variant(s) across platforms...[/yellow]")
        for v in variants:
            console.print(f"  checking '{v}'...")
            username_results_by_variant[v] = await check_username_async(v)

        table = Table(title="Confirmed public profiles")
        table.add_column("Username")
        table.add_column("Site")
        table.add_column("URL")
        for variant, results in username_results_by_variant.items():
            for r in results:
                if r.get("exists"):
                    table.add_row(variant, r["site"], r["url"])
        console.print(table)

    if args.email_domain:
        emails = generate_email_variants(args.name, args.email_domain)
        console.print(f"[yellow]Candidate email patterns for {args.email_domain}:[/yellow]")
        for e in emails:
            console.print(f"  {e}  [dim](unverified pattern)[/dim]")

    # Step 2: convert to unified Findings
    findings = convert_to_findings(
        args.name,
        search_results,
        github_users,
        username_results_by_variant,
        args.email_domain
    )
    console.print(f"[green]Total {len(findings)} findings collected.[/green]")

    # Step 3: enrich with threat intel (optional)
    if not args.no_enrich:
        console.print("[yellow]Enriching findings with threat intelligence...[/yellow]")
        findings = await enrich_findings(findings)

    # Step 4: store in database
    init_db()
    for f in findings:
        save_finding(f)

    # Step 5: build graph and timeline (optional)
    graph_path = None
    timeline = None
    if not args.no_graph:
        console.print("[yellow]Building relationship graph...[/yellow]")
        G = build_graph(findings)
        graph_path = export_graph_html(G, "output/graph.html")
        console.print(f"  Graph saved to {graph_path}")
        timeline = build_timeline(findings)

    # Step 6: generate reports
    # 6a. Existing Markdown/JSON report (always)
    paths = save_report(
        args.name,
        search_results,
        username_results_by_variant,
        github_users
    )
    console.print(f"\n[green]Basic report saved:[/green]\n  {paths['markdown']}\n  {paths['json']}")

    # 6b. Advanced PDF/HTML report (unless --no-pdf)
    if not args.no_pdf:
        console.print("[yellow]Generating advanced PDF report...[/yellow]")
        report_data = {
            "target": args.name,
            "username": args.username,
            "location": args.location,
            "context": args.context,
            "findings": findings,
            "graph_path": graph_path,
            "timeline": timeline,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        pdf_path = save_advanced_report(report_data)
        console.print(f"  Advanced report saved to {pdf_path}")

    return findings


def main():
    args = parse_args()
    if args.schedule:
        from scheduler import start_watcher
        start_watcher(
            target=args.name,
            username=args.username,
            location=args.location,
            context=args.context,
            interval_minutes=args.schedule
        )
    else:
        asyncio.run(run_investigation_async(args))


if __name__ == "__main__":
    main()