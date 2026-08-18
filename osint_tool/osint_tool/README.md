# Name-based OSINT Tool (public data only)

Given a person's name, this tool:

1. **Web searches**  runs a set of smart, targeted DuckDuckGo queries
   (name + linkedin, + github, + twitter, + news, etc.)
2. **GitHub lookup**  checks GitHub's public search API for matching
   profile names
3. **Username enumeration**  generates plausible usernames from the
   name (`janedoe`, `jane.doe`, `jdoe`, ...) and checks ~19 major
   platforms for a live public profile at that handle (same as you
   manually visiting `github.com/jane doe` in a browser)
4. **Email pattern suggestions** (optional) if you give it a company
   domain, it suggests likely email address *patterns* (not verified,
   just candidates like `jane.doe@company.com`)
5. **Report generation** writes a Markdown + JSON report to `output/`

## What this tool deliberately does NOT do

- No login/authentication bypass
- No scraping of content behind auth walls
- No breach-data / leaked-credential lookups
- No email verification via SMTP probing (that edges into abuse territory
  on many mail servers)
- No phone number / address lookups via data-broker APIs

If you want to extend it in those directions, that's a legal/ethical
line you'd be crossing depending on jurisdiction and use case — worth
researching (GDPR, CFAA, platform ToS) before doing so.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic - auto-generates username variants and checks them
python main.py "Jane Doe"

# Add context to disambiguate common names
python main.py "Jane Doe" --context "Paris software engineer"

# Check one specific known/suspected username instead of variants
python main.py "Jane Doe" --username janedoe123

# Also suggest email patterns for a known employer domain
python main.py "Jane Doe" --email-domain acmecorp.com

# Skip the (slower) cross-platform username scan
python main.py "Jane Doe" --skip-username-scan
```

Reports land in `output/<name>_<timestamp>.md` and `.json`.

## Extending it

- Add more platforms: edit `data/sites.json`  just add a URL template
  and how to detect a 404 (`status_code` or `text_match`).
- Add more public APIs (e.g. a company's public employee directory,
  a public Mastodon instance search) as new files in `modules/`,
  following the pattern in `github_lookup.py`.
- Rate limiting: bump `MAX_CONCURRENCY` down in `config.py` if you
  start getting blocked by a platform.
