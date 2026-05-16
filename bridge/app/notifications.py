import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_local_env():
    path = Path(__file__).resolve().parents[2] / ".env.local"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class NotificationService:
    def __init__(self):
        _load_local_env()
        self.telegram_token = os.getenv("BB_NOTIFY_TELEGRAM_BOT_TOKEN", "").strip()
        self.telegram_chat_id = os.getenv("BB_NOTIFY_TELEGRAM_CHAT_ID", "").strip()
        self.wechat_webhook = os.getenv("BB_NOTIFY_WECHAT_WEBHOOK", "").strip()
        self.min_interval_seconds = float(os.getenv("BB_NOTIFY_MIN_INTERVAL_SECONDS", "900"))
        self._last_sent_at = {}

    def configured_providers(self):
        providers = []
        if self.telegram_token and self.telegram_chat_id:
            providers.append("telegram")
        if self.wechat_webhook:
            providers.append("wechat")
        return providers

    def send_login_alert(self, status):
        site = status.get("site") or ((status.get("content") or {}).get("site"))
        key = f"login:{site}"
        now = time.time()
        last_sent_at = self._last_sent_at.get(key)
        if last_sent_at and now - last_sent_at < self.min_interval_seconds:
            return {
                "sent": False,
                "skipped": "rate_limited",
                "providers": self.configured_providers(),
            }

        text = self._format_login_alert(status)
        results = []
        if self.telegram_token and self.telegram_chat_id:
            results.append(self._send_telegram(text))
        if self.wechat_webhook:
            results.append(self._send_wechat(text))
        sent = any(result.get("ok") for result in results)
        if sent:
            self._last_sent_at[key] = now
        return {
            "sent": sent,
            "providers": self.configured_providers(),
            "results": results,
        }

    def _format_login_alert(self, status):
        content = status.get("content") or status
        site = content.get("site") or status.get("site") or "unknown"
        url = content.get("url") or ((status.get("page") or {}).get("url")) or ""
        checked_at = content.get("checkedAt") or ""
        return (
            "[browser-bridge] Login attention required\n"
            f"site: {site}\n"
            f"loggedIn: {content.get('loggedIn')}\n"
            f"needsHumanLogin: {content.get('needsHumanLogin')}\n"
            f"url: {url}\n"
            f"checkedAt: {checked_at}"
        )

    def _post_json(self, url, payload):
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                status = response.status
                body = response.read().decode("utf-8", errors="replace")
            return {
                "ok": True,
                "status": status,
                "body": body[:500],
            }
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            return {
                "ok": False,
                "error": str(error),
            }

    def _send_telegram(self, text):
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        result = self._post_json(url, {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": True,
        })
        return {
            "provider": "telegram",
            **result,
        }

    def _send_wechat(self, text):
        result = self._post_json(self.wechat_webhook, {
            "msgtype": "text",
            "text": {
                "content": text,
            },
        })
        return {
            "provider": "wechat",
            **result,
        }
