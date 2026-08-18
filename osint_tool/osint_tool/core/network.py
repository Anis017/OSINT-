# core/network.py
import random
import aiohttp
from .config_loader import load_config

config = load_config()

async def get_http_session():
    """Return an aiohttp.ClientSession with proxy and user-agent rotation."""
    headers = {"User-Agent": random.choice(config.USER_AGENTS)}
    connector = None
    if config.PROXY:
        connector = aiohttp.TCPConnector()
    session = aiohttp.ClientSession(
        headers=headers,
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
    )
    return session

def rotate_user_agent():
    return random.choice(config.USER_AGENTS)