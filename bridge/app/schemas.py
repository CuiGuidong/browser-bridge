def ok(action, data):
    return {"ok": True, "action": action, "data": data}


def fail(action, code, message, detail=None):
    return {
        "ok": False,
        "action": action,
        "error": {
            "code": code,
            "message": message,
            "detail": detail or {},
        },
    }
