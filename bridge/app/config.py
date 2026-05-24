import os


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
