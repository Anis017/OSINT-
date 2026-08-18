"""
Uses GitHub's public, unauthenticated search API to find users whose
profile name matches. Public API, public data, rate-limited by GitHub
itself (60 req/hr unauthenticated) - nothing sneaky.
"""

import requests

from config import USER_AGENT, REQUEST_TIMEOUT


def search_github_users(full_name):
    url = "https://api.github.com/search/users"
    params = {"q": f'"{full_name}" in:name', "per_page": 10}
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return {"error": f"GitHub API returned {resp.status_code}"}
        data = resp.json()
        return [
            {
                "login": item["login"],
                "profile_url": item["html_url"],
                "avatar_url": item.get("avatar_url"),
            }
            for item in data.get("items", [])
        ]
    except Exception as e:
        return {"error": str(e)}
