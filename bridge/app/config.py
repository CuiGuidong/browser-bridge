import os


def _load_env_local():
    paths = [
        os.path.join(os.getcwd(), ".env.local"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env.local"),
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                                v = v[1:-1]
                            if k and not os.environ.get(k):
                                os.environ[k] = v
                break
            except Exception:
                pass


_load_env_local()

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"


def _get_int(name, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


BRIDGE_HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = _get_int("BRIDGE_PORT", 17777)

BROWSER_RUNTIME = os.getenv("BROWSER_RUNTIME", "auto")  # auto | native_only

# Keepalive configurations
BB_KEEPALIVE_ENABLED = os.getenv("BB_KEEPALIVE_ENABLED", "false").lower() == "true"
BB_KEEPALIVE_SITES = [s.strip() for s in os.getenv("BB_KEEPALIVE_SITES", "").split(",") if s.strip()]
BB_KEEPALIVE_WINDOW_START = os.getenv("BB_KEEPALIVE_WINDOW_START", "09:00")
BB_KEEPALIVE_WINDOW_END = os.getenv("BB_KEEPALIVE_WINDOW_END", "23:00")
BB_KEEPALIVE_DWELL_SECONDS_MIN = _get_int("BB_KEEPALIVE_DWELL_SECONDS_MIN", 20)
BB_KEEPALIVE_DWELL_SECONDS_MAX = _get_int("BB_KEEPALIVE_DWELL_SECONDS_MAX", 60)
BB_KEEPALIVE_STATUS_FILE = os.getenv("BB_KEEPALIVE_STATUS_FILE", "")
