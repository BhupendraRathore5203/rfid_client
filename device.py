import requests
import json
import os
import time
import socket
import uuid
import psutil
import pyudev

CONFIG_FILE = "config.json"

BASE_URL = "http://10.153.137.102:8000/api"   # 🔥 CHANGE THIS

REGISTER_API = f"{BASE_URL}/register-device"
UPDATE_API = f"{BASE_URL}/update-device-info"
HEARTBEAT_API = f"{BASE_URL}/heartbeat"


# -------------------------------
# DEVICE ID
# -------------------------------
def get_device_id():
    try:
        with open('/sys/firmware/devicetree/base/serial-number') as f:
            return f.read().replace('\x00', '').strip()
    except:
        return "UNKNOWN_DEVICE"


# -------------------------------
# SYSTEM INFO
# -------------------------------
def get_system_info():
    return {
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "ip_address": socket.gethostbyname(socket.gethostname()),
        "mac_address": hex(uuid.getnode())
    }


# -------------------------------
# GET CONNECTED DEVICES
# -------------------------------
def get_usb_devices():
    devices = []

    context = pyudev.Context()

    for device in context.list_devices(subsystem='usb'):
        if device.device_type == 'usb_device':
            devices.append({
                "name": device.get('ID_MODEL', 'USB Device'),
                "type": "RFID",  # you can improve detection later
                "identifier": device.device_node or device.sys_name
            })

    return devices


# -------------------------------
# REGISTER DEVICE
# -------------------------------
def register_device():
    device_id = get_device_id()

    payload = {
        "device_id": device_id
    }

    res = requests.post(REGISTER_API, json=payload, timeout=5)
    data = res.json()

    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

    return data


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return register_device()

    with open(CONFIG_FILE) as f:
        return json.load(f)


# -------------------------------
# SEND UPDATE
# -------------------------------
def send_device_update(config):
    payload = {
        "device_id": config["device_id"],
        "api_key": config["api_key"],
        **get_system_info(),
        "peripherals": get_usb_devices()
    }

    try:
        requests.post(UPDATE_API, json=payload, timeout=5)
        print("✅ Device info updated")
    except Exception as e:
        print("❌ Update failed:", e)


# -------------------------------
# HEARTBEAT
# -------------------------------
def send_heartbeat(config):
    try:
        requests.post(HEARTBEAT_API, json={
            "device_id": config["device_id"],
            "api_key": config["api_key"]
        }, timeout=5)
        print("💓 Heartbeat sent")
    except:
        print("❌ Heartbeat failed")


# -------------------------------
# USB LISTENER (🔥 MAIN FEATURE)
# -------------------------------
def monitor_usb(config):
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='usb')

    print("👀 Listening for USB changes...")

    for action, device in monitor:
        print(f"🔌 USB {action}: {device}")

        # Call API whenever device inserted/removed
        send_device_update(config)


# -------------------------------
# MAIN
# -------------------------------
def main():
    config = load_config()

    if not config.get("approved"):
        print("❌ Device not approved")
        return

    print("🚀 Device started")

    # 🔥 Initial update on startup
    send_device_update(config)

    # 🔁 Start USB monitoring
    import threading
    threading.Thread(target=monitor_usb, args=(config,), daemon=True).start()

    # 🔁 Heartbeat loop
    while True:
        send_heartbeat(config)
        time.sleep(30)


if __name__ == "__main__":
    main()