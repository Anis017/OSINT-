# intel/shodan.py
import aiohttp
from core.network import get_http_session
from core.config_loader import load_config

config = load_config()

async def shodan_lookup(ip):
    if not config.SHODAN_API_KEY:
        return {"error": "Shodan API key not set"}
    url = f"https://api.shodan.io/shodan/host/{ip}?key={config.SHODAN_API_KEY}"
    async with await get_http_session() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                return {"error": f"Shodan error: {resp.status}"}