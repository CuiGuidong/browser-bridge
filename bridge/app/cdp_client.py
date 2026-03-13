import json
import urllib.error
import urllib.request

from .config import CDP_BASE_URL, CDP_HOST_HEADER, CDP_TIMEOUT_SECONDS


class CdpClientError(Exception):
    pass


class CdpHttpClient:
    def __init__(self, base_url=CDP_BASE_URL, host_header=CDP_HOST_HEADER, timeout=CDP_TIMEOUT_SECONDS):
        self.base_url = base_url.rstrip("/")
        self.host_header = host_header
        self.timeout = timeout

    def get_json(self, path):
        body = self.request_text("GET", path)
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise CdpClientError(f"Invalid JSON from CDP endpoint: {path}") from e

    def get_text(self, path):
        return self.request_text("GET", path)

    def put_json(self, path):
        body = self.request_text("PUT", path)
        try:
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise CdpClientError(f"Invalid JSON from CDP endpoint: {path}") from e

    def request_text(self, method, path):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("Host", self.host_header)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            details = e.read().decode("utf-8", errors="replace") if hasattr(e, 'read') else ''
            msg = f"HTTP {e.code} from CDP endpoint: {path}"
            if details:
                msg += f" :: {details.strip()}"
            raise CdpClientError(msg) from e
        except urllib.error.URLError as e:
            raise CdpClientError(f"Failed to reach CDP endpoint: {path}: {e}") from e
