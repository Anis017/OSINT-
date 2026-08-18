import json
from datetime import datetime, timezone

from config import OUTPUT_DIR
from modules.models import Finding, FindingType
from .normalizers import normalize_github_lookup, normalize_search_engines, normalize_username_check
from .search_engines import aggregate_hits
from .correlate import run_correlation


def _slug(name):
    return "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_")


def _flatten_username_results(username_results_by_variant):
    """username_results_by_variant is {variant: [check results...]} -> flat list."""
    flat = []
    for variant, results in username_results_by_variant.items():
        for r in results:
            r = dict(r)
            r["_variant"] = variant
            flat.append(r)
    return flat


def _build_findings(search_results, username_results_by_variant, github_users):
    findings = []

    flat_username_results = _flatten_username_results(username_results_by_variant)
    findings += normalize_username_check(flat_username_results)

    aggregated = aggregate_hits(search_results)
    findings += normalize_search_engines(aggregated)

    if isinstance(github_users, list) and github_users:
        findings += normalize_github_lookup(github_users)

    return findings, aggregated


def _correlation_to_dict(corr):
    return {
        "type": corr.finding_type.value,
        "value": corr.value,
        "confidence": round(corr.confidence, 2),
        "source_count": corr.source_count,
        "note": corr.note,
        "supporting_sources": sorted({f.source_module for f in corr.supporting_findings}),
    }


def _finding_to_dict(f):
    return {
        "type": f.type.value,
        "value": f.value,
        "source_module": f.source_module,
        "source_detail": f.source_detail,
        "confidence": round(f.confidence, 2),
    }


def save_report(full_name, search_results, username_results_by_variant, github_users):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slug(full_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    findings, aggregated_hits = _build_findings(
        search_results, username_results_by_variant, github_users
    )
    correlations = run_correlation(findings)

    report = {
        "target_name": full_name,
        "generated_at": timestamp,
        "correlations": [_correlation_to_dict(c) for c in correlations],
        "findings": [_finding_to_dict(f) for f in findings],
        "search_results": search_results,
        "username_checks": username_results_by_variant,
        "github_matches": github_users,
    }

    json_path = OUTPUT_DIR / f"{slug}_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    md_path = OUTPUT_DIR / f"{slug}_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# OSINT Report: {full_name}\n\n")
        f.write(f"_Generated {timestamp} — public sources only_\n\n")

        # --- Lead with correlated, confidence-ranked findings ---
        f.write("## Correlated Findings (highest confidence first)\n\n")
        if correlations:
            for c in correlations:
                pct = int(c.confidence * 100)
                f.write(f"- **[{pct}%] {c.value}** ({c.finding_type.value}) — {c.note}\n")
            f.write("\n")
        else:
            f.write("No cross-source correlations found — see raw findings below.\n\n")

        # --- Existing sections, unchanged ---
        f.write("## Confirmed public profiles (by username variant)\n\n")
        any_hit = False
        for variant, results in username_results_by_variant.items():
            hits = [r for r in results if r.get("exists")]
            if hits:
                any_hit = True
                f.write(f"### Username variant: `{variant}`\n")
                for h in hits:
                    f.write(f"- **{h['site']}**: {h['url']}\n")
                f.write("\n")
        if not any_hit:
            f.write("No confirmed public profiles found across checked platforms.\n\n")

        if isinstance(github_users, list) and github_users:
            f.write("## GitHub name matches\n\n")
            for u in github_users:
                profile_url = u.get("html_url") or u.get("profile_url", "")
                f.write(f"- {u['login']} — {profile_url}\n")
            f.write("\n")

        f.write("## Web search results\n\n")
        for query, hits in search_results.items():
            f.write(f"### Query: `{query}`\n")
            for h in hits[:5]:
                title = h.get("title", "")
                href = h.get("href", "")
                f.write(f"- [{title}]({href})\n")
            f.write("\n")

        # --- Raw findings appendix, useful for auditing confidence scores ---
        f.write("## All Findings (raw, for reference)\n\n")
        f.write("| Type | Value | Source | Confidence |\n")
        f.write("|---|---|---|---|\n")
        for fdg in sorted(findings, key=lambda x: x.confidence, reverse=True):
            f.write(f"| {fdg.type.value} | {fdg.value} | {fdg.source_module} | {fdg.confidence:.2f} |\n")
        f.write("\n")

    return {"json": str(json_path), "markdown": str(md_path)}

# ---- NEW: Advanced PDF/HTML report ----
import os
from datetime import datetime
from jinja2 import Template

from core.config_loader import load_config

config = load_config()

def save_advanced_report(data):
    """
    Generates an HTML report (and PDF if WeasyPrint is available).
    data: dict with target, context, timestamp, findings, graph_path, timeline
    Returns: path to the generated HTML (or PDF if successful)
    """
    import os
    from datetime import datetime
    from jinja2 import Template
    from config import OUTPUT_DIR
    import json

    # Ensure output directory exists
    report_dir = OUTPUT_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data
    target = data.get("target", "Unknown")
    context = data.get("context", "")
    timestamp = data.get("timestamp", datetime.utcnow().isoformat())
    findings = data.get("findings", [])
    graph_path = data.get("graph_path", "")
    timeline = data.get("timeline", [])

    # ---- Convert findings to serializable dicts ----
    serializable_findings = []
    for f in findings:
        # Convert enum to string
        f_type = f.type.value if hasattr(f.type, 'value') else str(f.type)
        # Convert datetime to ISO string
        f_ts = f.timestamp.isoformat() if f.timestamp else None
        # Build a clean dict
        entry = {
            "type": f_type,
            "value": f.value,
            "source": f.source,
            "timestamp": f_ts,
            "evidence_hash": f.evidence_hash,
            "enrichments": f.enrichments or {},
            "extra": f.extra or {}
        }
        serializable_findings.append(entry)

    # HTML template (unchanged)
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>OSINT Report - {{ target }}</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #2c3e50; border-bottom: 2px solid #3498db; }
            .meta { color: #7f8c8d; font-size: 0.9em; }
            .finding { background: #f8f9fa; padding: 12px; margin: 8px 0; border-left: 4px solid #3498db; border-radius: 4px; }
            .finding strong { color: #2c3e50; }
            .source { color: #95a5a6; font-size: 0.85em; }
            .enrichment { background: #ecf0f1; padding: 8px; margin-top: 6px; border-radius: 3px; }
            .enrichment summary { cursor: pointer; color: #2980b9; }
            .enrichment pre { white-space: pre-wrap; word-wrap: break-word; }
            .graph-container { border: 1px solid #ddd; padding: 10px; margin: 20px 0; background: #fcfcfc; }
            .timeline-item { margin: 6px 0; padding: 4px 0; border-bottom: 1px solid #eee; }
            .timeline-item .time { font-weight: bold; color: #2c3e50; }
            .timeline-item .event { margin-left: 10px; }
            .timeline-item .src { color: #7f8c8d; font-size: 0.85em; }
            .footer { margin-top: 30px; font-size: 0.8em; color: #bdc3c7; text-align: center; }
            .badge { display: inline-block; background: #3498db; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.7em; margin-left: 8px; }
        </style>
    </head>
    <body>
        <h1>🔍 OSINT Investigation Report</h1>
        <p><strong>Target:</strong> {{ target }}</p>
        <p><strong>Context:</strong> {{ context }}</p>
        <p><strong>Generated:</strong> {{ timestamp }}</p>

        <h2>📊 Findings Summary ({{ findings|length }})</h2>
        {% for f in findings %}
            <div class="finding">
                <strong>{{ f.type }}</strong>: {{ f.value }}
                <span class="source">(source: {{ f.source }})</span>
                {% if f.evidence_hash %}
                    <span class="badge">hash: {{ f.evidence_hash[:8] }}…</span>
                {% endif %}
                {% if f.enrichments %}
                    <div class="enrichment">
                        <details>
                            <summary>📎 Enrichments (click to expand)</summary>
                            <pre>{{ f.enrichments|tojson(indent=2) }}</pre>
                        </details>
                    </div>
                {% endif %}
            </div>
        {% endfor %}

        <h2>⏱️ Timeline</h2>
        {% if timeline %}
            {% for event in timeline %}
                <div class="timeline-item">
                    <span class="time">{{ event.time }}</span>
                    <span class="event">{{ event.event }}</span>
                    <span class="src">({{ event.source }})</span>
                </div>
            {% endfor %}
        {% else %}
            <p>No timeline data available.</p>
        {% endif %}

        <h2>🔗 Relationship Graph</h2>
        {% if graph_path %}
            <div class="graph-container">
                <iframe src="{{ graph_path }}" width="100%" height="600px" style="border:none;"></iframe>
            </div>
            <p><em>Graph exported to: {{ graph_path }}</em></p>
        {% else %}
            <p>Graph not generated.</p>
        {% endif %}

        <h2>📄 Raw Findings (JSON)</h2>
        <pre>{{ findings|tojson(indent=2) }}</pre>

        <div class="footer">Generated by OSINT Tool – {{ timestamp }}</div>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(
        target=target,
        context=context,
        timestamp=timestamp,
        findings=serializable_findings,
        graph_path=graph_path,
        timeline=timeline
    )

    # Write HTML
    base_name = f"advanced_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    html_path = report_dir / (base_name + ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Try to generate PDF if weasyprint is available
    try:
        import weasyprint
        pdf_path = report_dir / (base_name + ".pdf")
        weasyprint.HTML(string=html_content).write_pdf(str(pdf_path))
        return str(pdf_path)
    except ImportError:
        print("⚠️ WeasyPrint not installed. Only HTML report generated.")
        return str(html_path)
    except Exception as e:
        print(f"⚠️ PDF generation failed: {e}. HTML report saved.")
        return str(html_path)