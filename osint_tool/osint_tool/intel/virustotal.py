# intel/virustotal.py
import aiohttp
from core.network import get_http_session
from core.config_loader import load_config

config = load_config()

async def vt_lookup(resource, resource_type="ip"):
    """
    Query VirusTotal API.
    resource: IP, domain, or file hash.
    resource_type: 'ip', 'domain', 'hash'
    """
    if not config.VIRUSTOTAL_API_KEY:
        return {"error": "VT API key not set"}

    url = f"https://www.virustotal.com/api/v3/{resource_type}s/{resource}"
    headers = {"x-apikey": config.VIRUSTOTAL_API_KEY}

    async with await get_http_session() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                return {"error": f"VT API error: {resp.status}"}