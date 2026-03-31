import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s\u3000<>\"'】）)\]]+")


def extract_first_url(text):
    if not text:
        return None
    match = URL_PATTERN.search((text or "").strip())
    if not match:
        return None
    return match.group(0).rstrip("，。；！？、")


def is_supported_weibo_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in {
        "weibo.com",
        "www.weibo.com",
        "s.weibo.com",
        "m.weibo.cn",
        "mapp.api.weibo.cn",
    }


def classify_read_post_input(raw_text):
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {"ok": False, "error": "Empty input"}

    url = extract_first_url(raw_text)
    if not url:
        return {"ok": False, "error": "Invalid weibo input"}
    if not is_supported_weibo_url(url):
        return {"ok": False, "error": "Unsupported URL"}
    return {"ok": True, "url": url}
