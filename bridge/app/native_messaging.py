"""Chrome Native Messaging protocol codec.

Protocol format: 4-byte little-endian uint32 length prefix + UTF-8 JSON payload.
- host -> Chrome: max 1 MB
- Chrome -> host: max 64 MiB
"""
import struct
import json


def read_message(stream):
    """Read one Native Messaging message from a binary stream.

    Returns parsed JSON dict, or None on EOF / invalid data.
    """
    raw_length = stream.read(4)
    if not raw_length or len(raw_length) < 4:
        return None
    length = struct.unpack('<I', raw_length)[0]
    data = stream.read(length)
    if not data or len(data) < length:
        return None
    return json.loads(data)


def write_message(stream, msg):
    """Write one Native Messaging message to a binary stream."""
    encoded = json.dumps(msg, ensure_ascii=False).encode('utf-8')
    stream.write(struct.pack('<I', len(encoded)))
    stream.write(encoded)
    stream.flush()
