import re
from urllib.parse import urlparse


URL_PATTERN = re.compile(r"https?://[^\s　<>\"'】）)\]]+")

ZHIHU_HOSTS = {
    "zhihu.com",
    "www.zhihu.com",
    "zhuanlan.zhihu.com",
}

SUPPORTED_PATHS = (
    "/question/",
    "/p/",
    "/people/",
    "/org/",
)


def extract_first_url(text):
    if not text:
        return None
    match = URL_PATTERN.search((text or "").strip())
    if not match:
        return None
    return match.group(0).rstrip("，。；！？、")


def is_supported_zhihu_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or ""
    except Exception:
        return False
    if host not in ZHIHU_HOSTS:
        return False
    return any(path.startswith(prefix) for prefix in SUPPORTED_PATHS) or "/answer/" in path


def classify_read_post_input(raw_text):
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {"ok": False, "error": "Empty input"}

    url = extract_first_url(raw_text)
    if not url:
        return {"ok": False, "error": "No URL found in input"}
    if not is_supported_zhihu_url(url):
        return {"ok": False, "error": f"Unsupported zhihu URL: {url}"}
    return {"ok": True, "url": url}
