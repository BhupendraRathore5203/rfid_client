from utils.security import generate_headers

API_URL = "http://your-server.com/api/scan"


def send_attendance(config, uid):
    try:
        device_id = config.get("device_id")
        api_key = config.get("api_key")
        if not device_id or not api_key:
            raise RuntimeError("Config missing device_id/api_key")

        headers = generate_headers(device_id, api_key)

        payload = {
            "uid": uid
        }

        import requests  # type: ignore
        res = requests.post(API_URL, json=payload, headers=headers)
        return res.json()
    except Exception as e:
        print("API Error:", e)
        return None
