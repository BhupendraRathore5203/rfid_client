from device import load_config
from api import send_attendance
from attendance.rfid import read_card
import time

config = load_config()

print("🚀 Device started:", config["device_id"])

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