# storage/models.py
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class FindingRecord(Base):
    __tablename__ = 'findings'
    id = Column(Integer, primary_key=True)
    type = Column(String(50))
    value = Column(String(500))
    source = Column(String(100))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    evidence_hash = Column(String(64))
    extra = Column(Text)  # JSON string for enrichment data

class ScanRun(Base):
    __tablename__ = 'scan_runs'
    id = Column(Integer, primary_key=True)
    target = Column(String(200))
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    findings_count = Column(Integer)