import requests
import json
import os

CONFIG_FILE = "config.json"
API_URL = "http://localhost:8000/api/register-device"


def get_device_id():
    try:
        with open('/sys/firmware/devicetree/base/serial-number') as f:
            return f.read().replace('\x00', '').strip()
    except:
        return "UNKNOWN_DEVICE"


def register_device():
    device_id = get_device_id()

    payload = {
        "device_id": device_id,
        "device_type": "RFID"
    }

    res = requests.post(API_URL, json=payload)
    data = res.json()

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

    return data


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return register_device()

    with open(CONFIG_FILE) as f:
        return json.load(f)