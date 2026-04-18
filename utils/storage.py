import json

FILE = "offline.json"


def save_offline(data):
    try:
        with open(FILE, "r") as f:
            logs = json.load(f)
    except:
        logs = []

    logs.append(data)

    with open(FILE, "w") as f:
        json.dump(logs, f)