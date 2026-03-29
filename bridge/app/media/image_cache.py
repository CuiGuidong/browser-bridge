import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse


CACHE_DIR = "/tmp/browser-bridge-cache"
IMAGE_TAG_PATTERN = re.compile(r"\[Image:\s*([^\]|]+)\s*(?:\|[^\]]+)?\]")


def _normalized_cache_key(url):
    try:
        parsed = urlparse(url.strip())
        normalized = urlunparse(parsed._replace(fragment=""))
        return normalized or url.strip()
    except Exception:
        return url.strip()


def _guess_extension(url):
    ext = "jpg"
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        if "format" in qs and qs["format"]:
            return qs["format"][0]
        base_ext = os.path.splitext(parsed.path)[1]
        if base_ext:
            return base_ext.lstrip(".")
    except Exception:
        return ext
    return ext


def build_cache_path(url, cache_dir=CACHE_DIR):
    cache_key = _normalized_cache_key(url)
    md5_hash = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
    ext = _guess_extension(url)
    return os.path.join(cache_dir, f"{md5_hash}.{ext}")


def _spawn_downloader(tasks):
    if not tasks:
        return
    downloader_path = Path(__file__).with_name("async_image_downloader.py")
    try:
        process = subprocess.Popen(
            [sys.executable, str(downloader_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        process.communicate(input=json.dumps(tasks).encode("utf-8"))
    except Exception:
        return


def process_and_spawn_downloads(text_or_items, cache_dir=CACHE_DIR):
    if not text_or_items:
        return text_or_items

    tasks = []

    def replacer(match):
        url = match.group(1).strip()
        local_path = build_cache_path(url, cache_dir=cache_dir)
        tasks.append({"url": url, "path": local_path})
        return f"[Image Local: {local_path} | Remote: {url}]"

    result = text_or_items
    if isinstance(text_or_items, str):
        result = IMAGE_TAG_PATTERN.sub(replacer, text_or_items)
    elif isinstance(text_or_items, list):
        result = []
        for item in text_or_items:
            new_item = dict(item)
            if new_item.get("text"):
                new_item["text"] = IMAGE_TAG_PATTERN.sub(replacer, new_item["text"])
            result.append(new_item)

    _spawn_downloader(tasks)
    return result
