# analytics/nlp_analyzer.py
import re

# Simple regex patterns – you can replace with spaCy for better accuracy
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
DOMAIN_RE = re.compile(r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}')
IP_RE = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
CRYPTO_BTC = re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b')
CRYPTO_ETH = re.compile(r'\b0x[a-fA-F0-9]{40}\b')

def extract_entities(text):
    """Extract emails, domains, IPs, crypto addresses from text."""
    entities = {
        "emails": EMAIL_RE.findall(text),
        "domains": DOMAIN_RE.findall(text),
        "ips": IP_RE.findall(text),
        "btc": CRYPTO_BTC.findall(text),
        "eth": CRYPTO_ETH.findall(text)
    }
    return entities