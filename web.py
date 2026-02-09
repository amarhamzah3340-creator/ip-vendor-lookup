import atexit
from argparse import ArgumentParser
from threading import Lock

from flask import Flask, jsonify, render_template

from collector import RouterCollector, load_oui, load_routers

app = Flask(__name__)

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
    if router_id != active_router_id or active_collector is None:
        return jsonify({"connected": False, "router_ip": router_map.get(router_id, {}).get("ip")})
    return jsonify(active_collector.status())


@app.route("/data/<router_id>")
def data(router_id):
    if router_id != active_router_id or active_collector is None:
        return jsonify([])
    return jsonify(active_collector.get_data())


@app.route("/secrets/<router_id>")
def secrets(router_id):
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
