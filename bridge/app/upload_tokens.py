import threading
import time
import secrets

_upload_tokens = {}
_upload_tokens_lock = threading.Lock()

def issue_upload_token(path, size, mime, session_id, tab_id, expected_origin):
    file_id = secrets.token_hex(16)
    with _upload_tokens_lock:
        _upload_tokens[file_id] = {
            "path": path,
            "size": size,
            "mime": mime,
            "session_id": session_id,
            "tab_id": tab_id,
            "expected_origin": expected_origin,
            "created_at": time.time()
        }
    return file_id

def get_upload_token(file_id):
    # Only read and check, do not pop or destroy
    with _upload_tokens_lock:
        return _upload_tokens.get(file_id)

def remove_upload_token(file_id):
    # Explicitly remove and destroy
    with _upload_tokens_lock:
        _upload_tokens.pop(file_id, None)
