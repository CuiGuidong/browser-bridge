import concurrent.futures
import json
import os
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlparse


CACHE_DIR = "/tmp/browser-bridge-cache"
EXPIRATION_SECONDS = 24 * 60 * 60
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _is_weibo_image_url(url):
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host.endswith("sinaimg.cn")


def _write_temp_then_rename(data, path):
    temp_path = f"{path}.tmp.{int(time.time() * 1000)}"
    with open(temp_path, "wb") as fh:
        fh.write(data)
    os.rename(temp_path, path)


def download_image_with_urllib(url, path):
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    with opener.open(req, timeout=15) as response:
        data = response.read()
    _write_temp_then_rename(data, path)
    return True


def download_image_with_curl(url, path, minimal=False):
    temp_path = f"{path}.tmp.{int(time.time() * 1000)}"
    if minimal:
        cmd = [
            "curl",
            "-sS",
            "-o",
            temp_path,
            url,
        ]
    else:
        cmd = [
            "curl",
            "-fL",
            "--connect-timeout",
            "10",
            "--max-time",
            "30",
            "-A",
            DEFAULT_USER_AGENT,
            "-o",
            temp_path,
            url,
        ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0 or not os.path.exists(temp_path) or os.path.getsize(temp_path) <= 0:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except OSError:
                pass
            return False
        os.rename(temp_path, path)
        return True
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        return False


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
        # Weibo images often reject urllib with 403 while curl succeeds.
        if _is_weibo_image_url(url):
            if download_image_with_curl(url, path, minimal=True):
                return
            download_image_with_urllib(url, path)
            return
        try:
            download_image_with_urllib(url, path)
            return
        except Exception:
            if download_image_with_curl(url, path):
                return
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
