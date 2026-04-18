import time

from api import send_attendance
from attendance.rfid import read_card
from device import load_config

try:
    config = load_config()
except Exception as e:
    print("Startup error:", e)
    raise SystemExit(1)

print("🚀 Device started:", config.get("device_id", "UNKNOWN_DEVICE"))

while True:
    try:
        uid = read_card()
        print("Card detected:", uid)

        response = send_attendance(config, uid)

        print("Server:", response)

        time.sleep(2)  # prevent duplicate scans

    except Exception as e:
        print("Error:", e)
        time.sleep(2)
