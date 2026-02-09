import time
import json
import sys
from routeros_api import RouterOsApiPool

MIKROTIK_LOCAL_IP = "192.168.1.1"
MIKROTIK_VPN_IP = "10.10.10.1"

MIKROTIK_USER = "user"
MIKROTIK_PASS = "pass"
MIKROTIK_PORT = 8728

POLL_INTERVAL = 60
CACHE_FILE = "ppp_active.json"

MODE = "local"
if len(sys.argv) > 1:
    MODE = sys.argv[1]

MIKROTIK_IP = MIKROTIK_LOCAL_IP if MODE == "local" else MIKROTIK_VPN_IP


def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def main():
    print(f"[INFO] Connecting to MikroTik ({MODE})...")

    while True:
        try:
            api_pool = RouterOsApiPool(
                MIKROTIK_IP,
                username=MIKROTIK_USER,
                password=MIKROTIK_PASS,
                port=MIKROTIK_PORT,
                plaintext_login=True
            )

            api = api_pool.get_api()
            ppp = api.get_resource("/ppp/active")
            actives = ppp.get()

            result = []

            for a in actives:
                result.append({
                    "name": a.get("name"),
                    "ip": a.get("address"),
                    "mac": a.get("caller-id"),
                    "uptime": a.get("uptime"),
                    "service": a.get("service")
                })

            save_cache(result)

            print(f"[OK] Updated {len(result)} users")

        except Exception as e:
            print("[ERROR]", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
