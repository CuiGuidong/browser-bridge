def ok(action, data):
    return {"ok": True, "action": action, "data": data}


def fail(action, message):
    return {"ok": False, "action": action, "message": message}
