"""
Shared data model. Every module's raw output gets normalized into a list
of Finding objects here -- this is what makes cross-module correlation
possible, since a GitHub bio location and a search-result location are
otherwise two unrelated shapes of data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class FindingType(str, Enum):
    # Existing types
    USERNAME = "username"
    URL = "url"
    LOCATION = "location"
    EMAIL = "email"
    NAME_VARIANT = "name_variant"
    BIO_TEXT = "bio_text"
    AVATAR_HASH = "avatar_hash"
    EMPLOYER = "employer"
    SOCIAL_HANDLE = "social_handle"

    # New types (added for advanced OSINT)
    GITHUB = "github"
    IP = "ip"
    DOMAIN = "domain"
    PHONE = "phone"


@dataclass
class Finding:
    type: FindingType
    value: str                     # normalized value

    # ---- Old fields (used by existing modules) ----
    source_module: str = ""        # "github_lookup", "username_check", etc.
    source_detail: str = ""        # e.g. site name or query
    confidence: float = 0.5        # 0.0‑1.0
    raw: dict = field(default_factory=dict)  # original data for debugging

    # ---- New fields (for advanced features) ----
    source: str = ""               # alias for source_module (preferred)
    timestamp: Optional[datetime] = None
    evidence_hash: str = ""        # SHA‑256 of value + source
    enrichments: Dict[str, Any] = field(default_factory=dict)  # threat intel data
    extra: Dict[str, Any] = field(default_factory=dict)        # any additional data

    def __post_init__(self):
        """Auto‑fill timestamp and set source from source_module if needed."""
        if not self.source and self.source_module:
            self.source = self.source_module
        elif not self.source_module and self.source:
            self.source_module = self.source
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        # If evidence_hash is missing, generate one (optional, but recommended)
        if not self.evidence_hash and self.value and self.source:
            import hashlib
            raw = f"{self.value}|{self.source}"
            self.evidence_hash = hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Correlation:
    """A link between two or more findings that reinforce each other."""
    finding_type: FindingType
    value: str
    supporting_findings: list = field(default_factory=list)  # list[Finding]
    confidence: float = 0.0
    note: str = ""

    @property
    def source_count(self):
        return len({f.source_module for f in self.supporting_findings})