import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s\u3000<>\"'】）)\]]+")
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{16,32}$")


def extract_first_url(text):
    if not text:
        return None
    match = URL_PATTERN.search(text.strip())
    if not match:
        return None
    return match.group(0).rstrip("，。；！？、")


def is_short_link(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return host == "xhslink.com" or host.endswith(".xhslink.com")
    except Exception:
        return False


def is_xiaohongshu_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
        return host == "www.xiaohongshu.com" or host.endswith(".xiaohongshu.com")
    except Exception:
        return False


def looks_like_note_id(value):
    if not value:
        return False
    value = value.strip()
    if "://" in value:
        return False
    if any("\u4e00" <= ch <= "\u9fff" for ch in value):
        return False
    if " " in value or "\t" in value or "\n" in value:
        return False
    return bool(NOTE_ID_PATTERN.match(value))


def extract_note_id(value):
    if not value:
        return None
    value = value.strip()
    if "://" not in value:
        if not looks_like_note_id(value):
            return None
        return value or None
    try:
        parts = [p for p in urlparse(value).path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "explore":
            return parts[1]
    except Exception:
        return None
    return None


def build_note_url(value):
    note_id = extract_note_id(value)
    if not note_id:
        return None
    return f"https://www.xiaohongshu.com/explore/{note_id}"


def classify_read_post_input(raw_text):
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {"ok": False, "error": "Empty input"}

    url = extract_first_url(raw_text)
    if url:
        if is_short_link(url):
            return {"ok": True, "kind": "short_url", "url": url, "noteId": None}
        if is_xiaohongshu_url(url):
            return {"ok": True, "kind": "long_url", "url": url, "noteId": extract_note_id(url)}
        return {"ok": False, "error": "Unsupported URL"}

    if looks_like_note_id(raw_text):
        note_id = extract_note_id(raw_text)
        return {
            "ok": True,
            "kind": "note_id",
            "url": build_note_url(note_id),
            "noteId": note_id,
        }

    return {"ok": False, "error": "Invalid note input"}
