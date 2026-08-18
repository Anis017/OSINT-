"""
Turns a full name into a set of plausible usernames / email local-parts,
the same way a human would guess them. This is the "smart" part: instead
of checking one exact string, we check the handles people actually pick.
"""

from slugify import slugify


def generate_username_variants(full_name, max_variants=8):
    parts = [p for p in slugify(full_name).split("-") if p]
    if not parts:
        return []

    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    variants = []
    if last:
        variants += [
            f"{first}{last}",
            f"{first}.{last}",
            f"{first}_{last}",
            f"{first[0]}{last}",
            f"{first}{last[0]}",
            f"{last}{first}",
            f"{first}-{last}",
        ]
    variants.append(first)

    # de-dupe, preserve order
    seen = set()
    out = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out[:max_variants]


def generate_email_variants(full_name, domain):
    parts = [p for p in slugify(full_name).split("-") if p]
    if not parts:
        return []
    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    locals_ = [first]
    if last:
        locals_ += [
            f"{first}.{last}",
            f"{first}{last}",
            f"{first}_{last}",
            f"{first[0]}{last}",
            f"{first}.{last[0]}",
        ]
    return [f"{l}@{domain}" for l in locals_]
