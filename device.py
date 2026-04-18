import json
import os
import socket
import time
import uuid
from pathlib import Path

CONFIG_FILE_NAME = "config.json"
CONFIG_FILE = CONFIG_FILE_NAME

BASE_URL = "http://10.153.137.102:8000/api"   # 🔥 CHANGE THIS

REGISTER_API = f"{BASE_URL}/register-device"
UPDATE_API = f"{BASE_URL}/update-device-info"
HEARTBEAT_API = f"{BASE_URL}/heartbeat"


# -------------------------------
# CONFIG
# -------------------------------
def get_config_path() -> Path:
    override = os.getenv("RFID_CONFIG_FILE") or os.getenv("RFID_CONFIG_PATH")
    if override:
        return Path(override).expanduser()

    return Path(__file__).with_name(CONFIG_FILE_NAME)


def _read_config(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {}
    except OSError as e:
        print(f"Config read failed ({path}): {e}")
        return {}

    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid config JSON ({path}): {e}")
        return {}

    return data if isinstance(data, dict) else {}


def _write_config(path: Path, data: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    except OSError as e:
        print(f"Config write failed ({path}): {e}")


# -------------------------------
# DEVICE ID
# -------------------------------
def get_device_id():
    override = os.getenv("RFID_DEVICE_ID")
    if override and override.strip():
        return override.strip()

    for path in (
        "/sys/firmware/devicetree/base/serial-number",
        "/proc/device-tree/serial-number",
    ):
        try:
            with open(path, encoding="utf-8") as f:
                serial = f.read().replace("\x00", "").strip()
            if serial:
                return serial
        except OSError:
            pass

    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("serial"):
                    serial = line.split(":", 1)[-1].strip()
                    if serial:
                        return serial
    except OSError:
        pass

    for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(path, encoding="utf-8") as f:
                machine_id = f.read().strip()
            if machine_id:
                return machine_id
        except OSError:
            pass

    return hex(uuid.getnode())


# -------------------------------
# SYSTEM INFO
# -------------------------------
def get_system_info():
    try:
        import psutil  # type: ignore
    except Exception:
        return {}

    try:
        ip_address = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip_address = None

    try:
        disk_usage = psutil.disk_usage("/").percent
    except Exception:
        disk_usage = None

    return {
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent,
        "disk_usage": disk_usage,
        "ip_address": ip_address,
        "mac_address": hex(uuid.getnode())
    }


# -------------------------------
# GET CONNECTED DEVICES
# -------------------------------
def get_usb_devices():
    devices = []

    try:
        import pyudev  # type: ignore
    except Exception:
        return devices

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

    import requests  # type: ignore

    res = requests.post(REGISTER_API, json=payload, timeout=5)
    res.raise_for_status()

    try:
        data = res.json()
    except Exception as e:
        raise RuntimeError("Register API returned invalid JSON") from e

    if not isinstance(data, dict):
        raise RuntimeError("Register API returned non-object JSON")

    if not data.get("device_id"):
        data["device_id"] = device_id

    config_path = get_config_path()
    _write_config(config_path, data)

    return data


def load_config():
    config_path = get_config_path()
    config = _read_config(config_path)

    env_api_key = os.getenv("RFID_API_KEY")
    if env_api_key and env_api_key.strip() and not config.get("api_key"):
        config["api_key"] = env_api_key.strip()

    if not config.get("device_id"):
        config["device_id"] = get_device_id()

    if not config.get("api_key"):
        try:
            config = register_device()
        except Exception as e:
            raise RuntimeError(
                f"Missing api_key in {config_path}. "
                "Create config.json with api_key (and optional device_id), "
                "or fix BASE_URL/REGISTER_API so the client can register."
            ) from e

    _write_config(config_path, config)
    return config


# -------------------------------
# SEND UPDATE
# -------------------------------
def send_device_update(config):
    if not config.get("device_id") or not config.get("api_key"):
        raise RuntimeError("Config missing device_id/api_key")

    payload = {
        "device_id": config["device_id"],
        "api_key": config["api_key"],
        **get_system_info(),
        "peripherals": get_usb_devices()
    }

    try:
        import requests  # type: ignore
        requests.post(UPDATE_API, json=payload, timeout=5)
        print("✅ Device info updated")
    except Exception as e:
        print("❌ Update failed:", e)


# -------------------------------
# HEARTBEAT
# -------------------------------
def send_heartbeat(config):
    try:
        if not config.get("device_id") or not config.get("api_key"):
            raise RuntimeError("Config missing device_id/api_key")

        import requests  # type: ignore
        requests.post(HEARTBEAT_API, json={
            "device_id": config["device_id"],
            "api_key": config["api_key"]
        }, timeout=5)
        print("💓 Heartbeat sent")
    except Exception as e:
        print("❌ Heartbeat failed:", e)


# -------------------------------
# USB LISTENER (🔥 MAIN FEATURE)
# -------------------------------
def monitor_usb(config):
    try:
        import pyudev  # type: ignore
    except Exception:
        print("pyudev not installed; USB monitoring disabled.")
        return

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
