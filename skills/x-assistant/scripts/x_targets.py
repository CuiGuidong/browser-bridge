from urllib.parse import urlparse


_RESERVED_HANDLES = {
    "home",
    "search",
    "explore",
    "notifications",
    "messages",
    "compose",
    "settings",
    "i",
}


def extract_status_id(url):
    try:
        parts = [p for p in urlparse(url).path.split("/") if p]
        if "status" in parts:
            idx = parts.index("status")
            if idx + 1 < len(parts):
                return parts[idx + 1]
    except Exception:
        return None
    return None


def extract_handle(value):
    if not value:
        return None
    value = value.strip()
    if value.startswith("@"):
        value = value[1:]
    if "://" not in value:
        return value or None
    try:
        parsed = urlparse(value)
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return None
        handle = parts[0]
        if handle.lower() in _RESERVED_HANDLES:
            return None
        return handle
    except Exception:
        return None


def build_profile_url(handle):
    normalized = extract_handle(handle)
    if not normalized:
        return None
    return f"https://x.com/{normalized}"


def build_author_from_page_url(page_url):
    handle = extract_handle(page_url)
    if not handle:
        return None
    return {
        "handle": handle,
        "url": build_profile_url(handle),
    }
