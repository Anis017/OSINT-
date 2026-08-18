# intel/abuseipdb.py
import aiohttp
from core.network import get_http_session
from core.config_loader import load_config

config = load_config()

async def abuseipdb_check(ip):
    if not config.ABUSEIPDB_API_KEY:
        return {"error": "AbuseIPDB key not set"}
    url = "https://api.abuseipdb.com/api/v2/check"
    params = {"ipAddress": ip, "maxAgeInDays": 90}
    headers = {"Key": config.ABUSEIPDB_API_KEY, "Accept": "application/json"}
    async with await get_http_session() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {"error": f"AbuseIPDB error: {resp.status}"}