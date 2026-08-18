# analytics/timeline.py
from datetime import datetime

def build_timeline(findings):
    """Sort findings by timestamp and return chronological list."""
    # Assuming each finding has a 'timestamp' attribute (datetime)
    sorted_findings = sorted(findings, key=lambda f: f.timestamp, reverse=False)
    return [{"time": f.timestamp.isoformat(), "event": f.value, "source": f.source} for f in sorted_findings]