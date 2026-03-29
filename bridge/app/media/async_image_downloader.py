import concurrent.futures
import json
import os
import sys
import time
import urllib.request


CACHE_DIR = "/tmp/browser-bridge-cache"
EXPIRATION_SECONDS = 24 * 60 * 60


def clean_old_cache(cache_dir=CACHE_DIR, expiration_seconds=EXPIRATION_SECONDS):
    if not os.path.exists(cache_dir):
        return
    now = time.time()
    for filename in os.listdir(cache_dir):
        filepath = os.path.join(cache_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            file_mod_time = os.path.getmtime(filepath)
        except OSError:
            continue
        if now - file_mod_time <= expiration_seconds:
            continue
        try:
            os.remove(filepath)
        except OSError:
            pass


def download_image(url, path):
    if os.path.exists(path):
        return
    try:
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with opener.open(req, timeout=15) as response:
            data = response.read()
        temp_path = f"{path}.tmp.{int(time.time() * 1000)}"
        with open(temp_path, "wb") as fh:
            fh.write(data)
        os.rename(temp_path, path)
    except Exception:
        return


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    clean_old_cache()
    try:
        payload = sys.stdin.read()
        if not payload.strip():
            return
        tasks = json.loads(payload)
    except Exception:
        return
    if not tasks:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for task in tasks:
            url = task.get("url")
            path = task.get("path")
            if url and path:
                futures.append(executor.submit(download_image, url, path))
        concurrent.futures.wait(futures)


if __name__ == "__main__":
    main()
