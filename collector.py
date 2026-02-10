import json
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from routeros_api import RouterOsApiPool


class RouterCollector:
    def __init__(
        self,
        router: Dict,
        poll_interval: int = 30,
        oui_map: Optional[Dict[str, str]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
    ):
        self.router = router
        self.poll_interval = poll_interval
        self.oui_map = oui_map or {}
        self.log_callback = log_callback

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._api_pool: Optional[RouterOsApiPool] = None

        self._lock = threading.Lock()
        self._data: List[Dict] = []
        self._connected = False
        self._last_error = ""

    def _log(self, message: str, level: str = "INFO") -> None:
        if self.log_callback:
            self.log_callback(message, level)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._log(f"Collector starting for {self.router.get('name', self.router.get('id', '-'))}")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name=f"collector-{self.router['id']}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=self.poll_interval + 2)
        self._disconnect()
        self._log(f"Collector stopped for {self.router.get('name', self.router.get('id', '-'))}")

    def status(self) -> Dict:
        with self._lock:
            return {
                "connected": self._connected,
                "router_ip": self.router.get("ip"),
                "last_error": self._last_error,
            }

    def get_data(self) -> List[Dict]:
        with self._lock:
            return list(self._data)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._connect()
                data = self._fetch_ppp_active()
                with self._lock:
                    self._data = data
                    self._connected = True
                    self._last_error = ""
                self._log(f"Fetched {len(data)} PPP active rows from {self.router.get('ip')}")
            except Exception as exc:
                with self._lock:
                    self._connected = False
                    self._last_error = str(exc)
                self._log(f"Router polling error {self.router.get('ip')}: {exc}", "ERROR")
            finally:
                # Always disconnect after every polling cycle so stop() doesn't leave hanging connection.
                self._disconnect()

            self._stop_event.wait(self.poll_interval)

    def _connect(self) -> None:
        self._api_pool = RouterOsApiPool(
            self.router["ip"],
            username=self.router["username"],
            password=self.router["password"],
            port=self.router.get("port", 8274),
            plaintext_login=True,
        )
        self._log(f"Connected API {self.router.get('ip')}:{self.router.get('port', 8274)}")

    def _fetch_ppp_active(self) -> List[Dict]:
        if not self._api_pool:
            return []

        api = self._api_pool.get_api()
        resource = api.get_resource("/ppp/active")
        result = []
        for item in resource.get():
            mac = item.get("caller-id", "")
            result.append(
                {
                    "name": item.get("name", ""),
                    "ip": item.get("address", ""),
                    "mac": mac,
                    "vendor": self._lookup_vendor(mac),
                    "uptime": item.get("uptime", "-"),
                }
            )
        return result

    def _lookup_vendor(self, mac: str) -> str:
        key = mac.upper().replace("-", ":")[0:8]
        return self.oui_map.get(key, "Unknown")

    def _disconnect(self) -> None:
        if self._api_pool is not None:
            try:
                self._api_pool.disconnect()
                self._log(f"Disconnected API {self.router.get('ip')}")
            except Exception:
                pass
            finally:
                self._api_pool = None


def _resolve_path(path_str: str, base_dir: Optional[Path] = None) -> Path:
    path = Path(path_str)
    if path.is_absolute() and path.exists():
        return path

    candidates = []
    if base_dir is not None:
        candidates.append(base_dir / path)

    candidates.append(Path.cwd() / path)
    module_dir = Path(__file__).resolve().parent
    candidates.append(module_dir / path)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else path


def load_oui(oui_file: str) -> Dict[str, str]:
    vendors: Dict[str, str] = {}
    oui_path = _resolve_path(oui_file)
    try:
        with oui_path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if "(hex)" not in line:
                    continue
                prefix, vendor = line.split("(hex)", maxsplit=1)
                key = prefix.strip().replace("-", ":")
                vendors[key] = vendor.strip()
    except FileNotFoundError:
        return {}
    return vendors


def load_routers(config_file: str = "config.json") -> Tuple[List[Dict], int, str, str]:
    config_path = _resolve_path(config_file)
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)

    oui_value = cfg.get("oui_file", "oui.txt")
    oui_path = _resolve_path(oui_value, base_dir=config_path.parent)
    return cfg.get("routers", []), cfg.get("poll_interval", 30), str(oui_path), str(config_path)
