import re
import hashlib
import os
import json
import subprocess
from urllib.parse import urlparse, parse_qs

CACHE_DIR = "/tmp/browser-bridge-cache"

def process_and_spawn_downloads(text_or_items):
    """
    Scans text (or list of dicts with 'text') for [Image: URL], replaces them with dual-anchor tags,
    and spawns a detached background process to download the images.
    """
    if not text_or_items:
        return text_or_items

    tasks = []
    
    def replacer(match):
        original_tag = match.group(0)
        url = match.group(1)
        
        # Calculate local path
        md5_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        
        # Try to guess extension from format param or url
        ext = "jpg"
        try:
            parsed = urlparse(url)
            qs = parse_qs(parsed.query)
            if 'format' in qs:
                ext = qs['format'][0]
            else:
                base_ext = os.path.splitext(parsed.path)[1]
                if base_ext:
                    ext = base_ext.lstrip('.')
        except Exception:
            pass
            
        local_path = os.path.join(CACHE_DIR, f"{md5_hash}.{ext}")
        tasks.append({"url": url, "path": local_path})
        
        return f"[Image Local: {local_path} | Remote: {url}]"

    # Regex to find [Image: URL]
    # Assuming URL doesn't contain ]
    pattern = re.compile(r'\[Image:\s*([^\]|]+)\s*(?:\|[^\]]+)?\]')

    # Process based on type
    result = text_or_items
    if isinstance(text_or_items, str):
        result = pattern.sub(replacer, text_or_items)
    elif isinstance(text_or_items, list):
        # Process feed/search items
        result = []
        for item in text_or_items:
            new_item = dict(item)
            if "text" in new_item and new_item["text"]:
                new_item["text"] = pattern.sub(replacer, new_item["text"])
            result.append(new_item)

    # Spawn downloader if tasks exist
    if tasks:
        # Get the path to the downloader script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        downloader_path = os.path.join(script_dir, "async_image_downloader.py")
        
        try:
            # We pass the JSON task list via stdin to the subprocess
            # Use detached creation so it doesn't block
            process = subprocess.Popen(
                ["python3", downloader_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True # Detach from parent
            )
            process.communicate(input=json.dumps(tasks).encode('utf-8'))
        except Exception as e:
            # Silently fail downloading rather than breaking the text response
            pass

    return result
