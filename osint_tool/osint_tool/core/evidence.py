# core/evidence.py
import hashlib
import time
from datetime import datetime

def create_evidence(value, source, finding_type):
    """Create a structured evidence object with timestamp and hash."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    # Combine value and source for a unique hash
    raw = f"{value}|{source}|{timestamp}"
    sha256 = hashlib.sha256(raw.encode()).hexdigest()
    return {
        "type": finding_type,
        "value": value,
        "source": source,
        "timestamp": timestamp,
        "hash": sha256
    }