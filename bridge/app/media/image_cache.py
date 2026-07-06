import re

IMAGE_TAG_PATTERN = re.compile(r"\[Image:\s*([^\]|]+)\s*(?:\|\s*Alt:\s*([^\]]+))?\]")

def normalize_image_tags(text_or_items):
    if not text_or_items:
        return text_or_items

    def replacer(match):
        url = match.group(1).strip()
        alt = match.group(2)
        if alt:
            alt = alt.strip()
            return f"[Image: {url} | Alt: {alt}]"
        return f"[Image: {url}]"

    if isinstance(text_or_items, str):
        return IMAGE_TAG_PATTERN.sub(replacer, text_or_items)
    elif isinstance(text_or_items, list):
        result = []
        for item in text_or_items:
            if not isinstance(item, dict):
                result.append(item)
                continue
            new_item = dict(item)
            if new_item.get("text"):
                new_item["text"] = IMAGE_TAG_PATTERN.sub(replacer, new_item["text"])
            result.append(new_item)
        return result
    return text_or_items

def normalize_media_items(media_items):
    if not media_items:
        return []
    result = []
    for order, item in enumerate(media_items, start=1):
        if not isinstance(item, dict):
            continue
        new_item = dict(item)
        # remove localPath
        new_item.pop("localPath", None)
        
        # trim url
        if "url" in new_item and new_item["url"]:
            new_item["url"] = new_item["url"].strip()
            
        # ensure order
        if "order" not in new_item:
            new_item["order"] = order
            
        # Ensure type
        if "type" not in new_item:
            new_item["type"] = "image"
            
        # Ensure other fields exist but are None if missing
        for key in ["placement", "alt", "title", "source", "role"]:
            if key not in new_item:
                new_item[key] = None
        result.append(new_item)
    return result
