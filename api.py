import requests
from utils.security import generate_headers

API_URL = "http://your-server.com/api/scan"


def send_attendance(config, uid):
    headers = generate_headers(config["device_id"], config["api_key"])

    payload = {
        "uid": uid
    }

    try:
        res = requests.post(API_URL, json=payload, headers=headers)
        return res.json()
    except Exception as e:
        print("API Error:", e)
        return None