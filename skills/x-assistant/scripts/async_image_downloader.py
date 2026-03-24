import sys
import json
import urllib.request
import os
import time
import concurrent.futures

# Configuration
CACHE_DIR = "/tmp/browser-bridge-cache"
EXPIRATION_SECONDS = 24 * 60 * 60  # 24 hours

def clean_old_cache():
    if not os.path.exists(CACHE_DIR):
        return
    now = time.time()
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            file_mod_time = os.path.getmtime(filepath)
            if now - file_mod_time > EXPIRATION_SECONDS:
                try:
                    os.remove(filepath)
                except Exception as e:
                    print(f"Failed to delete {filepath}: {e}")

def download_image(url, path):
    if os.path.exists(path):
        return  # Skip already downloaded
        
    try:
        # Avoid proxy side effects that might block Python's urllib
        proxy_handler = urllib.request.ProxyHandler({})
        opener = urllib.request.build_opener(proxy_handler)
        
        # Twitter CDN requires User-Agent sometimes
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with opener.open(req, timeout=15) as response:
            data = response.read()
            # Write to a temporary file first, then atomic rename to prevent partial files
            temp_path = f"{path}.tmp.{int(time.time() * 1000)}"
            with open(temp_path, 'wb') as f:
                f.write(data)
            os.rename(temp_path, path)
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def main():
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    clean_old_cache()
    
    # Read mapping from stdin
    try:
        input_data = sys.stdin.read()
        if not input_data.strip():
            return
        tasks = json.loads(input_data)
    except Exception as e:
        print(f"Error parsing input: {e}")
        return

    # tasks should be a list of dicts: [{"url": "...", "path": "..."}]
    if not tasks:
        return

    # Use ThreadPool to download concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for task in tasks:
            url = task.get("url")
            path = task.get("path")
            if url and path:
                futures.append(executor.submit(download_image, url, path))
        
        # Wait for all to finish (this runs detached, so it doesn't block the agent)
        concurrent.futures.wait(futures)

if __name__ == "__main__":
    main()
