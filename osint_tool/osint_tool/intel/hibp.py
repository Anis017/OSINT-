# intel/hibp.py
import aiohttp
from core.network import get_http_session
from core.config_loader import load_config

config = load_config()

async def hibp_check(email):
    """Check if email appears in Have I Been Pwned."""
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    headers = {"hibp-api-key": config.HIBP_API_KEY} if config.HIBP_API_KEY else {}
    async with await get_http_session() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 404:
                return []  # not found
            else:
                return {"error": f"HIBP error: {resp.status}"}