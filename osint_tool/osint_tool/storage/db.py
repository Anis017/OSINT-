# storage/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .model import Base, FindingRecord, ScanRun
from core.config_loader import load_config
import json
import datetime
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc)

config = load_config()
engine = create_engine(f"sqlite:///{config.DB_PATH}")
Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

import json

def save_finding(finding):
    session = Session()
    rec = FindingRecord(
        type=finding.type,
        value=finding.value,
        source=finding.source,
        timestamp=finding.timestamp or datetime.utcnow(),
        evidence_hash=finding.evidence_hash,
        extra=json.dumps(finding.extra or {})   # ← this is the fix
    )
    session.add(rec)
    session.commit()
    session.close()

def get_findings(limit=100):
    session = Session()
    records = session.query(FindingRecord).order_by(FindingRecord.timestamp.desc()).limit(limit).all()
    session.close()
    return records

def get_all_findings():
    session = Session()
    records = session.query(FindingRecord).all()
    session.close()
    return records

