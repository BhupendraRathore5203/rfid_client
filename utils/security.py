import time
import hmac
import hashlib


def generate_headers(device_id, api_key):
    timestamp = str(int(time.time()))

    message = device_id + timestamp

    signature = hmac.new(
        api_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "X-DEVICE-ID": device_id,
        "X-TIMESTAMP": timestamp,
        "X-SIGNATURE": signature
    }