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

CDP_PUBLIC_HOST = os.getenv("CDP_PUBLIC_HOST", "127.0.0.1")
CDP_CONNECT_HOST = os.getenv("CDP_CONNECT_HOST", CDP_PUBLIC_HOST)
CDP_PORT = _get_int("CDP_PORT", 9222)

CDP_BASE_URL = f"http://{CDP_PUBLIC_HOST}:{CDP_PORT}"
CDP_CONNECT_BASE_URL = f"http://{CDP_CONNECT_HOST}:{CDP_PORT}"
CDP_HOST_HEADER = f"{CDP_PUBLIC_HOST}:{CDP_PORT}"
CDP_WS_BASE_URL = f"ws://{CDP_PUBLIC_HOST}:{CDP_PORT}"
CDP_TIMEOUT_SECONDS = _get_int("CDP_TIMEOUT_SECONDS", 10)
