import hashlib


def analyze_item(item):
    text = (item.get("text") or "").strip()
    author_info = (item.get("authorInfo") or "").strip()

    is_ad = "Promoted" in text or "赞助" in text or "Ad" in author_info
    is_retweet = "RT @" in text or "Retweeted" in author_info or "转推了" in author_info

    score = 50
    score += min(len(text) // 10, 30)
    if "http" in text or "[Image:" in text or "[Video" in text:
        score += 10
    if len(text) < 20 and ("http" in text or "[Image:" in text):
        score -= 10

    signal_type = "original"
    if is_ad:
        signal_type = "ad"
        score -= 100
    elif is_retweet:
        signal_type = "retweet"
        score -= 10
    elif len(text) < 15 and not ("http" in text or "[Image:" in text):
        signal_type = "low-info"
        score -= 30

    worth_reading = score > 40 and not is_ad

    return {
        "signal_type": signal_type,
        "score": score,
        "is_ad": is_ad,
        "is_worth_reading": worth_reading,
    }


def dedup_and_score(items):
    seen_urls = set()
    seen_texts = set()
    deduped = []

    for item in items:
        url = (item.get("url") or "").strip()
        text = (item.get("text") or "").strip()

        if url and url in seen_urls:
            continue

        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        if text_hash in seen_texts:
            continue

        if url:
            seen_urls.add(url)
        seen_texts.add(text_hash)

        enriched = dict(item)
        enriched["analysis"] = analyze_item(enriched)
        deduped.append(enriched)

    deduped.sort(key=lambda x: x["analysis"]["score"], reverse=True)
    return deduped
