import atexit
from argparse import ArgumentParser
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional
from threading import Lock

from flask import Flask, jsonify, render_template

from collector import RouterCollector, load_oui, load_routers

app = Flask(__name__)

collector_lock = Lock()
config_lock = Lock()
active_router_id = None
active_collector = None

routers: List[Dict] = []
router_map: Dict[str, Dict] = {}
poll_interval = 30
oui_file = "oui.txt"
oui_map: Dict[str, str] = {}
config_path = "config.json"
_last_config_mtime: Optional[float] = None
_last_oui_mtime: Optional[float] = None

_log_callback: Optional[Callable[[str, str], None]] = None


def log(message: str, level: str = "INFO") -> None:
    if _log_callback:
        _log_callback(message, level)


def set_log_callback(callback: Optional[Callable[[str, str], None]]) -> None:
    global _log_callback
    _log_callback = callback


def _load_config(force: bool = False) -> None:
    global routers, router_map, poll_interval, oui_file, oui_map, config_path, _last_config_mtime, _last_oui_mtime

    new_routers, new_poll_interval, new_oui_file, new_config_path = load_routers()
    config_mtime = Path(new_config_path).stat().st_mtime if Path(new_config_path).exists() else None
    oui_mtime = Path(new_oui_file).stat().st_mtime if Path(new_oui_file).exists() else None

    if not force and config_mtime == _last_config_mtime and oui_mtime == _last_oui_mtime:
        return

    routers = new_routers
    router_map = {r["id"]: r for r in routers}
    poll_interval = new_poll_interval
    oui_file = new_oui_file
    oui_map = load_oui(oui_file)
    config_path = new_config_path
    _last_config_mtime = config_mtime
    _last_oui_mtime = oui_mtime
    log(f"Config reloaded ({len(routers)} routers, poll={poll_interval}s, oui={oui_file})")


def refresh_config(force: bool = False) -> None:
    with config_lock:
        _load_config(force=force)


refresh_config(force=True)

routers, poll_interval, oui_file = load_routers()
router_map = {r["id"]: r for r in routers}
oui_map = load_oui(oui_file)

collector_lock = Lock()
active_router_id = None
active_collector = None


def stop_active_collector() -> None:
    global active_router_id, active_collector

    with collector_lock:
        if active_collector is not None:
            active_collector.stop()
        active_collector = None
        active_router_id = None


atexit.register(stop_active_collector)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/routers")
def get_routers():
    refresh_config()
    return jsonify([
        {"id": r["id"], "name": r["name"], "ip": r["ip"]}
        for r in routers
    ])


@app.route("/vendors")
def get_vendors():
    refresh_config()
    return jsonify(sorted({v for v in oui_map.values() if v}))


@app.route("/connect/<router_id>", methods=["POST"])
def connect_router(router_id):
    global active_router_id, active_collector

    refresh_config()
    router = router_map.get(router_id)
    if not router:
        return jsonify({"success": False, "message": "Router not found"}), 404

    with collector_lock:
        if active_router_id == router_id and active_collector is not None:
            return jsonify({"success": True, "message": f"Already connected to {router_id}"})

        if active_collector is not None:
            active_collector.stop()


@app.route("/routers")
def get_routers():
    refresh_config()
    return jsonify([
        {"id": r["id"], "name": r["name"], "ip": r["ip"]}
        for r in routers
    ])


@app.route("/vendors")
def get_vendors():
    refresh_config()
    return jsonify(sorted({v for v in oui_map.values() if v}))


@app.route("/connect/<router_id>", methods=["POST"])
def connect_router(router_id):
    global active_router_id, active_collector

    refresh_config()
    router = router_map.get(router_id)
    if not router:
        return jsonify({"success": False, "message": "Router not found"}), 404

    with collector_lock:
        if active_router_id == router_id and active_collector is not None:
            return jsonify({"success": True, "message": f"Already connected to {router_id}"})

        if active_collector is not None:
            active_collector.stop()

        active_collector = RouterCollector(router, poll_interval=poll_interval, oui_map=oui_map, log_callback=log)
        active_collector.start()
        active_router_id = router_id

    log(f"Active router switched to {router.get('name')} ({router.get('ip')})")

@app.route("/connect/<router_id>", methods=["POST"])
def connect_router(router_id):
    global active_router_id, active_collector

    refresh_config()
    router = router_map.get(router_id)
    if not router:
        return jsonify({"success": False, "message": "Router not found"}), 404

    with collector_lock:
        if active_router_id == router_id and active_collector is not None:
            return jsonify({"success": True, "message": f"Already connected to {router_id}"})

        if active_collector is not None:
            active_collector.stop()

        active_collector = RouterCollector(router, poll_interval=poll_interval, oui_map=oui_map, log_callback=log)
        active_collector.start()
        active_router_id = router_id

    log(f"Active router switched to {router.get('name')} ({router.get('ip')})")

@app.route("/routers")
def get_routers():
    return jsonify([
        {"id": r["id"], "name": r["name"], "ip": r["ip"]}
        for r in routers
    ])


@app.route("/connect/<router_id>", methods=["POST"])
def connect_router(router_id):
    global active_router_id, active_collector

    router = router_map.get(router_id)
    if not router:
        return jsonify({"success": False, "message": "Router not found"}), 404

    with collector_lock:
        if active_router_id == router_id and active_collector is not None:
            return jsonify({"success": True, "message": f"Already connected to {router_id}"})

        if active_collector is not None:
            active_collector.stop()

        active_collector = RouterCollector(router, poll_interval=poll_interval, oui_map=oui_map)
        active_collector.start()
        active_router_id = router_id

    return jsonify({"success": True, "message": f"Connected to {router_id}"})


@app.route("/status/<router_id>")
def status(router_id):
    refresh_config()
    if router_id != active_router_id or active_collector is None:
        return jsonify({"connected": False, "router_ip": router_map.get(router_id, {}).get("ip")})
    return jsonify(active_collector.status())


@app.route("/data/<router_id>")
def data(router_id):
    refresh_config()
    if router_id != active_router_id or active_collector is None:
        return jsonify([])
    return jsonify(active_collector.get_data())


@app.route("/secrets/<router_id>")
def secrets(router_id):
    refresh_config()
    if router_id != active_router_id or active_collector is None:
        return jsonify([])

    rows = active_collector.get_data()
    names = sorted({r.get("name", "") for r in rows if r.get("name")})
    return jsonify(names)


if __name__ == "__main__":
    parser = ArgumentParser(description="PPP monitor web server")
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start Flask server. Without this flag, script only validates config and exits.",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=1080)
    args = parser.parse_args()

    if args.start:
        app.run(host=args.host, port=args.port)
    else:
        print("Server not started. Use --start to run the web server.")
