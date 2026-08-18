# core/config_loader.py
import os
try:
    from dotenv import load_dotenv
    load_dotenv()  # optional .env file
except ImportError:
    def load_dotenv():
        pass

class Config:
    # API Keys
    VIRUSTOTAL_API_KEY = os.getenv("VT_API_KEY", "")
    SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
    ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY", "")
    HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")  # optional for HIBP v3

    # Network
    PROXY = os.getenv("PROXY", None)  # e.g., "socks5://127.0.0.1:9050"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
        # add more
    ]
    REQUEST_TIMEOUT = 30
    MAX_CONCURRENT = 10

    # Storage
    DB_PATH = os.getenv("DB_PATH", "data/osint.db")

    # Reporting
    REPORT_OUTPUT_DIR = "output/reports"

def load_config():
    return Config